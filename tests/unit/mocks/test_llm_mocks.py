"""Tests for LLM provider mocks."""

import pytest

from app.models.query import QueryRequest
from tests.mocks.llm_mocks import (
    CountingMockProvider,
    FailingMockProvider,
    MockAnthropicProvider,
    MockLLMProvider,
    MockOpenAIProvider,
)


class TestMockLLMProvider:
    """Test generic mock LLM provider."""

    @pytest.mark.asyncio
    async def test_default_response(self):
        """Test default mock response."""
        provider = MockLLMProvider()
        request = QueryRequest(query="test")

        response = await provider.complete(request)

        assert response.content == "mock response"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 5
        assert response.model == "mock-model"

    @pytest.mark.asyncio
    async def test_custom_response(self):
        """Test custom mock response."""
        provider = MockLLMProvider(
            name="custom",
            response_content="custom response",
            prompt_tokens=100,
            completion_tokens=50,
            model="custom-model",
        )
        request = QueryRequest(query="test")

        response = await provider.complete(request)

        assert response.content == "custom response"
        assert response.prompt_tokens == 100
        assert response.completion_tokens == 50
        assert response.model == "custom-model"

    @pytest.mark.asyncio
    async def test_should_fail(self):
        """Test provider that fails."""
        provider = MockLLMProvider(should_fail=True, failure_message="Test error")
        request = QueryRequest(query="test")

        with pytest.raises(Exception) as exc_info:
            await provider.complete(request)

        assert "Test error" in str(exc_info.value)

    def test_get_name(self):
        """Test getting provider name."""
        provider = MockLLMProvider(name="test-provider")

        assert provider.get_name() == "test-provider"

    @pytest.mark.asyncio
    async def test_call_count(self):
        """Test call counting."""
        provider = MockLLMProvider()
        request = QueryRequest(query="test")

        assert provider.get_call_count() == 0

        await provider.complete(request)
        assert provider.get_call_count() == 1

        await provider.complete(request)
        assert provider.get_call_count() == 2

    @pytest.mark.asyncio
    async def test_reset_call_count(self):
        """Test resetting call count."""
        provider = MockLLMProvider()
        request = QueryRequest(query="test")

        await provider.complete(request)
        await provider.complete(request)
        assert provider.get_call_count() == 2

        provider.reset_call_count()
        assert provider.get_call_count() == 0

    @pytest.mark.asyncio
    async def test_set_should_fail(self):
        """Test changing failure behavior."""
        provider = MockLLMProvider()
        request = QueryRequest(query="test")

        # Initially succeeds
        response = await provider.complete(request)
        assert response.content == "mock response"

        # Change to fail
        provider.set_should_fail(True)
        with pytest.raises(Exception):
            await provider.complete(request)

        # Change back to succeed
        provider.set_should_fail(False)
        response = await provider.complete(request)
        assert response.content == "mock response"

    @pytest.mark.asyncio
    async def test_set_response_content(self):
        """Test changing response content."""
        provider = MockLLMProvider()
        request = QueryRequest(query="test")

        response = await provider.complete(request)
        assert response.content == "mock response"

        provider.set_response_content("new content")

        response = await provider.complete(request)
        assert response.content == "new content"


class TestMockOpenAIProvider:
    """Test mock OpenAI provider."""

    @pytest.mark.asyncio
    async def test_response(self):
        """Test OpenAI mock response."""
        provider = MockOpenAIProvider()
        request = QueryRequest(query="test")

        response = await provider.complete(request)

        assert "OpenAI" in response.content
        assert response.prompt_tokens == 50
        assert response.completion_tokens == 25
        assert response.model == "gpt-3.5-turbo"

    def test_get_name(self):
        """Test provider name."""
        provider = MockOpenAIProvider()

        assert provider.get_name() == "openai"

    @pytest.mark.asyncio
    async def test_failure(self):
        """Test failing OpenAI provider."""
        provider = MockOpenAIProvider(should_fail=True)
        request = QueryRequest(query="test")

        with pytest.raises(Exception) as exc_info:
            await provider.complete(request)

        assert "OpenAI" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_count(self):
        """Test call counting."""
        provider = MockOpenAIProvider()
        request = QueryRequest(query="test")

        await provider.complete(request)
        await provider.complete(request)

        assert provider.get_call_count() == 2


