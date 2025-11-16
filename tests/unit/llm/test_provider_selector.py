"""Tests for LLM provider selector."""

from unittest.mock import Mock

from app.llm.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from app.llm.provider_selector import (
    LLMProviderSelector,
    PreferredProviderStrategy,
    RoundRobinStrategy,
)


class TestPreferredProviderStrategy:
    """Test preferred provider selection strategy."""

    def test_select_preferred_provider(self):
        """Test selecting preferred provider when available."""
        strategy = PreferredProviderStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"

        providers = [provider1, provider2]
        circuit_breakers = {}

        selected = strategy.select(
            providers, circuit_breakers, preferred_provider="anthropic"
        )

        assert selected == provider2

    def test_select_first_when_no_preference(self):
        """Test selecting first available when no preference."""
        strategy = PreferredProviderStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"

        providers = [provider1, provider2]
        circuit_breakers = {}

        selected = strategy.select(providers, circuit_breakers)

        assert selected == provider1

    def test_skip_provider_with_open_circuit(self):
        """Test skipping provider with open circuit breaker."""
        strategy = PreferredProviderStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"

        providers = [provider1, provider2]

        # Create circuit breaker in OPEN state for provider1
        breaker1 = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        breaker1._state = CircuitState.OPEN

        circuit_breakers = {"openai": breaker1}

        selected = strategy.select(providers, circuit_breakers)

        # Should skip openai (circuit open) and select anthropic
        assert selected == provider2

    def test_select_preferred_even_if_not_first(self):
        """Test selecting preferred provider even if not first in list."""
        strategy = PreferredProviderStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"
        provider3 = Mock()
        provider3.get_name.return_value = "cohere"

        providers = [provider1, provider2, provider3]
        circuit_breakers = {}

        selected = strategy.select(
            providers, circuit_breakers, preferred_provider="cohere"
        )

        assert selected == provider3

    def test_fallback_when_preferred_unavailable(self):
        """Test fallback when preferred provider is unavailable."""
        strategy = PreferredProviderStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"

        providers = [provider1, provider2]

        # Make preferred provider unavailable
        breaker2 = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        breaker2._state = CircuitState.OPEN

        circuit_breakers = {"anthropic": breaker2}

        selected = strategy.select(
            providers, circuit_breakers, preferred_provider="anthropic"
        )

        # Should fallback to openai
        assert selected == provider1

    def test_return_none_when_no_providers(self):
        """Test returning None when provider list is empty."""
        strategy = PreferredProviderStrategy()

        selected = strategy.select([], {})

        assert selected is None

    def test_return_none_when_all_circuits_open(self):
        """Test returning None when all circuits are open."""
        strategy = PreferredProviderStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"

        providers = [provider1, provider2]

        # Open all circuits
        breaker1 = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        breaker1._state = CircuitState.OPEN
        breaker2 = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        breaker2._state = CircuitState.OPEN

        circuit_breakers = {"openai": breaker1, "anthropic": breaker2}

        selected = strategy.select(providers, circuit_breakers)

        assert selected is None

    def test_half_open_circuit_is_available(self):
        """Test that HALF_OPEN circuit is considered available."""
        strategy = PreferredProviderStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"

        providers = [provider1]

        breaker1 = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        breaker1._state = CircuitState.HALF_OPEN

        circuit_breakers = {"openai": breaker1}

        selected = strategy.select(providers, circuit_breakers)

        # HALF_OPEN should be available
        assert selected == provider1


