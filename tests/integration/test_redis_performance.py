"""
Performance benchmarks for Redis cache.

These tests measure cache performance under various conditions.
"""

import asyncio
import time
from typing import List

import pytest
import pytest_asyncio

from app.cache.redis_cache import RedisCache
from app.models.cache_entry import CacheEntry
from app.repositories.redis_repository import RedisRepository, create_redis_pool


@pytest_asyncio.fixture
async def redis_pool():
    """Create Redis connection pool for benchmarking."""
    pool = await create_redis_pool()
    yield pool
    await pool.disconnect()


@pytest_asyncio.fixture
async def redis_repository(redis_pool):
    """Create Redis repository for benchmarking."""
    return RedisRepository(pool=redis_pool)


@pytest_asyncio.fixture
async def redis_cache(redis_repository):
    """Create Redis cache for benchmarking."""
    cache = RedisCache(repository=redis_repository)
    await cache.invalidate_all()
    yield cache
    await cache.invalidate_all()


def create_test_entries(count: int) -> List[CacheEntry]:
    """Create test cache entries."""
    return [
        CacheEntry(
            query_hash=f"bench_hash_{i}",
            original_query=f"Benchmark query {i}",
            response=f"Benchmark response {i}" * 10,  # Larger response
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=100,
            embedding=[0.1] * 1536 if i % 2 == 0 else None,  # Some with embeddings
        )
        for i in range(count)
    ]