class TestMockAnthropicProvider:
    """Test mock Anthropic provider."""

    @pytest.mark.asyncio
    async def test_response(self):
        """Test Anthropic mock response."""
        provider = MockAnthropicProvider()
        request = QueryRequest(query="test")

        response = await provider.complete(request)

        assert "Claude" in response.content
        assert response.prompt_tokens == 60
        assert response.completion_tokens == 30
        assert "claude" in response.model

    def test_get_name(self):
        """Test provider name."""
        provider = MockAnthropicProvider()

        assert provider.get_name() == "anthropic"

    @pytest.mark.asyncio
    async def test_failure(self):
        """Test failing Anthropic provider."""
        provider = MockAnthropicProvider(should_fail=True)
        request = QueryRequest(query="test")

        with pytest.raises(Exception) as exc_info:
            await provider.complete(request)

        assert "Anthropic" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_count(self):
        """Test call counting."""
        provider = MockAnthropicProvider()
        request = QueryRequest(query="test")

        await provider.complete(request)
        await provider.complete(request)
        await provider.complete(request)

        assert provider.get_call_count() == 3


class TestFailingMockProvider:
    """Test always-failing mock provider."""

    @pytest.mark.asyncio
    async def test_always_fails(self):
        """Test provider always fails."""
        provider = FailingMockProvider()
        request = QueryRequest(query="test")

        with pytest.raises(Exception) as exc_info:
            await provider.complete(request)

        assert "Mock error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_custom_error_message(self):
        """Test custom error message."""
        provider = FailingMockProvider(error_message="Custom failure")
        request = QueryRequest(query="test")

        with pytest.raises(Exception) as exc_info:
            await provider.complete(request)

        assert "Custom failure" in str(exc_info.value)

    def test_get_name(self):
        """Test provider name."""
        provider = FailingMockProvider(name="test-failing")

        assert provider.get_name() == "test-failing"

    @pytest.mark.asyncio
    async def test_call_count_increments(self):
        """Test call count increments even on failure."""
        provider = FailingMockProvider()
        request = QueryRequest(query="test")

        for _ in range(3):
            with pytest.raises(Exception):
                await provider.complete(request)

        assert provider.get_call_count() == 3


class TestCountingMockProvider:
    """Test counting mock provider."""

    @pytest.mark.asyncio
    async def test_tracks_requests(self):
        """Test request tracking."""
        provider = CountingMockProvider()
        request = QueryRequest(query="test query")

        await provider.complete(request)

        assert provider.get_call_count() == 1
        last_request = provider.get_last_request()
        assert last_request is not None
        assert last_request.query == "test query"

    @pytest.mark.asyncio
    async def test_response_numbering(self):
        """Test response numbering."""
        provider = CountingMockProvider()
        request = QueryRequest(query="test")

        response1 = await provider.complete(request)
        response2 = await provider.complete(request)
        response3 = await provider.complete(request)

        assert "1" in response1.content
        assert "2" in response2.content
        assert "3" in response3.content

    @pytest.mark.asyncio
    async def test_get_all_requests(self):
        """Test getting all requests."""
        provider = CountingMockProvider()

        await provider.complete(QueryRequest(query="first"))
        await provider.complete(QueryRequest(query="second"))
        await provider.complete(QueryRequest(query="third"))

        requests = provider.get_all_requests()

        assert len(requests) == 3
        assert requests[0].query == "first"
        assert requests[1].query == "second"
        assert requests[2].query == "third"

    @pytest.mark.asyncio
    async def test_get_last_request_empty(self):
        """Test get_last_request when no calls."""
        provider = CountingMockProvider()

        assert provider.get_last_request() is None

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test resetting provider."""
        provider = CountingMockProvider()
        request = QueryRequest(query="test")

        await provider.complete(request)
        await provider.complete(request)

        assert provider.get_call_count() == 2
        assert len(provider.get_all_requests()) == 2

        provider.reset()

        assert provider.get_call_count() == 0
        assert len(provider.get_all_requests()) == 0
        assert provider.get_last_request() is None

    def test_get_name(self):
        """Test provider name."""
        provider = CountingMockProvider(name="custom-counter")

        assert provider.get_name() == "custom-counter"
