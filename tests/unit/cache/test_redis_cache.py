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

    @pytest.mark.asyncio
    async def test_should_batch_set(self, redis_cache, mock_repository, sample_entry):
        """Test batch setting cache entries."""
        entries = [sample_entry]
        mock_repository.batch_store.return_value = 1

        result = await redis_cache.batch_set(entries)

        assert result == 1
        mock_repository.batch_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_batch_get(self, redis_cache, mock_repository, sample_entry):
        """Test batch getting cache entries."""
        queries = ["What is Python?", "What is Java?"]
        mock_repository.batch_fetch.return_value = {
            "test_hash": sample_entry,
            "test_hash_2": None,
        }

        result = await redis_cache.batch_get(queries)

        assert len(result) == 2
        mock_repository.batch_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_batch_delete(self, redis_cache, mock_repository):
        """Test batch deleting cache entries."""
        queries = ["What is Python?", "What is Java?"]
        mock_repository.batch_delete.return_value = 2

        result = await redis_cache.batch_delete(queries)

        assert result == 2
        mock_repository.batch_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_batch_exists(self, redis_cache, mock_repository):
        """Test batch checking existence."""
        queries = ["What is Python?", "What is Java?"]
        mock_repository.batch_exists.return_value = {
            "key1": True,
            "key2": False,
        }

        result = await redis_cache.batch_exists(queries)

        assert len(result) == 2
        mock_repository.batch_exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_empty_batch_operations(self, redis_cache):
        """Test batch operations with empty lists."""
        assert await redis_cache.batch_set([]) == 0
        assert await redis_cache.batch_get([]) == {}
        assert await redis_cache.batch_delete([]) == 0
        assert await redis_cache.batch_exists([]) == {}

    @pytest.mark.asyncio
    async def test_should_warm_cache(self, redis_cache, mock_repository, sample_entry):
        """Test cache warming with entries."""
        entries = [sample_entry]
        mock_repository.batch_store.return_value = 1

        result = await redis_cache.warm_cache(entries)

        assert result["total"] == 1
        assert result["success"] == 1
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_should_handle_empty_warming(self, redis_cache):
        """Test cache warming with no entries."""
        result = await redis_cache.warm_cache([])

        assert result["total"] == 0
        assert result["success"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_should_warm_cache_with_progress_callback(
        self, redis_cache, mock_repository, sample_entry
    ):
        """Test cache warming with progress callback."""
        entries = [sample_entry] * 5
        mock_repository.batch_store.return_value = 5
        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        result = await redis_cache.warm_cache(
            entries, progress_callback=progress_callback
        )

        assert result["total"] == 5
        assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_should_warm_from_queries(self, redis_cache, mock_repository):
        """Test cache warming from query list."""
        queries = ["What is Python?", "What is Java?"]
        mock_repository.exists.return_value = False
        mock_repository.batch_store.return_value = 2

        result = await redis_cache.warm_from_queries(queries, llm_provider=None)

        assert result["total"] == 2
        assert result["success"] == 2

    @pytest.mark.asyncio
    async def test_should_skip_already_cached_queries(
        self, redis_cache, mock_repository
    ):
        """Test cache warming skips already cached queries."""
        queries = ["What is Python?"]
        mock_repository.exists.return_value = True

        result = await redis_cache.warm_from_queries(queries, llm_provider=None)

        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_should_get_memory_stats(self, redis_cache, mock_repository):
        """Test getting memory statistics."""
        mock_stats = {
            "used_memory": 1024000,
            "used_memory_peak": 2048000,
            "maxmemory": 4096000,
        }
        mock_repository.get_memory_stats.return_value = mock_stats

        result = await redis_cache.get_memory_stats()

        assert result == mock_stats
        mock_repository.get_memory_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_check_memory_pressure(self, redis_cache, mock_repository):
        """Test checking memory pressure."""
        mock_repository.check_memory_pressure.return_value = True

        result = await redis_cache.is_memory_pressure_high()

        assert result is True
        mock_repository.check_memory_pressure.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_evict_old_entries(self, redis_cache, mock_repository):
        """Test evicting old cache entries."""
        mock_repository.evict_lru_keys.return_value = 50

        result = await redis_cache.evict_old_entries(count=50)

        assert result == 50
        mock_repository.evict_lru_keys.assert_called_once_with(50)

    @pytest.mark.asyncio
    async def test_should_set_max_memory(self, redis_cache, mock_repository):
        """Test setting maximum memory limit."""
        mock_repository.set_memory_limit.return_value = True

        result = await redis_cache.set_max_memory(max_memory_mb=100)

        assert result is True
        mock_repository.set_memory_limit.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_get_memory_breakdown(self, redis_cache, mock_repository):
        """Test getting memory breakdown by type."""
        mock_breakdown = {"overhead": 1000, "dataset": 5000, "keys": 100}
        mock_repository.get_memory_usage_by_type.return_value = mock_breakdown

        result = await redis_cache.get_memory_breakdown()

        assert result == mock_breakdown
        mock_repository.get_memory_usage_by_type.assert_called_once()
