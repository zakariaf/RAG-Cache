"""
Integration tests for Query Pipeline.

Tests the full query processing flow including:
- Exact cache
- Semantic cache
- LLM calls
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.cache_entry import CacheEntry
from app.models.qdrant_point import SearchResult
from app.models.query import QueryRequest
from app.pipeline.semantic_matcher import SemanticMatcher
from app.services.query_service import QueryService


class TestQueryPipelineFlow:
    """Integration tests for full query pipeline."""

    @pytest.fixture
    def mock_redis_cache(self):
        """Create mock Redis cache."""
        mock = MagicMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider."""
        mock = MagicMock()
        mock.get_name = MagicMock(return_value="openai")
        mock.complete = AsyncMock(
            return_value=MagicMock(
                content="LLM response",
                model="gpt-4",
                prompt_tokens=10,
                completion_tokens=20,
            )
        )
        return mock

    @pytest.fixture
    def mock_embedding_generator(self):
        """Create mock embedding generator."""
        mock = MagicMock()
        mock.generate = AsyncMock(return_value=[0.1] * 384)
        return mock

    @pytest.fixture
    def mock_qdrant_repository(self):
        """Create mock Qdrant repository."""
        mock = MagicMock()
        mock.search_similar = AsyncMock(return_value=[])
        mock.store_point = AsyncMock(return_value=True)
        mock.ping = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def semantic_matcher(self, mock_embedding_generator, mock_qdrant_repository):
        """Create semantic matcher with mocks."""
        return SemanticMatcher(
            embedding_generator=mock_embedding_generator,
            qdrant_repository=mock_qdrant_repository,
            similarity_threshold=0.85,
        )

    @pytest.fixture
    def query_service(self, mock_redis_cache, mock_llm_provider, semantic_matcher):
        """Create query service with all dependencies."""
        return QueryService(
            cache=mock_redis_cache,
            llm_provider=mock_llm_provider,
            semantic_matcher=semantic_matcher,
        )

    @pytest.mark.asyncio
    async def test_exact_cache_hit(
        self, query_service, mock_redis_cache, mock_llm_provider
    ):
        """Test exact cache hit returns cached response."""
        cached_entry = CacheEntry(
            query_hash="hash123",
            original_query="What is Python?",
            response="Python is a programming language",
            provider="openai",
            model="gpt-4",
            prompt_tokens=5,
            completion_tokens=10,
            embedding=None,
        )
        mock_redis_cache.get = AsyncMock(return_value=cached_entry)

        request = QueryRequest(query="What is Python?", use_cache=True)
        response = await query_service.process(request)

        assert response.from_cache is True
        assert response.is_exact_match is True
        assert response.response == "Python is a programming language"
        mock_llm_provider.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_semantic_cache_hit(
        self, query_service, mock_redis_cache, mock_qdrant_repository, mock_llm_provider
    ):
        """Test semantic cache hit returns similar cached response."""
        mock_redis_cache.get = AsyncMock(return_value=None)

        # Set up semantic match
        search_result = SearchResult(
            point_id="point1",
            score=0.92,
            vector=None,
            payload={
                "query_hash": "hash456",
                "original_query": "What is the Python language?",
                "response": "Python is a versatile programming language",
                "provider": "openai",
                "model": "gpt-4",
            },
        )
        mock_qdrant_repository.search_similar = AsyncMock(return_value=[search_result])

        request = QueryRequest(query="Tell me about Python", use_cache=True)
        response = await query_service.process(request)

        assert response.from_cache is True
        assert response.is_semantic_match is True
        assert response.cache_info.similarity_score == 0.92
        mock_llm_provider.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_calls_llm(
        self, query_service, mock_redis_cache, mock_qdrant_repository, mock_llm_provider
    ):
        """Test cache miss calls LLM provider."""
        mock_redis_cache.get = AsyncMock(return_value=None)
        mock_qdrant_repository.search_similar = AsyncMock(return_value=[])

        request = QueryRequest(query="What is new in Python 3.12?", use_cache=True)
        response = await query_service.process(request)

        assert response.from_cache is False
        assert response.response == "LLM response"
        mock_llm_provider.complete.assert_called_once()
        mock_redis_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_bypass_cache(
        self, query_service, mock_redis_cache, mock_llm_provider
    ):
        """Test bypassing cache when use_cache is False."""
        request = QueryRequest(query="What is Python?", use_cache=False)
        response = await query_service.process(request)

        assert response.from_cache is False
        mock_redis_cache.get.assert_not_called()
        mock_llm_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_stores_in_both_caches_on_miss(
        self, query_service, mock_redis_cache, mock_qdrant_repository
    ):
        """Test response stored in both caches on miss."""
        mock_redis_cache.get = AsyncMock(return_value=None)
        mock_qdrant_repository.search_similar = AsyncMock(return_value=[])

        request = QueryRequest(query="New question", use_cache=True)
        await query_service.process(request)

        mock_redis_cache.set.assert_called_once()
        mock_qdrant_repository.store_point.assert_called_once()


