"""Integration tests for LLM providers."""

import pytest

from app.llm.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from app.llm.cost_tracker import LLMCostTracker
from app.llm.fallback_strategy import FallbackConfig, LLMFallbackStrategy
from app.llm.provider_selector import (
    LLMProviderSelector,
    PreferredProviderStrategy,
    RoundRobinStrategy,
)
from app.llm.registry import LLMProviderRegistry
from app.llm.timeout_handler import TimeoutConfig, TimeoutHandler
from app.models.query import QueryRequest
from tests.mocks.llm_mocks import (
    FailingMockProvider,
    MockAnthropicProvider,
    MockLLMProvider,
    MockOpenAIProvider,
)


class TestLLMProviderIntegration:
    """Integration tests for LLM provider components."""

    @pytest.mark.asyncio
    async def test_registry_with_multiple_providers(self):
        """Test registry managing multiple providers."""
        registry = LLMProviderRegistry()
        openai = MockOpenAIProvider()
        anthropic = MockAnthropicProvider()

        registry.register(openai)
        registry.register(anthropic)

        assert registry.has_provider("openai")
        assert registry.has_provider("anthropic")
        assert len(registry.list_providers()) == 2

    @pytest.mark.asyncio
    async def test_provider_selection_preferred_strategy(self):
        """Test provider selection with preferred strategy."""
        selector = LLMProviderSelector(PreferredProviderStrategy())
        providers = [MockOpenAIProvider(), MockAnthropicProvider()]
        circuit_breakers = {}

        # Select preferred provider
        provider = selector.select_provider(
            providers, circuit_breakers, preferred_provider="anthropic"
        )

        assert provider.get_name() == "anthropic"

    @pytest.mark.asyncio
    async def test_provider_selection_round_robin(self):
        """Test provider selection with round-robin strategy."""
        selector = LLMProviderSelector(RoundRobinStrategy())
        providers = [MockOpenAIProvider(), MockAnthropicProvider()]
        circuit_breakers = {}

        # First call
        provider1 = selector.select_provider(providers, circuit_breakers)
        assert provider1.get_name() == "openai"

        # Second call
        provider2 = selector.select_provider(providers, circuit_breakers)
        assert provider2.get_name() == "anthropic"

        # Third call wraps around
        provider3 = selector.select_provider(providers, circuit_breakers)
        assert provider3.get_name() == "openai"

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_fallback(self):
        """Test circuit breaker integration with fallback."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)

        failing_provider = FailingMockProvider(name="failing")
        success_provider = MockLLMProvider(name="backup")

        # Fail twice to open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.execute(
                    lambda: failing_provider.complete(QueryRequest(query="test"))
                )

        # Circuit should be open
        assert breaker.get_state().name == "OPEN"

        # Fallback strategy can use backup provider
        strategy = LLMFallbackStrategy()
        providers = [success_provider]  # Use backup only

        response = await strategy.execute_with_fallback(
            providers, QueryRequest(query="test")
        )

        assert response.content == "mock response"

    @pytest.mark.asyncio
    async def test_cost_tracking_across_providers(self):
        """Test cost tracking with multiple providers."""
        tracker = LLMCostTracker()
        openai = MockOpenAIProvider()
        anthropic = MockAnthropicProvider()
        request = QueryRequest(query="test")

        # Make requests
        openai_response = await openai.complete(request)
        anthropic_response = await anthropic.complete(request)

        # Track costs
        tracker.track_request(
            "openai",
            openai_response.model,
            openai_response.prompt_tokens,
            openai_response.completion_tokens,
        )
        tracker.track_request(
            "anthropic",
            anthropic_response.model,
            anthropic_response.prompt_tokens,
            anthropic_response.completion_tokens,
        )

        # Verify summary
        summary = tracker.get_summary()
        assert summary.total_requests == 2
        assert "openai" in summary.provider_costs
        assert "anthropic" in summary.provider_costs

    @pytest.mark.asyncio
    async def test_fallback_strategy_with_providers(self):
        """Test fallback strategy with real provider flow."""
        failing = FailingMockProvider(name="primary")
        backup = MockLLMProvider(name="backup", response_content="backup worked")

        strategy = LLMFallbackStrategy()
        providers = [failing, backup]
        request = QueryRequest(query="test")

        response = await strategy.execute_with_fallback(providers, request)

        assert response.content == "backup worked"
        assert failing.get_call_count() == 1
        assert backup.get_call_count() == 1

    @pytest.mark.asyncio
    async def test_timeout_handler_with_provider(self):
        """Test timeout handler wrapping provider calls."""
        timeout_config = TimeoutConfig(timeout_seconds=5.0)
        handler = TimeoutHandler(timeout_config)
        provider = MockLLMProvider()
        request = QueryRequest(query="test")

        # Should complete within timeout
        response = await handler.execute(lambda: provider.complete(request))

        assert response.content == "mock response"
        assert provider.get_call_count() == 1

    @pytest.mark.asyncio
    async def test_full_workflow_with_registry_and_selection(self):
        """Test complete workflow: registry → selection → execution."""
        # Setup registry
        registry = LLMProviderRegistry()
        registry.register(MockOpenAIProvider())
        registry.register(MockAnthropicProvider())

        # Setup selector
        selector = LLMProviderSelector(PreferredProviderStrategy())
        providers = [
            registry.get("openai"),
            registry.get("anthropic"),
        ]

        # Select and execute
        provider = selector.select_provider(providers, {}, preferred_provider="openai")
        response = await provider.complete(QueryRequest(query="Hello"))

        assert provider.get_name() == "openai"
        assert "OpenAI" in response.content

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        import asyncio

        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=0.1, success_threshold=1
        )
        breaker = CircuitBreaker(config)

        # Setup conditional provider
        call_count = [0]

        async def conditional_operation():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception("fail")
            return "success"

        # Fail twice to open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.execute(conditional_operation)

        # Circuit is open
        assert breaker.get_state().name == "OPEN"

        # Wait for recovery
        await asyncio.sleep(0.15)

        # Should attempt recovery and succeed
        result = await breaker.execute(conditional_operation)
        assert result == "success"
        assert breaker.get_state().name == "CLOSED"

    @pytest.mark.asyncio
    async def test_provider_with_circuit_breaker_and_cost_tracking(self):
        """Test provider with circuit breaker and cost tracking."""
        breaker = CircuitBreaker()
        tracker = LLMCostTracker()
        provider = MockOpenAIProvider()
        request = QueryRequest(query="test")

        # Execute through circuit breaker
        response = await breaker.execute(lambda: provider.complete(request))

        # Track cost
        tracker.track_request(
            provider.get_name(),
            response.model,
            response.prompt_tokens,
            response.completion_tokens,
        )

        # Verify
        assert breaker.get_state().name == "CLOSED"
        assert tracker.get_request_count() == 1
        assert tracker.get_total_cost() > 0

    @pytest.mark.asyncio
    async def test_fallback_with_cost_tracking(self):
        """Test fallback strategy with cost tracking."""
        tracker = LLMCostTracker()
        strategy = LLMFallbackStrategy()

        failing = FailingMockProvider()
        backup = MockOpenAIProvider()
        providers = [failing, backup]
        request = QueryRequest(query="test")

        response = await strategy.execute_with_fallback(providers, request)

        # Track successful request
        tracker.track_request(
            backup.get_name(),
            response.model,
            response.prompt_tokens,
            response.completion_tokens,
        )

        assert tracker.get_request_count() == 1
        assert failing.get_call_count() == 1
        assert backup.get_call_count() == 1

    @pytest.mark.asyncio
    async def test_multiple_provider_registrations_and_selections(self):
        """Test complex multi-provider scenario."""
        registry = LLMProviderRegistry()

        # Register multiple providers
        for i in range(3):
            provider = MockLLMProvider(
                name=f"provider-{i}", response_content=f"Response {i}"
            )
            registry.register(provider)

        # Verify all registered
        assert len(registry.list_providers()) == 3

        # Select each one
        for i in range(3):
            provider = registry.get(f"provider-{i}")
            response = await provider.complete(QueryRequest(query="test"))
            assert f"Response {i}" in response.content

    @pytest.mark.asyncio
    async def test_provider_failure_and_retry(self):
        """Test provider failure and retry mechanism."""
        provider = MockLLMProvider()
        request = QueryRequest(query="test")

        # First call succeeds
        response1 = await provider.complete(request)
        assert response1.content == "mock response"

        # Configure to fail
        provider.set_should_fail(True)
        with pytest.raises(Exception):
            await provider.complete(request)

        # Configure back to success
        provider.set_should_fail(False)
        response2 = await provider.complete(request)
        assert response2.content == "mock response"

        assert provider.get_call_count() == 3

    @pytest.mark.asyncio
    async def test_end_to_end_with_all_components(self):
        """Test end-to-end integration of all components."""
        # Setup components
        registry = LLMProviderRegistry()
        selector = LLMProviderSelector(PreferredProviderStrategy())
        tracker = LLMCostTracker()
        fallback_strategy = LLMFallbackStrategy(FallbackConfig(max_retries=2))

        # Register providers
        openai = MockOpenAIProvider()
        anthropic = MockAnthropicProvider()
        registry.register(openai)
        registry.register(anthropic)

        # Select provider
        providers_list = [registry.get("openai"), registry.get("anthropic")]
        selected = selector.select_provider(
            providers_list, {}, preferred_provider="openai"
        )

        # Execute with fallback
        response = await fallback_strategy.execute_with_single_fallback(
            selected,
            registry.get("anthropic"),
            QueryRequest(query="Hello"),
        )

        # Track cost
        tracker.track_request(
            selected.get_name(),
            response.model,
            response.prompt_tokens,
            response.completion_tokens,
        )

        # Verify end-to-end
        assert response.content is not None
        assert tracker.get_request_count() == 1
        assert tracker.get_total_cost() > 0