@pytest.mark.integration
@pytest.mark.benchmark
@pytest.mark.asyncio
class TestRedisCachePerformance:
    """Performance benchmarks for Redis cache."""

    async def test_benchmark_single_write_performance(self, redis_cache: RedisCache):
        """Benchmark single write operations."""
        entries = create_test_entries(1000)

        start_time = time.time()
        success_count = 0

        for entry in entries:
            success = await redis_cache.set(entry)
            if success:
                success_count += 1

        elapsed = time.time() - start_time
        throughput = success_count / elapsed

        print(f"\n=== Single Write Performance ===")
        print(f"Operations: {success_count}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} ops/s")
        print(f"Avg Latency: {(elapsed / success_count) * 1000:.2f}ms")

        assert success_count == 1000
        assert throughput > 100  # At least 100 ops/s

    async def test_benchmark_single_read_performance(self, redis_cache: RedisCache):
        """Benchmark single read operations."""
        # Setup: populate cache
        entries = create_test_entries(1000)
        await redis_cache.batch_set(entries)

        queries = [entry.original_query for entry in entries]

        start_time = time.time()
        hit_count = 0

        for query in queries:
            result = await redis_cache.get(query)
            if result:
                hit_count += 1

        elapsed = time.time() - start_time
        throughput = hit_count / elapsed

        print(f"\n=== Single Read Performance ===")
        print(f"Operations: {hit_count}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} ops/s")
        print(f"Avg Latency: {(elapsed / hit_count) * 1000:.2f}ms")
        print(f"Hit Rate: {(hit_count / len(queries)) * 100:.2f}%")

        assert hit_count == 1000
        assert throughput > 500  # Reads should be faster

    async def test_benchmark_batch_write_performance(self, redis_cache: RedisCache):
        """Benchmark batch write operations."""
        entries = create_test_entries(1000)
        batch_size = 100

        start_time = time.time()
        total_written = 0

        for i in range(0, len(entries), batch_size):
            batch = entries[i : i + batch_size]
            count = await redis_cache.batch_set(batch)
            total_written += count

        elapsed = time.time() - start_time
        throughput = total_written / elapsed

        print(f"\n=== Batch Write Performance ===")
        print(f"Operations: {total_written}")
        print(f"Batch Size: {batch_size}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} ops/s")
        print(
            f"Avg Latency: {(elapsed / (total_written / batch_size)) * 1000:.2f}ms per batch"
        )

        assert total_written == 1000
        assert throughput > 500  # Batch should be faster

    async def test_benchmark_batch_read_performance(self, redis_cache: RedisCache):
        """Benchmark batch read operations."""
        # Setup: populate cache
        entries = create_test_entries(1000)
        await redis_cache.batch_set(entries)

        queries = [entry.original_query for entry in entries]
        batch_size = 100

        start_time = time.time()
        total_read = 0

        for i in range(0, len(queries), batch_size):
            batch = queries[i : i + batch_size]
            results = await redis_cache.batch_get(batch)
            total_read += sum(1 for v in results.values() if v is not None)

        elapsed = time.time() - start_time
        throughput = total_read / elapsed

        print(f"\n=== Batch Read Performance ===")
        print(f"Operations: {total_read}")
        print(f"Batch Size: {batch_size}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} ops/s")
        print(
            f"Avg Latency: {(elapsed / (total_read / batch_size)) * 1000:.2f}ms per batch"
        )

        assert total_read == 1000
        assert throughput > 1000  # Batch reads should be very fast

    async def test_benchmark_concurrent_writes(self, redis_cache: RedisCache):
        """Benchmark concurrent write operations."""
        entries = create_test_entries(500)

        start_time = time.time()

        # Concurrent writes
        tasks = [redis_cache.set(entry) for entry in entries]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r)
        throughput = success_count / elapsed

        print(f"\n=== Concurrent Write Performance ===")
        print(f"Operations: {success_count}")
        print(f"Concurrency: {len(tasks)}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} ops/s")

        assert success_count == 500
        assert throughput > 200

    async def test_benchmark_concurrent_reads(self, redis_cache: RedisCache):
        """Benchmark concurrent read operations."""
        # Setup: populate cache
        entries = create_test_entries(500)
        await redis_cache.batch_set(entries)

        queries = [entry.original_query for entry in entries]

        start_time = time.time()

        # Concurrent reads
        tasks = [redis_cache.get(query) for query in queries]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        hit_count = sum(1 for r in results if r is not None)
        throughput = hit_count / elapsed

        print(f"\n=== Concurrent Read Performance ===")
        print(f"Operations: {hit_count}")
        print(f"Concurrency: {len(tasks)}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} ops/s")

        assert hit_count == 500
        assert throughput > 500

    async def test_benchmark_cache_warming(self, redis_cache: RedisCache):
        """Benchmark cache warming performance."""
        entries = create_test_entries(1000)

        start_time = time.time()

        result = await redis_cache.warm_cache(entries, batch_size=100)

        elapsed = time.time() - start_time
        throughput = result["success"] / elapsed

        print(f"\n=== Cache Warming Performance ===")
        print(f"Operations: {result['success']}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} ops/s")
        print(f"Failed: {result['failed']}")

        assert result["success"] == 1000
        assert throughput > 300

    async def test_benchmark_mixed_workload(self, redis_cache: RedisCache):
        """Benchmark mixed read/write workload."""
        # Setup: populate with some data
        initial_entries = create_test_entries(500)
        await redis_cache.batch_set(initial_entries)

        new_entries = create_test_entries(500)
        queries = [entry.original_query for entry in initial_entries]

        start_time = time.time()

        # Mixed operations
        write_tasks = [redis_cache.set(entry) for entry in new_entries[:250]]
        read_tasks = [redis_cache.get(query) for query in queries[:250]]

        results = await asyncio.gather(*write_tasks, *read_tasks)

        elapsed = time.time() - start_time
        throughput = len(results) / elapsed

        print(f"\n=== Mixed Workload Performance ===")
        print(f"Operations: {len(results)} (250 writes + 250 reads)")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} ops/s")

        assert len(results) == 500
        assert throughput > 200

    async def test_benchmark_memory_stats_collection(self, redis_cache: RedisCache):
        """Benchmark metrics collection performance."""
        iterations = 100

        start_time = time.time()

        for _ in range(iterations):
            await redis_cache.get_memory_stats()

        elapsed = time.time() - start_time
        throughput = iterations / elapsed

        print(f"\n=== Memory Stats Collection Performance ===")
        print(f"Operations: {iterations}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} ops/s")
        print(f"Avg Latency: {(elapsed / iterations) * 1000:.2f}ms")

        assert throughput > 50  # Should be reasonably fast

    async def test_benchmark_invalidation_performance(self, redis_cache: RedisCache):
        """Benchmark cache invalidation performance."""
        # Setup: populate cache
        entries = create_test_entries(1000)
        await redis_cache.batch_set(entries)

        start_time = time.time()

        count = await redis_cache.invalidate_by_pattern("*")

        elapsed = time.time() - start_time
        throughput = count / elapsed if count > 0 else 0

        print(f"\n=== Invalidation Performance ===")
        print(f"Keys Deleted: {count}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} ops/s")

        assert count >= 1000
        assert elapsed < 5.0  # Should complete in reasonable time
