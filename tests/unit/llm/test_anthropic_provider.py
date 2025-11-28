"""
Tests for Anthropic LLM provider.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.anthropic_provider import AnthropicProvider
from app.exceptions import LLMProviderError
from app.models.query import QueryRequest


@pytest.fixture
def mock_rate_limiter():
    """Create mock rate limiter."""
    limiter = MagicMock()
    limiter.acquire = AsyncMock()
    return limiter


@pytest.fixture
def mock_retry_handler():
    """Create mock retry handler."""
    handler = MagicMock()
    handler.execute = AsyncMock()
    return handler


@pytest.fixture
def provider(mock_rate_limiter, mock_retry_handler):
    """Create Anthropic provider with mocks."""
    return AnthropicProvider(
        api_key="test-api-key",
        rate_limiter=mock_rate_limiter,
        retry_handler=mock_retry_handler,
    )


@pytest.fixture
def sample_request():
    """Create sample query request."""
    return QueryRequest(
        query="What is machine learning?",
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        temperature=0.7,
    )


class TestAnthropicProvider:
    """Test Anthropic provider functionality."""

    def test_get_name(self, provider):
        """Test provider name."""
        assert provider.get_name() == "anthropic"

    @pytest.mark.asyncio
    async def test_complete_success(self, provider, mock_retry_handler, sample_request):
        """Test successful completion."""
        from app.models.llm import LLMResponse

        mock_response = LLMResponse(
            content="Machine learning is a subset of AI...",
            prompt_tokens=10,
            completion_tokens=50,
            model="claude-3-5-sonnet-20241022",
        )
        mock_retry_handler.execute.return_value = mock_response

        result = await provider.complete(sample_request)

        assert result.content == "Machine learning is a subset of AI..."
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 50

    @pytest.mark.asyncio
    async def test_complete_acquires_rate_limit(
        self, provider, mock_rate_limiter, mock_retry_handler, sample_request
    ):
        """Test complete acquires rate limiter."""
        from app.models.llm import LLMResponse

        mock_retry_handler.execute.return_value = LLMResponse(
            content="test", prompt_tokens=1, completion_tokens=1, model="claude"
        )

        await provider.complete(sample_request)

        mock_rate_limiter.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_uses_retry_handler(
        self, provider, mock_retry_handler, sample_request
    ):
        """Test complete uses retry handler."""
        from app.models.llm import LLMResponse

        mock_retry_handler.execute.return_value = LLMResponse(
            content="test", prompt_tokens=1, completion_tokens=1, model="claude"
        )

        await provider.complete(sample_request)

        mock_retry_handler.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_anthropic_error(
        self, provider, mock_retry_handler, sample_request
    ):
        """Test complete handles Anthropic errors."""
        from anthropic import AnthropicError

        mock_retry_handler.execute.side_effect = AnthropicError("API Error")

        with pytest.raises(LLMProviderError) as exc_info:
            await provider.complete(sample_request)

        assert "Anthropic API call failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_complete_unexpected_error(
        self, provider, mock_retry_handler, sample_request
    ):
        """Test complete handles unexpected errors."""
        mock_retry_handler.execute.side_effect = Exception("Unexpected error")

        with pytest.raises(LLMProviderError) as exc_info:
            await provider.complete(sample_request)

        assert "Unexpected error" in str(exc_info.value)

    def test_get_client_creates_once(self, provider):
        """Test client is created once and reused."""
        with patch("app.llm.anthropic_provider.AsyncAnthropic") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            client1 = provider._get_client()
            client2 = provider._get_client()

            assert client1 is client2
            mock_client_class.assert_called_once()

    def test_init_with_custom_rate_limit(self):
        """Test initialization with custom rate limit."""
        provider = AnthropicProvider(
            api_key="test-key",
            requests_per_minute=100,
        )

        assert provider._rate_limiter is not None

    def test_init_creates_default_rate_limiter(self):
        """Test initialization creates default rate limiter."""
        provider = AnthropicProvider(api_key="test-key")

        assert provider._rate_limiter is not None

    def test_init_creates_default_retry_handler(self):
        """Test initialization creates default retry handler."""
        provider = AnthropicProvider(api_key="test-key")

        assert provider._retry_handler is not None


class TestAnthropicProviderMakeApiCall:
    """Test _make_api_call method."""

    @pytest.mark.asyncio
    async def test_make_api_call_with_default_model(self):
        """Test API call uses Claude model when default."""
        with patch("app.llm.anthropic_provider.AsyncAnthropic") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Response text")]
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 20
            mock_response.model = "claude-3-5-sonnet-20241022"
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            provider = AnthropicProvider(api_key="test-key")
            request = QueryRequest(query="test query")

            result = await provider._make_api_call(request)

            assert result.content == "Response text"
            assert result.prompt_tokens == 10
            assert result.completion_tokens == 20

    @pytest.mark.asyncio
    async def test_make_api_call_with_custom_model(self):
        """Test API call uses specified model."""
        with patch("app.llm.anthropic_provider.AsyncAnthropic") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Response")]
            mock_response.usage.input_tokens = 5
            mock_response.usage.output_tokens = 10
            mock_response.model = "claude-3-opus-20240229"
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            provider = AnthropicProvider(api_key="test-key")
            request = QueryRequest(query="test", model="claude-3-opus-20240229")

            result = await provider._make_api_call(request)

            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "claude-3-opus-20240229"
