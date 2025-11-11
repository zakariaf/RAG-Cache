"""Test query service."""

import pytest
from unittest.mock import AsyncMock

from app.services.query_service import QueryService
from app.models.query import QueryRequest
from app.models.llm import LLMResponse
from app.models.cache_entry import CacheEntry


@pytest.fixture
def mock_cache():
    """Create mock cache."""
    return AsyncMock()


@pytest.fixture
def mock_llm():
    """Create mock LLM provider."""
    llm = AsyncMock()
    llm.get_name.return_value = "openai"
    return llm


@pytest.fixture
def query_service(mock_cache, mock_llm):
    """Create query service with mocks."""
    return QueryService(cache=mock_cache, llm_provider=mock_llm)


@pytest.fixture
def sample_request():
    """Create sample query request."""
    return QueryRequest(query="What is Python?", use_cache=True)


@pytest.fixture
def sample_llm_response():
    """Create sample LLM response."""
    return LLMResponse(
        content="Python is a programming language",
        prompt_tokens=10,
        completion_tokens=20,
        model="gpt-3.5-turbo",
    )


@pytest.fixture
def sample_cache_entry():
    """Create sample cache entry."""
    return CacheEntry(
        query_hash="test_hash",
        original_query="What is Python?",
        response="Python is a programming language",
        provider="openai",
        model="gpt-3.5-turbo",
        prompt_tokens=10,
        completion_tokens=20,
        embedding=None,
    )


class TestQueryService:
    """Test query service implementation."""

    @pytest.mark.asyncio
    async def test_should_return_cached_response(
        self, query_service, mock_cache, sample_request, sample_cache_entry
    ):
        """Test returning cached response."""
        mock_cache.get.return_value = sample_cache_entry

        response = await query_service.process(sample_request)

        assert response.response == "Python is a programming language"
        assert response.from_cache is True
        assert response.is_exact_match is True
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_call_llm_on_cache_miss(
        self, query_service, mock_cache, mock_llm, sample_request, sample_llm_response
    ):
        """Test calling LLM on cache miss."""
        mock_cache.get.return_value = None
        mock_llm.complete.return_value = sample_llm_response

        response = await query_service.process(sample_request)

        assert response.response == "Python is a programming language"
        assert response.from_cache is False
        mock_cache.get.assert_called_once()
        mock_llm.complete.assert_called_once()
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_store_llm_response_in_cache(
        self, query_service, mock_cache, mock_llm, sample_request, sample_llm_response
    ):
        """Test storing LLM response in cache."""
        mock_cache.get.return_value = None
        mock_llm.complete.return_value = sample_llm_response

        await query_service.process(sample_request)

        mock_cache.set.assert_called_once()
        # Verify the entry being stored
        stored_entry = mock_cache.set.call_args[0][0]
        assert stored_entry.response == "Python is a programming language"
        assert stored_entry.provider == "openai"

    @pytest.mark.asyncio
    async def test_should_skip_cache_when_disabled(
        self, query_service, mock_cache, mock_llm, sample_llm_response
    ):
        """Test skipping cache when disabled."""
        request = QueryRequest(query="What is Python?", use_cache=False)
        mock_llm.complete.return_value = sample_llm_response

        response = await query_service.process(request)

        assert response.response == "Python is a programming language"
        assert response.from_cache is False
        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_cache_error_gracefully(
        self, query_service, mock_cache, mock_llm, sample_request, sample_llm_response
    ):
        """Test handling cache errors gracefully."""
        mock_cache.get.side_effect = Exception("Cache error")
        mock_llm.complete.return_value = sample_llm_response

        response = await query_service.process(sample_request)

        assert response.response == "Python is a programming language"
        assert response.from_cache is False
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_cache_store_error(
        self, query_service, mock_cache, mock_llm, sample_request, sample_llm_response
    ):
        """Test handling cache store errors."""
        mock_cache.get.return_value = None
        mock_cache.set.side_effect = Exception("Store error")
        mock_llm.complete.return_value = sample_llm_response

        # Should not raise exception
        response = await query_service.process(sample_request)

        assert response.response == "Python is a programming language"
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_include_usage_metrics(
        self, query_service, mock_cache, mock_llm, sample_request, sample_llm_response
    ):
        """Test including usage metrics in response."""
        mock_cache.get.return_value = None
        mock_llm.complete.return_value = sample_llm_response

        response = await query_service.process(sample_request)

        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30

    @pytest.mark.asyncio
    async def test_should_include_latency(
        self, query_service, mock_cache, mock_llm, sample_request, sample_llm_response
    ):
        """Test including latency in response."""
        mock_cache.get.return_value = None
        mock_llm.complete.return_value = sample_llm_response

        response = await query_service.process(sample_request)

        assert response.latency_ms >= 0
        assert isinstance(response.latency_ms, float)
