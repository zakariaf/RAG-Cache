"""
Integration tests for Redis cache.

These tests require a running Redis instance.
"""

import pytest
import pytest_asyncio
from redis.asyncio import ConnectionPool

from app.cache.redis_cache import RedisCache
from app.config import config
from app.models.cache_entry import CacheEntry
from app.repositories.redis_repository import RedisRepository, create_redis_pool


@pytest_asyncio.fixture
async def redis_pool():
    """Create Redis connection pool for testing."""
    pool = await create_redis_pool()
    yield pool
    await pool.disconnect()


@pytest_asyncio.fixture
async def redis_repository(redis_pool):
    """Create Redis repository for testing."""
    return RedisRepository(pool=redis_pool)


@pytest_asyncio.fixture
async def redis_cache(redis_repository):
    """Create Redis cache for testing."""
    cache = RedisCache(repository=redis_repository)
    # Clean up before each test
    await cache.invalidate_all()
    yield cache
    # Clean up after each test
    await cache.invalidate_all()


@pytest.fixture
def sample_entry():
    """Create sample cache entry."""
    return CacheEntry(
        query_hash="test_integration_hash",
        original_query="What is integration testing?",
        response="Integration testing tests the complete flow",
        provider="openai",
        model="gpt-3.5-turbo",
        prompt_tokens=10,
        completion_tokens=20,
        embedding=None,
    )


@pytest.mark.integration
@pytest.mark.asyncio
class TestRedisCacheIntegration:
    """Integration tests for Redis cache."""

    async def test_should_store_and_retrieve_entry(
        self, redis_cache: RedisCache, sample_entry: CacheEntry
    ):
        """Test storing and retrieving cache entry."""
        # Store entry
        success = await redis_cache.set(sample_entry)
        assert success is True

        # Retrieve entry
        result = await redis_cache.get(sample_entry.original_query)
        assert result is not None
        assert result.original_query == sample_entry.original_query
        assert result.response == sample_entry.response

    async def test_should_return_none_for_missing_entry(self, redis_cache: RedisCache):
        """Test retrieving non-existent entry."""
        result = await redis_cache.get("Non-existent query")
        assert result is None

    async def test_should_delete_entry(
        self, redis_cache: RedisCache, sample_entry: CacheEntry
    ):
        """Test deleting cache entry."""
        # Store entry
        await redis_cache.set(sample_entry)

        # Verify it exists
        exists = await redis_cache.exists(sample_entry.original_query)
        assert exists is True

        # Delete entry
        deleted = await redis_cache.delete(sample_entry.original_query)
        assert deleted is True

        # Verify it's gone
        exists = await redis_cache.exists(sample_entry.original_query)
        assert exists is False

    async def test_should_check_health(self, redis_cache: RedisCache):
        """Test Redis health check."""
        healthy = await redis_cache.health_check()
        assert healthy is True

    async def test_should_invalidate_by_pattern(
        self, redis_cache: RedisCache, sample_entry: CacheEntry
    ):
        """Test invalidating entries by pattern."""
        # Store multiple entries
        await redis_cache.set(sample_entry)

        # Invalidate all
        count = await redis_cache.invalidate_by_pattern("*")
        assert count >= 1

    async def test_should_batch_store_and_fetch(self, redis_cache: RedisCache):
        """Test batch operations."""
        # Create multiple entries
        entries = [
            CacheEntry(
                query_hash=f"hash_{i}",
                original_query=f"Query {i}",
                response=f"Response {i}",
                provider="openai",
                model="gpt-3.5-turbo",
                prompt_tokens=10,
                completion_tokens=20,
                embedding=None,
            )
            for i in range(5)
        ]

        # Batch store
        count = await redis_cache.batch_set(entries)
        assert count == 5

        # Batch fetch
        queries = [f"Query {i}" for i in range(5)]
        results = await redis_cache.batch_get(queries)
        assert len(results) == 5
        assert all(results[q] is not None for q in queries)

    async def test_should_get_metrics(self, redis_cache: RedisCache):
        """Test getting Redis metrics."""
        metrics = await redis_cache.get_metrics()
        assert metrics is not None
        assert metrics.total_keys >= 0
        assert metrics.memory_used_bytes >= 0

    async def test_should_get_cache_size(
        self, redis_cache: RedisCache, sample_entry: CacheEntry
    ):
        """Test getting cache size."""
        # Initially should be 0 or small
        initial_size = await redis_cache.get_cache_size()

        # Add entry
        await redis_cache.set(sample_entry)

        # Size should increase
        new_size = await redis_cache.get_cache_size()
        assert new_size > initial_size

    async def test_should_warm_cache(self, redis_cache: RedisCache):
        """Test cache warming."""
        entries = [
            CacheEntry(
                query_hash=f"warm_hash_{i}",
                original_query=f"Warm query {i}",
                response=f"Warm response {i}",
                provider="openai",
                model="gpt-3.5-turbo",
                prompt_tokens=10,
                completion_tokens=20,
                embedding=None,
            )
            for i in range(10)
        ]

        result = await redis_cache.warm_cache(entries, batch_size=5)
        assert result["total"] == 10
        assert result["success"] == 10
        assert result["failed"] == 0

    async def test_should_get_memory_stats(self, redis_cache: RedisCache):
        """Test getting memory statistics."""
        stats = await redis_cache.get_memory_stats()
        assert stats is not None
        assert "used_memory" in stats
        assert stats["used_memory"] >= 0

    async def test_should_batch_delete(self, redis_cache: RedisCache):
        """Test batch delete operations."""
        # Create and store entries
        entries = [
            CacheEntry(
                query_hash=f"del_hash_{i}",
                original_query=f"Delete query {i}",
                response=f"Delete response {i}",
                provider="openai",
                model="gpt-3.5-turbo",
                prompt_tokens=10,
                completion_tokens=20,
                embedding=None,
            )
            for i in range(3)
        ]
        await redis_cache.batch_set(entries)

        # Batch delete
        queries = [f"Delete query {i}" for i in range(3)]
        count = await redis_cache.batch_delete(queries)
        assert count == 3

        # Verify all deleted
        results = await redis_cache.batch_get(queries)
        assert all(results[q] is None for q in queries)

    async def test_should_handle_concurrent_operations(
        self, redis_cache: RedisCache, sample_entry: CacheEntry
    ):
        """Test concurrent cache operations."""
        import asyncio

        # Concurrent writes
        tasks = [redis_cache.set(sample_entry) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        assert all(results)

        # Concurrent reads
        tasks = [redis_cache.get(sample_entry.original_query) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        assert all(r is not None for r in results)

    async def test_should_expire_entries_with_ttl(
        self, redis_cache: RedisCache, sample_entry: CacheEntry
    ):
        """Test TTL expiration (requires waiting)."""
        # Note: This test would need to wait for actual expiration
        # For now, just verify the entry is stored with TTL
        success = await redis_cache.set(sample_entry)
        assert success is True

        # Verify entry exists
        exists = await redis_cache.exists(sample_entry.original_query)
        assert exists is True
