"""Test Redis cache service."""

from unittest.mock import AsyncMock

import pytest

from app.cache.redis_cache import RedisCache
from app.models.cache_entry import CacheEntry
from app.models.statistics import RedisMetrics


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    repository = AsyncMock()
    return repository


@pytest.fixture
def redis_cache(mock_repository):
    """Create Redis cache with mock repository."""
    return RedisCache(repository=mock_repository)


@pytest.fixture
def sample_entry():
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


class TestRedisCache:
    """Test Redis cache service."""

    @pytest.mark.asyncio
    async def test_should_get_cached_entry(
        self, redis_cache, mock_repository, sample_entry
    ):
        """Test getting cached entry."""
        mock_repository.fetch.return_value = sample_entry

        result = await redis_cache.get("What is Python?")

        assert result == sample_entry
        mock_repository.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_return_none_when_not_cached(
        self, redis_cache, mock_repository
    ):
        """Test getting non-cached entry."""
        mock_repository.fetch.return_value = None

        result = await redis_cache.get("What is Python?")

        assert result is None
        mock_repository.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_set_cache_entry(
        self, redis_cache, mock_repository, sample_entry
    ):
        """Test setting cache entry."""
        mock_repository.store.return_value = True

        result = await redis_cache.set(sample_entry)

        assert result is True
        mock_repository.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_set_failure(
        self, redis_cache, mock_repository, sample_entry
    ):
        """Test handling cache set failure."""
        mock_repository.store.return_value = False

        result = await redis_cache.set(sample_entry)

        assert result is False
        mock_repository.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_delete_cache_entry(self, redis_cache, mock_repository):
        """Test deleting cache entry."""
        mock_repository.delete.return_value = True

        result = await redis_cache.delete("What is Python?")

        assert result is True
        mock_repository.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_check_if_exists(self, redis_cache, mock_repository):
        """Test checking if entry exists."""
        mock_repository.exists.return_value = True

        result = await redis_cache.exists("What is Python?")

        assert result is True
        mock_repository.exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_check_health(self, redis_cache, mock_repository):
        """Test health check."""
        mock_repository.ping.return_value = True

        result = await redis_cache.health_check()

        assert result is True
        mock_repository.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_invalidate_by_pattern(self, redis_cache, mock_repository):
        """Test invalidating cache by pattern."""
        mock_repository.delete_by_pattern.return_value = 5

        result = await redis_cache.invalidate_by_pattern("cache:*")

        assert result == 5
        mock_repository.delete_by_pattern.assert_called_once_with("cache:*")

    @pytest.mark.asyncio
    async def test_should_invalidate_all(self, redis_cache, mock_repository):
        """Test invalidating all cache entries."""
        mock_repository.clear_all.return_value = True

        result = await redis_cache.invalidate_all()

        assert result is True
        mock_repository.clear_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_get_cached_queries(self, redis_cache, mock_repository):
        """Test getting cached query keys."""
        mock_keys = ["key1", "key2", "key3"]
        mock_repository.get_keys_by_pattern.return_value = mock_keys

        result = await redis_cache.get_cached_queries("*")

        assert result == mock_keys
        mock_repository.get_keys_by_pattern.assert_called_once_with("*")

    @pytest.mark.asyncio
    async def test_should_get_metrics(self, redis_cache, mock_repository):
        """Test getting Redis metrics."""
        mock_metrics = RedisMetrics(
            total_keys=100,
            memory_used_bytes=1024000,
            memory_peak_bytes=2048000,
            total_connections=50,
            connected_clients=5,
            total_commands_processed=1000,
            uptime_seconds=3600,
            hits=80,
            misses=20,
            evicted_keys=5,
            expired_keys=10,
        )
        mock_repository.get_metrics.return_value = mock_metrics

        result = await redis_cache.get_metrics()

        assert result == mock_metrics
        assert result.hit_rate == 80.0
        mock_repository.get_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_get_cache_size(self, redis_cache, mock_repository):
        """Test getting cache size."""
        mock_repository.get_key_count.return_value = 42

        result = await redis_cache.get_cache_size()

        assert result == 42
        mock_repository.get_key_count.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_get_entry_memory(self, redis_cache, mock_repository):
        """Test getting entry memory usage."""
        mock_repository.get_memory_usage.return_value = 1024

        result = await redis_cache.get_entry_memory("What is Python?")

        assert result == 1024
        mock_repository.get_memory_usage.assert_called_once()
