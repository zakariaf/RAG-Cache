"""Unit tests for Parallel Cache Checking."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.cache_entry import CacheEntry
from app.pipeline.parallel_cache import (
    CacheResult,
    CacheSource,
    ParallelCacheChecker,
    check_caches_parallel,
)
from app.pipeline.semantic_matcher import SemanticMatch
from app.similarity.score_calculator import SimilarityLevel


class TestCacheResult:
    """Tests for CacheResult."""

    def test_miss(self):
        """Test cache miss result."""
        result = CacheResult.miss()
        assert result.source == CacheSource.NONE
        assert result.is_hit is False

    def test_from_exact(self):
        """Test exact cache hit result."""
        entry = CacheEntry(
            query_hash="hash",
            original_query="test",
            response="response",
            provider="openai",
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=20,
        )

        result = CacheResult.from_exact(entry)

        assert result.source == CacheSource.EXACT
        assert result.is_hit is True
        assert result.exact_entry is entry

    def test_from_semantic(self):
        """Test semantic cache hit result."""
        match = SemanticMatch(
            query_hash="hash",
            original_query="test",
            cached_response="response",
            similarity_score=0.9,
            similarity_level=SimilarityLevel.VERY_HIGH,
            provider="openai",
            model="gpt-4",
            point_id="point1",
        )

        result = CacheResult.from_semantic(match)

        assert result.source == CacheSource.SEMANTIC
        assert result.is_hit is True
        assert result.semantic_match is match


class TestParallelCacheChecker:
    """Tests for ParallelCacheChecker."""

    @pytest.fixture
    def mock_redis_cache(self):
        """Create mock Redis cache."""
        mock = MagicMock()
        mock.get = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def mock_semantic_matcher(self):
        """Create mock semantic matcher."""
        mock = MagicMock()
        mock.find_match = AsyncMock(return_value=None)
        return mock

    @pytest.mark.asyncio
    async def test_check_miss_all(self, mock_redis_cache, mock_semantic_matcher):
        """Test when both caches miss."""
        checker = ParallelCacheChecker(
            redis_cache=mock_redis_cache,
            semantic_matcher=mock_semantic_matcher,
        )

        result = await checker.check("test query")

        assert result.is_hit is False
        assert result.source == CacheSource.NONE

    @pytest.mark.asyncio
    async def test_check_exact_hit(self, mock_redis_cache, mock_semantic_matcher):
        """Test exact cache hit."""
        entry = CacheEntry(
            query_hash="hash",
            original_query="test",
            response="response",
            provider="openai",
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=20,
        )
        mock_redis_cache.get = AsyncMock(return_value=entry)

        checker = ParallelCacheChecker(
            redis_cache=mock_redis_cache,
            semantic_matcher=mock_semantic_matcher,
        )

        result = await checker.check("test query")

        assert result.is_hit is True
        assert result.source == CacheSource.EXACT

    @pytest.mark.asyncio
    async def test_check_semantic_hit(self, mock_redis_cache, mock_semantic_matcher):
        """Test semantic cache hit when exact misses."""
        match = SemanticMatch(
            query_hash="hash",
            original_query="similar",
            cached_response="response",
            similarity_score=0.9,
            similarity_level=SimilarityLevel.VERY_HIGH,
            provider="openai",
            model="gpt-4",
            point_id="point1",
        )
        mock_semantic_matcher.find_match = AsyncMock(return_value=match)

        checker = ParallelCacheChecker(
            redis_cache=mock_redis_cache,
            semantic_matcher=mock_semantic_matcher,
        )

        result = await checker.check("test query")

        assert result.is_hit is True
        assert result.source == CacheSource.SEMANTIC

    @pytest.mark.asyncio
    async def test_prefer_exact_over_semantic(
        self, mock_redis_cache, mock_semantic_matcher
    ):
        """Test exact is preferred when both hit."""
        entry = CacheEntry(
            query_hash="hash",
            original_query="test",
            response="exact response",
            provider="openai",
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=20,
        )
        match = SemanticMatch(
            query_hash="hash2",
            original_query="similar",
            cached_response="semantic response",
            similarity_score=0.9,
            similarity_level=SimilarityLevel.VERY_HIGH,
            provider="openai",
            model="gpt-4",
            point_id="point1",
        )

        mock_redis_cache.get = AsyncMock(return_value=entry)
        mock_semantic_matcher.find_match = AsyncMock(return_value=match)

        checker = ParallelCacheChecker(
            redis_cache=mock_redis_cache,
            semantic_matcher=mock_semantic_matcher,
            prefer_exact=True,
        )

        result = await checker.check("test query")

        assert result.source == CacheSource.EXACT

    @pytest.mark.asyncio
    async def test_check_no_caches_configured(self):
        """Test when no caches are configured."""
        checker = ParallelCacheChecker()

        result = await checker.check("test query")

        assert result.is_hit is False

    @pytest.mark.asyncio
    async def test_check_batch(self, mock_redis_cache, mock_semantic_matcher):
        """Test batch checking."""
        checker = ParallelCacheChecker(
            redis_cache=mock_redis_cache,
            semantic_matcher=mock_semantic_matcher,
        )

        results = await checker.check_batch(["q1", "q2", "q3"])

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_check_handles_cache_error(
        self, mock_redis_cache, mock_semantic_matcher
    ):
        """Test handling cache errors gracefully."""
        mock_redis_cache.get = AsyncMock(side_effect=Exception("cache error"))

        checker = ParallelCacheChecker(
            redis_cache=mock_redis_cache,
            semantic_matcher=mock_semantic_matcher,
        )

        result = await checker.check("test query")

        # Should not raise, just return miss
        assert result.is_hit is False


class TestCheckCachesParallel:
    """Tests for check_caches_parallel function."""

    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """Test convenience function works."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)

        result = await check_caches_parallel(
            query="test",
            redis_cache=mock_redis,
        )

        assert result is not None
        assert result.is_hit is False
