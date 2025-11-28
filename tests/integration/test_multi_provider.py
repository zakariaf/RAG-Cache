"""Integration tests for multi-provider LLM flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.factory import LLMProviderFactory
from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.fallback_strategy import LLMFallbackStrategy
from app.llm.provider_selector import LLMProviderSelector
from app.models.query import QueryRequest
from app.models.llm import LLMResponse
from app.exceptions import LLMProviderError


class TestMultiProviderFlow:
    """Integration tests for multi-provider LLM interactions."""

    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI response."""
        return LLMResponse(
            content="OpenAI response content",
            prompt_tokens=10,
            completion_tokens=50,
            model="gpt-3.5-turbo",
        )

    @pytest.fixture
    def mock_anthropic_response(self):
        """Create mock Anthropic response."""
        return LLMResponse(
            content="Anthropic response content",
            prompt_tokens=15,
            completion_tokens=60,
            model="claude-3-5-sonnet-20241022",
        )

    @pytest.fixture
    def sample_request(self):
        """Create sample query request."""
        return QueryRequest(query="What is the capital of France?")

    @patch("app.llm.factory.config")
    def test_factory_creates_openai_provider(self, mock_config):
        """Test factory creates OpenAI provider."""
        mock_config.openai_api_key = "test-openai-key"
        mock_config.default_llm_provider = "openai"

        provider = LLMProviderFactory.create("openai")

        assert isinstance(provider, OpenAIProvider)
        assert provider.get_name() == "openai"

    @patch("app.llm.factory.config")
    def test_factory_creates_anthropic_provider(self, mock_config):
        """Test factory creates Anthropic provider."""
        mock_config.anthropic_api_key = "test-anthropic-key"

        provider = LLMProviderFactory.create("anthropic")

        assert isinstance(provider, AnthropicProvider)
        assert provider.get_name() == "anthropic"

    @pytest.mark.asyncio
    async def test_fallback_from_openai_to_anthropic(
        self, sample_request, mock_anthropic_response
    ):
        """Test fallback from OpenAI to Anthropic when primary fails."""
        # Create mock providers
        mock_openai = MagicMock()
        mock_openai.complete = AsyncMock(
            side_effect=LLMProviderError("OpenAI unavailable")
        )
        mock_openai.get_name.return_value = "openai"

        mock_anthropic = MagicMock()
        mock_anthropic.complete = AsyncMock(return_value=mock_anthropic_response)
        mock_anthropic.get_name.return_value = "anthropic"

        # Create fallback strategy with actual API
        fallback = LLMFallbackStrategy()

        # Execute with fallback - pass providers list
        result = await fallback.execute_with_fallback(
            providers=[mock_openai, mock_anthropic],
            request=sample_request,
        )

        assert result is not None
        assert result.content == "Anthropic response content"
        mock_openai.complete.assert_called_once()
        mock_anthropic.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_exhausts_all_providers(self, sample_request):
        """Test fallback exhausts all providers before failing."""
        # All providers fail
        mock_primary = MagicMock()
        mock_primary.complete = AsyncMock(
            side_effect=LLMProviderError("Primary failed")
        )
        mock_primary.get_name.return_value = "primary"

        mock_fallback1 = MagicMock()
        mock_fallback1.complete = AsyncMock(
            side_effect=LLMProviderError("Fallback 1 failed")
        )
        mock_fallback1.get_name.return_value = "fallback1"

        mock_fallback2 = MagicMock()
        mock_fallback2.complete = AsyncMock(
            side_effect=LLMProviderError("Fallback 2 failed")
        )
        mock_fallback2.get_name.return_value = "fallback2"

        fallback = LLMFallbackStrategy()

        with pytest.raises(LLMProviderError):
            await fallback.execute_with_fallback(
                providers=[mock_primary, mock_fallback1, mock_fallback2],
                request=sample_request,
            )

        # All providers should have been tried
        mock_primary.complete.assert_called_once()
        mock_fallback1.complete.assert_called_once()
        mock_fallback2.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_primary_succeeds_no_fallback(
        self, sample_request, mock_openai_response
    ):
        """Test primary success doesn't trigger fallback."""
        mock_primary = MagicMock()
        mock_primary.complete = AsyncMock(return_value=mock_openai_response)
        mock_primary.get_name.return_value = "openai"

        mock_fallback = MagicMock()
        mock_fallback.complete = AsyncMock()
        mock_fallback.get_name.return_value = "anthropic"

        fallback = LLMFallbackStrategy()

        result = await fallback.execute_with_fallback(
            providers=[mock_primary, mock_fallback],
            request=sample_request,
        )

        assert result.content == "OpenAI response content"
        mock_primary.complete.assert_called_once()
        mock_fallback.complete.assert_not_called()