class TestRoundRobinStrategy:
    """Test round-robin selection strategy."""

    def test_round_robin_selection(self):
        """Test round-robin cycles through providers."""
        strategy = RoundRobinStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"
        provider3 = Mock()
        provider3.get_name.return_value = "cohere"

        providers = [provider1, provider2, provider3]
        circuit_breakers = {}

        # First call
        selected1 = strategy.select(providers, circuit_breakers)
        assert selected1 == provider1

        # Second call
        selected2 = strategy.select(providers, circuit_breakers)
        assert selected2 == provider2

        # Third call
        selected3 = strategy.select(providers, circuit_breakers)
        assert selected3 == provider3

        # Fourth call - should wrap around
        selected4 = strategy.select(providers, circuit_breakers)
        assert selected4 == provider1

    def test_round_robin_skips_unavailable(self):
        """Test round-robin skips providers with open circuits."""
        strategy = RoundRobinStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"
        provider3 = Mock()
        provider3.get_name.return_value = "cohere"

        providers = [provider1, provider2, provider3]

        # Make provider2 unavailable
        breaker2 = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        breaker2._state = CircuitState.OPEN

        circuit_breakers = {"anthropic": breaker2}

        # Should only cycle between openai and cohere
        selected1 = strategy.select(providers, circuit_breakers)
        assert selected1.get_name() in ["openai", "cohere"]

        selected2 = strategy.select(providers, circuit_breakers)
        assert selected2.get_name() in ["openai", "cohere"]

    def test_round_robin_with_single_provider(self):
        """Test round-robin with single provider returns same provider."""
        strategy = RoundRobinStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"

        providers = [provider1]
        circuit_breakers = {}

        selected1 = strategy.select(providers, circuit_breakers)
        selected2 = strategy.select(providers, circuit_breakers)
        selected3 = strategy.select(providers, circuit_breakers)

        assert selected1 == provider1
        assert selected2 == provider1
        assert selected3 == provider1

    def test_round_robin_return_none_when_empty(self):
        """Test round-robin returns None when no providers."""
        strategy = RoundRobinStrategy()

        selected = strategy.select([], {})

        assert selected is None

    def test_round_robin_return_none_when_all_unavailable(self):
        """Test round-robin returns None when all unavailable."""
        strategy = RoundRobinStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"

        providers = [provider1]

        breaker1 = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        breaker1._state = CircuitState.OPEN

        circuit_breakers = {"openai": breaker1}

        selected = strategy.select(providers, circuit_breakers)

        assert selected is None


class TestLLMProviderSelector:
    """Test LLM provider selector."""

    def test_default_strategy_is_preferred(self):
        """Test default strategy is PreferredProviderStrategy."""
        selector = LLMProviderSelector()

        assert isinstance(selector._strategy, PreferredProviderStrategy)

    def test_custom_strategy(self):
        """Test using custom strategy."""
        strategy = RoundRobinStrategy()
        selector = LLMProviderSelector(strategy)

        assert selector._strategy == strategy

    def test_select_provider_uses_strategy(self):
        """Test select_provider delegates to strategy."""
        strategy = Mock()
        strategy.select.return_value = Mock()

        selector = LLMProviderSelector(strategy)

        provider1 = Mock()
        provider1.get_name.return_value = "openai"

        providers = [provider1]
        circuit_breakers = {}

        selector.select_provider(
            providers, circuit_breakers, preferred_provider="openai"
        )

        strategy.select.assert_called_once_with(providers, circuit_breakers, "openai")

    def test_set_strategy(self):
        """Test changing strategy at runtime."""
        selector = LLMProviderSelector()

        new_strategy = RoundRobinStrategy()
        selector.set_strategy(new_strategy)

        assert selector._strategy == new_strategy

    def test_select_with_preferred_provider_strategy(self):
        """Test full selection with preferred provider strategy."""
        selector = LLMProviderSelector(PreferredProviderStrategy())

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"

        providers = [provider1, provider2]
        circuit_breakers = {}

        selected = selector.select_provider(
            providers, circuit_breakers, preferred_provider="anthropic"
        )

        assert selected == provider2

    def test_select_with_round_robin_strategy(self):
        """Test full selection with round-robin strategy."""
        selector = LLMProviderSelector(RoundRobinStrategy())

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"

        providers = [provider1, provider2]
        circuit_breakers = {}

        # First selection
        selected1 = selector.select_provider(providers, circuit_breakers)
        assert selected1 == provider1

        # Second selection
        selected2 = selector.select_provider(providers, circuit_breakers)
        assert selected2 == provider2

    def test_select_provider_with_no_providers(self):
        """Test selecting when no providers available."""
        selector = LLMProviderSelector()

        selected = selector.select_provider([], {})

        assert selected is None