class TestQueryPreprocessingIntegration:
    """Integration tests for query preprocessing."""

    @pytest.mark.asyncio
    async def test_normalized_queries_hit_cache(self):
        """Test normalized queries hit same cache entry."""
        from app.pipeline.query_normalizer import normalize_query
        from app.utils.hasher import generate_cache_key

        # Different formatting, same semantic meaning
        queries = [
            "  What is Python?  ",
            "what is python?",
            "WHAT IS PYTHON?",
        ]

        # All should normalize to same key
        normalized = [normalize_query(q) for q in queries]
        assert len(set(normalized)) == 1  # All same

        # All should produce same cache key
        keys = [generate_cache_key(n) for n in normalized]
        assert len(set(keys)) == 1  # All same

    @pytest.mark.asyncio
    async def test_validation_blocks_invalid_queries(self):
        """Test validation blocks invalid queries."""
        from app.exceptions import ValidationError
        from app.pipeline.query_validator import QueryValidator

        validator = QueryValidator()

        with pytest.raises(ValidationError):
            validator.validate_or_raise("")

        with pytest.raises(ValidationError):
            validator.validate_or_raise(None)


class TestSemanticMatchingIntegration:
    """Integration tests for semantic matching."""

    @pytest.fixture
    def mock_embedding_generator(self):
        """Create mock embedding generator."""
        mock = MagicMock()
        mock.generate = AsyncMock(return_value=[0.1] * 384)
        return mock

    @pytest.fixture
    def mock_qdrant_repository(self):
        """Create mock Qdrant repository."""
        mock = MagicMock()
        mock.search_similar = AsyncMock(return_value=[])
        mock.store_point = AsyncMock(return_value=True)
        mock.ping = AsyncMock(return_value=True)
        return mock

    @pytest.mark.asyncio
    async def test_high_similarity_returns_match(
        self, mock_embedding_generator, mock_qdrant_repository
    ):
        """Test high similarity score returns match."""
        matcher = SemanticMatcher(
            embedding_generator=mock_embedding_generator,
            qdrant_repository=mock_qdrant_repository,
            similarity_threshold=0.85,
        )

        search_result = SearchResult(
            point_id="point1",
            score=0.95,
            vector=None,
            payload={
                "query_hash": "hash1",
                "original_query": "Similar query",
                "response": "Cached response",
                "provider": "openai",
                "model": "gpt-4",
            },
        )
        mock_qdrant_repository.search_similar = AsyncMock(return_value=[search_result])

        match = await matcher.find_match("Test query")

        assert match is not None
        assert match.similarity_score == 0.95
        assert match.is_high_quality is True

    @pytest.mark.asyncio
    async def test_low_similarity_returns_none(
        self, mock_embedding_generator, mock_qdrant_repository
    ):
        """Test low similarity score returns None."""
        matcher = SemanticMatcher(
            embedding_generator=mock_embedding_generator,
            qdrant_repository=mock_qdrant_repository,
            similarity_threshold=0.85,
        )

        # No results above threshold
        mock_qdrant_repository.search_similar = AsyncMock(return_value=[])

        match = await matcher.find_match("Unrelated query")

        assert match is None


class TestRequestContextIntegration:
    """Integration tests for request context."""

    @pytest.mark.asyncio
    async def test_context_tracks_cache_operations(self):
        """Test request context tracks cache operations."""
        from app.pipeline.request_context import (
            end_request,
            get_current_context,
            start_request,
        )

        ctx = start_request("Test query")

        # Simulate cache check
        ctx.mark_cache_checked(hit=False)
        ctx.mark_semantic_checked(hit=True)

        current = get_current_context()
        assert current.cache_checked is True
        assert current.cache_hit is False
        assert current.semantic_checked is True
        assert current.semantic_hit is True

        final = end_request()
        assert final.is_complete is True
        assert final.elapsed_ms > 0

    @pytest.mark.asyncio
    async def test_context_isolated_per_request(self):
        """Test contexts are isolated per request."""
        from app.pipeline.request_context import (
            end_request,
            get_current_context,
            start_request,
        )

        # First request
        ctx1 = start_request("Query 1")
        id1 = ctx1.request_id
        end_request()

        # Second request
        ctx2 = start_request("Query 2")
        id2 = ctx2.request_id
        end_request()

        # IDs should be different
        assert id1 != id2