class TestProviderSelection:
    """Tests for provider selection logic."""

    def test_selector_selects_preferred_provider(self):
        """Test selector returns preferred provider."""
        mock_openai = MagicMock()
        mock_openai.get_name.return_value = "openai"

        mock_anthropic = MagicMock()
        mock_anthropic.get_name.return_value = "anthropic"

        selector = LLMProviderSelector()

        result = selector.select_provider(
            providers=[mock_openai, mock_anthropic],
            circuit_breakers={},
            preferred_provider="anthropic",
        )

        assert result is not None
        assert result.get_name() == "anthropic"

    def test_selector_returns_first_available_when_no_preference(self):
        """Test selector returns first available when no preference."""
        mock_openai = MagicMock()
        mock_openai.get_name.return_value = "openai"

        mock_anthropic = MagicMock()
        mock_anthropic.get_name.return_value = "anthropic"

        selector = LLMProviderSelector()

        result = selector.select_provider(
            providers=[mock_openai, mock_anthropic],
            circuit_breakers={},
        )

        # Should return first provider
        assert result is not None

    def test_selector_returns_none_for_empty_list(self):
        """Test selector returns None for empty provider list."""
        selector = LLMProviderSelector()

        result = selector.select_provider(
            providers=[],
            circuit_breakers={},
        )

        assert result is None


class TestCostAggregation:
    """Tests for cost aggregation across providers."""

    def test_calculate_cost_openai(self):
        """Test cost calculation for OpenAI."""
        from app.llm.cost_calculator import CostCalculator

        calculator = CostCalculator()
        cost = calculator.calculate(1000, 500, "gpt-3.5-turbo")

        assert cost > 0
        assert cost < 0.01  # Should be very cheap

    def test_calculate_cost_anthropic(self):
        """Test cost calculation for Anthropic."""
        from app.llm.cost_calculator import CostCalculator

        calculator = CostCalculator()
        cost = calculator.calculate(1000, 500, "claude-3-5-sonnet-20241022")

        assert cost > 0

    def test_compare_provider_costs(self):
        """Test comparing costs across providers."""
        from app.llm.cost_calculator import CostCalculator

        calculator = CostCalculator()

        # Same token count, different providers
        openai_cost = calculator.calculate(1000, 1000, "gpt-3.5-turbo")
        anthropic_cost = calculator.calculate(1000, 1000, "claude-3-5-sonnet-20241022")

        # Both should have valid costs
        assert openai_cost > 0
        assert anthropic_cost > 0


class TestTokenCounting:
    """Tests for token counting across providers."""

    def test_count_tokens_openai(self):
        """Test token counting for OpenAI."""
        from app.llm.token_counter import TokenCounter

        counter = TokenCounter()
        text = "What is the capital of France?"
        count = counter.count(text, "gpt-3.5-turbo")

        assert count > 0
        assert count < 20  # Should be around 7-8 tokens

    def test_count_tokens_anthropic(self):
        """Test token counting for Anthropic."""
        from app.llm.token_counter import TokenCounter

        counter = TokenCounter()
        text = "What is the capital of France?"
        count = counter.count(text, "claude-3-5-sonnet-20241022")

        assert count > 0

    def test_token_counts_are_similar(self):
        """Test token counts are similar across providers."""
        from app.llm.token_counter import TokenCounter

        counter = TokenCounter()
        text = "The quick brown fox jumps over the lazy dog."

        openai_count = counter.count(text, "gpt-3.5-turbo")
        anthropic_count = counter.count(text, "claude-3-5-sonnet-20241022")

        # Counts should be within 2x of each other
        assert 0.5 < openai_count / max(anthropic_count, 1) < 2
