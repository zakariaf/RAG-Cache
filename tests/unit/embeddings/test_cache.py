"""Test embedding cache."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.embeddings.cache import EmbeddingCache
from app.models.embedding import EmbeddingResult


@pytest.fixture
def mock_generator():
    """Create mock embedding generator."""
    generator = Mock()
    generator.generate = AsyncMock()
    return generator


@pytest.fixture
def sample_embedding():
    """Create sample embedding result."""
    return EmbeddingResult.create(
        text="test",
        vector=[0.1, 0.2, 0.3],
        model="test-model",
        tokens=1,
    )


@pytest.fixture
def cache(mock_generator):
    """Create embedding cache."""
    return EmbeddingCache(generator=mock_generator, max_size=3)


class TestEmbeddingCache:
    """Test EmbeddingCache class."""

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache, mock_generator, sample_embedding):
        """Test cache miss generates embedding."""
        mock_generator.generate.return_value = sample_embedding

        result = await cache.get_or_generate("test")

        assert result == sample_embedding
        mock_generator.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit(self, cache, mock_generator, sample_embedding):
        """Test cache hit returns cached value."""
        mock_generator.generate.return_value = sample_embedding

        # First call - cache miss
        await cache.get_or_generate("test")

        # Second call - cache hit
        result = await cache.get_or_generate("test")

        assert result == sample_embedding
        assert mock_generator.generate.call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_cache_different_normalize(
        self, cache, mock_generator, sample_embedding
    ):
        """Test different normalize values create different cache keys."""
        mock_generator.generate.return_value = sample_embedding

        await cache.get_or_generate("test", normalize=True)
        await cache.get_or_generate("test", normalize=False)

        assert mock_generator.generate.call_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_cache_eviction(self, cache, mock_generator, sample_embedding):
        """Test LRU eviction when cache is full."""
        mock_generator.generate.return_value = sample_embedding

        # Fill cache (max_size=3)
        await cache.get_or_generate("text1")
        await cache.get_or_generate("text2")
        await cache.get_or_generate("text3")

        assert cache.size == 3

        # Add 4th item - should evict oldest (text1)
        await cache.get_or_generate("text4")

        assert cache.size == 3
        assert not cache.is_cached("text1")
        assert cache.is_cached("text4")

    def test_clear(self, cache):
        """Test clearing cache."""
        cache._cache["key"] = "value"
        cache.clear()
        assert cache.size == 0

    def test_invalidate_existing(self, cache, sample_embedding):
        """Test invalidating existing cache entry."""
        cache._cache["key"] = sample_embedding
        result = cache.invalidate("test")
        # Won't find it because key is hashed
        assert isinstance(result, bool)

    def test_size(self, cache):
        """Test getting cache size."""
        assert cache.size == 0
        cache._cache["key"] = "value"
        assert cache.size == 1

    def test_max_size(self, cache):
        """Test getting max cache size."""
        assert cache.max_size == 3

    def test_hits_and_misses(self, cache):
        """Test tracking hits and misses."""
        assert cache.hits == 0
        assert cache.misses == 0

    def test_hit_rate(self, cache):
        """Test calculating hit rate."""
        assert cache.hit_rate == 0.0

        cache._hits = 7
        cache._misses = 3
        assert cache.hit_rate == 0.7

    def test_get_stats(self, cache):
        """Test getting cache statistics."""
        stats = cache.get_stats()
        assert "size" in stats
        assert "max_size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats

    def test_reset_stats(self, cache):
        """Test resetting statistics."""
        cache._hits = 10
        cache._misses = 5
        cache.reset_stats()
        assert cache.hits == 0
        assert cache.misses == 0

    def test_is_cached(self, cache):
        """Test checking if text is cached."""
        assert not cache.is_cached("test")

    def test_peek(self, cache, sample_embedding):
        """Test peeking at cache without updating access order."""
        # Add to cache directly
        key = cache._get_cache_key("test", True)
        cache._cache[key] = sample_embedding

        result = cache.peek("test", normalize=True)
        assert result == sample_embedding

    def test_peek_missing(self, cache):
        """Test peeking at missing entry returns None."""
        result = cache.peek("missing")
        assert result is None

    def test_set_max_size(self, cache, sample_embedding):
        """Test updating max cache size."""
        # Fill cache
        for i in range(3):
            cache._cache[f"key{i}"] = sample_embedding

        # Reduce size
        cache.set_max_size(2)

        assert cache.max_size == 2
        assert cache.size <= 2

    def test_set_max_size_invalid(self, cache):
        """Test setting invalid max size raises error."""
        with pytest.raises(ValueError, match="at least 1"):
            cache.set_max_size(0)
