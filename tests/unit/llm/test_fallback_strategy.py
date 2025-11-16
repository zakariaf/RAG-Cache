"""Tests for LLM fallback strategy."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.exceptions import LLMProviderError
from app.llm.fallback_strategy import FallbackConfig, LLMFallbackStrategy
from app.models.llm import LLMResponse
from app.models.query import QueryRequest


class TestFallbackConfig:
    """Test fallback configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FallbackConfig()

        assert config.max_retries == 3
        assert config.retry_on_timeout is True
        assert config.retry_on_error is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = FallbackConfig(
            max_retries=5, retry_on_timeout=False, retry_on_error=False
        )

        assert config.max_retries == 5
        assert config.retry_on_timeout is False
        assert config.retry_on_error is False


class TestLLMFallbackStrategy:
    """Test LLM fallback strategy."""

    @pytest.mark.asyncio
    async def test_execute_with_successful_first_provider(self):
        """Test successful execution with first provider."""
        strategy = LLMFallbackStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider1.complete = AsyncMock(
            return_value=LLMResponse(
                content="success",
                prompt_tokens=10,
                completion_tokens=5,
                model="gpt-3.5-turbo",
            )
        )

        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"

        request = QueryRequest(query="test")
        providers = [provider1, provider2]

        response = await strategy.execute_with_fallback(providers, request)

        assert response.content == "success"
        provider1.complete.assert_called_once()
        # provider2 should not be called
        assert not hasattr(provider2, "complete") or not provider2.complete.called

    @pytest.mark.asyncio
    async def test_execute_with_fallback_on_error(self):
        """Test fallback to second provider on error."""
        strategy = LLMFallbackStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider1.complete = AsyncMock(side_effect=ValueError("API error"))

        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"
        provider2.complete = AsyncMock(
            return_value=LLMResponse(
                content="fallback success",
                prompt_tokens=10,
                completion_tokens=5,
                model="claude-3",
            )
        )

        request = QueryRequest(query="test")
        providers = [provider1, provider2]

        response = await strategy.execute_with_fallback(providers, request)

        assert response.content == "fallback success"
        provider1.complete.assert_called_once()
        provider2.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_all_providers_failing(self):
        """Test all providers failing raises error."""
        strategy = LLMFallbackStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider1.complete = AsyncMock(side_effect=ValueError("Error 1"))

        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"
        provider2.complete = AsyncMock(side_effect=ValueError("Error 2"))

        request = QueryRequest(query="test")
        providers = [provider1, provider2]

        with pytest.raises(LLMProviderError) as exc_info:
            await strategy.execute_with_fallback(providers, request)

        assert "All providers failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_with_no_providers(self):
        """Test error when no providers available."""
        strategy = LLMFallbackStrategy()

        request = QueryRequest(query="test")

        with pytest.raises(LLMProviderError) as exc_info:
            await strategy.execute_with_fallback([], request)

        assert "No providers available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_respects_max_retries(self):
        """Test max_retries limits number of attempts."""
        config = FallbackConfig(max_retries=2)
        strategy = LLMFallbackStrategy(config)

        provider1 = Mock()
        provider1.get_name.return_value = "provider1"
        provider1.complete = AsyncMock(side_effect=ValueError("Error 1"))

        provider2 = Mock()
        provider2.get_name.return_value = "provider2"
        provider2.complete = AsyncMock(side_effect=ValueError("Error 2"))

        provider3 = Mock()
        provider3.get_name.return_value = "provider3"
        provider3.complete = AsyncMock(
            return_value=LLMResponse(
                content="success", prompt_tokens=10, completion_tokens=5, model="model3"
            )
        )

        request = QueryRequest(query="test")
        providers = [provider1, provider2, provider3]

        with pytest.raises(LLMProviderError):
            await strategy.execute_with_fallback(providers, request)

        # Only first 2 providers should be tried
        provider1.complete.assert_called_once()
        provider2.complete.assert_called_once()
        # provider3 should not be called due to max_retries
        assert not hasattr(provider3, "complete") or not provider3.complete.called

    @pytest.mark.asyncio
    async def test_execute_with_timeout_retry(self):
        """Test retry on timeout error."""
        config = FallbackConfig(retry_on_timeout=True)
        strategy = LLMFallbackStrategy(config)

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider1.complete = AsyncMock(
            side_effect=LLMProviderError("Request timed out")
        )

        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"
        provider2.complete = AsyncMock(
            return_value=LLMResponse(
                content="success", prompt_tokens=10, completion_tokens=5, model="claude"
            )
        )

        request = QueryRequest(query="test")
        providers = [provider1, provider2]

        response = await strategy.execute_with_fallback(providers, request)

        assert response.content == "success"
        provider1.complete.assert_called_once()
        provider2.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_without_error_retry(self):
        """Test not retrying when retry_on_error is False."""
        config = FallbackConfig(retry_on_error=False, retry_on_timeout=False)
        strategy = LLMFallbackStrategy(config)

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider1.complete = AsyncMock(side_effect=ValueError("API error"))

        provider2 = Mock()
        provider2.get_name.return_value = "anthropic"

        request = QueryRequest(query="test")
        providers = [provider1, provider2]

        with pytest.raises(ValueError):
            await strategy.execute_with_fallback(providers, request)

        # Should not retry after first failure
        provider1.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_fallback_success_on_primary(self):
        """Test single fallback with primary succeeding."""
        strategy = LLMFallbackStrategy()

        primary = Mock()
        primary.get_name.return_value = "primary"
        primary.complete = AsyncMock(
            return_value=LLMResponse(
                content="primary success",
                prompt_tokens=10,
                completion_tokens=5,
                model="primary-model",
            )
        )

        fallback = Mock()
        fallback.get_name.return_value = "fallback"

        request = QueryRequest(query="test")

        response = await strategy.execute_with_single_fallback(
            primary, fallback, request
        )

        assert response.content == "primary success"
        primary.complete.assert_called_once()
        # Fallback should not be called
        assert not hasattr(fallback, "complete") or not fallback.complete.called

    @pytest.mark.asyncio
    async def test_execute_single_fallback_uses_fallback(self):
        """Test single fallback uses fallback on primary failure."""
        strategy = LLMFallbackStrategy()

        primary = Mock()
        primary.get_name.return_value = "primary"
        primary.complete = AsyncMock(side_effect=ValueError("Primary failed"))

        fallback = Mock()
        fallback.get_name.return_value = "fallback"
        fallback.complete = AsyncMock(
            return_value=LLMResponse(
                content="fallback success",
                prompt_tokens=10,
                completion_tokens=5,
                model="fallback-model",
            )
        )

        request = QueryRequest(query="test")

        response = await strategy.execute_with_single_fallback(
            primary, fallback, request
        )

        assert response.content == "fallback success"
        primary.complete.assert_called_once()
        fallback.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_fallback_both_fail(self):
        """Test single fallback when both providers fail."""
        strategy = LLMFallbackStrategy()

        primary = Mock()
        primary.get_name.return_value = "primary"
        primary.complete = AsyncMock(side_effect=ValueError("Primary error"))

        fallback = Mock()
        fallback.get_name.return_value = "fallback"
        fallback.complete = AsyncMock(side_effect=ValueError("Fallback error"))

        request = QueryRequest(query="test")

        with pytest.raises(LLMProviderError) as exc_info:
            await strategy.execute_with_single_fallback(primary, fallback, request)

        assert "Both providers failed" in str(exc_info.value)
        primary.complete.assert_called_once()
        fallback.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tries_providers_in_order(self):
        """Test providers are tried in provided order."""
        strategy = LLMFallbackStrategy()

        call_order = []

        provider1 = Mock()
        provider1.get_name.return_value = "provider1"

        async def provider1_complete(_):
            call_order.append("provider1")
            raise ValueError("Error 1")

        provider1.complete = provider1_complete

        provider2 = Mock()
        provider2.get_name.return_value = "provider2"

        async def provider2_complete(_):
            call_order.append("provider2")
            return LLMResponse(
                content="success", prompt_tokens=10, completion_tokens=5, model="model2"
            )

        provider2.complete = provider2_complete

        request = QueryRequest(query="test")
        providers = [provider1, provider2]

        await strategy.execute_with_fallback(providers, request)

        assert call_order == ["provider1", "provider2"]

    @pytest.mark.asyncio
    async def test_error_message_includes_last_error(self):
        """Test error message includes details of last error."""
        strategy = LLMFallbackStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "openai"
        provider1.complete = AsyncMock(side_effect=ValueError("Specific error message"))

        request = QueryRequest(query="test")
        providers = [provider1]

        with pytest.raises(LLMProviderError) as exc_info:
            await strategy.execute_with_fallback(providers, request)

        assert "Specific error message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_with_three_providers(self):
        """Test fallback through three providers."""
        strategy = LLMFallbackStrategy()

        provider1 = Mock()
        provider1.get_name.return_value = "provider1"
        provider1.complete = AsyncMock(side_effect=ValueError("Error 1"))

        provider2 = Mock()
        provider2.get_name.return_value = "provider2"
        provider2.complete = AsyncMock(side_effect=ValueError("Error 2"))

        provider3 = Mock()
        provider3.get_name.return_value = "provider3"
        provider3.complete = AsyncMock(
            return_value=LLMResponse(
                content="third time's the charm",
                prompt_tokens=10,
                completion_tokens=5,
                model="model3",
            )
        )

        request = QueryRequest(query="test")
        providers = [provider1, provider2, provider3]

        response = await strategy.execute_with_fallback(providers, request)

        assert response.content == "third time's the charm"
        provider1.complete.assert_called_once()
        provider2.complete.assert_called_once()
        provider3.complete.assert_called_once()
