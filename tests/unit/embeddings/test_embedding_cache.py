"""Unit tests for Embedding Cache."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.embeddings.embedding_cache import EmbeddingCache


class TestEmbeddingCache:
    """Tests for EmbeddingCache class."""

    @pytest.fixture
    def mock_redis_cache(self):
        """Create mock Redis cache."""
        mock = MagicMock()
        mock.get_raw = AsyncMock(return_value=None)
        mock.set_raw = AsyncMock(return_value=True)
        mock.delete_raw = AsyncMock(return_value=True)
        mock.exists_raw = AsyncMock(return_value=False)
        return mock

    @pytest.fixture
    def cache(self, mock_redis_cache):
        """Create embedding cache with mock."""
        return EmbeddingCache(redis_cache=mock_redis_cache, ttl_seconds=3600)

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache, mock_redis_cache):
        """Test cache miss returns None."""
        mock_redis_cache.get_raw = AsyncMock(return_value=None)
        result = await cache.get("test text")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache, mock_redis_cache):
        """Test cache hit returns embedding."""
        embedding = [0.1, 0.2, 0.3]
        mock_redis_cache.get_raw = AsyncMock(
            return_value={"embedding": embedding, "model": "test-model"}
        )
        result = await cache.get("test text")
        assert result == embedding

    @pytest.mark.asyncio
    async def test_set_success(self, cache, mock_redis_cache):
        """Test successful cache set."""
        embedding = [0.1, 0.2, 0.3]
        result = await cache.set("test text", embedding)
        assert result is True
        mock_redis_cache.set_raw.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_failure(self, mock_redis_cache):
        """Test cache set failure."""
        mock_redis_cache.set_raw = AsyncMock(return_value=False)
        cache = EmbeddingCache(redis_cache=mock_redis_cache, ttl_seconds=3600)
        result = await cache.set("test text", [0.1, 0.2])
        assert result is False

    @pytest.mark.asyncio
    async def test_get_or_generate_cache_hit(self, cache, mock_redis_cache):
        """Test get_or_generate with cache hit."""
        cached_embedding = [0.1, 0.2, 0.3]
        mock_redis_cache.get_raw = AsyncMock(
            return_value={"embedding": cached_embedding}
        )

        generator = AsyncMock(return_value=[0.4, 0.5, 0.6])
        result = await cache.get_or_generate("test", generator)

        assert result == cached_embedding
        generator.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_generate_cache_miss(self, cache, mock_redis_cache):
        """Test get_or_generate with cache miss."""
        mock_redis_cache.get_raw = AsyncMock(return_value=None)
        generated_embedding = [0.4, 0.5, 0.6]

        generator = AsyncMock(return_value=generated_embedding)
        result = await cache.get_or_generate("test", generator)

        assert result == generated_embedding
        generator.assert_called_once_with("test")
        mock_redis_cache.set_raw.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate(self, cache, mock_redis_cache):
        """Test cache invalidation."""
        result = await cache.invalidate("test text")
        assert result is True
        mock_redis_cache.delete_raw.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists(self, cache, mock_redis_cache):
        """Test exists check."""
        mock_redis_cache.exists_raw = AsyncMock(return_value=True)
        result = await cache.exists("test text")
        assert result is True

    def test_ttl_property(self, cache):
        """Test TTL getter."""
        assert cache.ttl == 3600

    def test_set_ttl(self, cache):
        """Test TTL setter."""
        cache.set_ttl(7200)
        assert cache.ttl == 7200

    def test_make_key_consistency(self, cache):
        """Test key generation is consistent."""
        key1 = cache._make_key("test text")
        key2 = cache._make_key("test text")
        assert key1 == key2

    def test_make_key_different_for_different_text(self, cache):
        """Test different text produces different keys."""
        key1 = cache._make_key("text one")
        key2 = cache._make_key("text two")
        assert key1 != key2

