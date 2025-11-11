"""Test OpenAI LLM provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openai import OpenAIError

from app.llm.openai_provider import OpenAIProvider
from app.models.query import QueryRequest
from app.exceptions import LLMProviderError


@pytest.fixture
def openai_provider():
    """Create OpenAI provider with test API key."""
    return OpenAIProvider(api_key="test-api-key")


@pytest.fixture
def sample_request():
    """Create sample query request."""
    return QueryRequest(query="What is Python?")


@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI API response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Python is a programming language"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.model = "gpt-3.5-turbo"
    return mock_response


class TestOpenAIProvider:
    """Test OpenAI provider implementation."""

    def test_should_get_provider_name(self, openai_provider):
        """Test getting provider name."""
        assert openai_provider.get_name() == "openai"

    @pytest.mark.asyncio
    async def test_should_complete_query(
        self, openai_provider, sample_request, mock_openai_response
    ):
        """Test completing query with OpenAI."""
        with patch("app.llm.openai_provider.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_openai_response
            mock_client_class.return_value = mock_client

            response = await openai_provider.complete(sample_request)

            assert response.content == "Python is a programming language"
            assert response.prompt_tokens == 10
            assert response.completion_tokens == 20
            assert response.total_tokens == 30
            assert response.model == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_should_handle_openai_error(self, openai_provider, sample_request):
        """Test handling OpenAI API errors."""
        with patch("app.llm.openai_provider.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = OpenAIError("API Error")
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMProviderError, match="OpenAI API call failed"):
                await openai_provider.complete(sample_request)

    @pytest.mark.asyncio
    async def test_should_handle_unexpected_error(
        self, openai_provider, sample_request
    ):
        """Test handling unexpected errors."""
        with patch("app.llm.openai_provider.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = RuntimeError(
                "Unexpected error"
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(
                LLMProviderError, match="Unexpected error in OpenAI provider"
            ):
                await openai_provider.complete(sample_request)

    @pytest.mark.asyncio
    async def test_should_use_custom_parameters(
        self, openai_provider, mock_openai_response
    ):
        """Test using custom request parameters."""
        with patch("app.llm.openai_provider.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_openai_response
            mock_client_class.return_value = mock_client

            request = QueryRequest(
                query="Test query",
                model="gpt-4",
                max_tokens=500,
                temperature=0.7,
            )

            await openai_provider.complete(request)

            # Verify the call was made with custom parameters
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["model"] == "gpt-4"
            assert call_args.kwargs["max_tokens"] == 500
            assert call_args.kwargs["temperature"] == 0.7
