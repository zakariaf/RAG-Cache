"""
Performance benchmarks for Qdrant operations.

Run with: pytest tests/benchmarks/ -v -m benchmark

These tests measure performance and are not part of regular CI.
"""

import pytest
import pytest_asyncio
from qdrant_client.models import Distance

from app.benchmarks.qdrant_benchmark import QdrantBenchmark
from app.cache.qdrant_client import create_qdrant_client
from app.models.qdrant_point import QdrantPoint
from app.repositories.qdrant_repository import QdrantRepository


@pytest_asyncio.fixture
async def qdrant_client():
    """Create Qdrant client for benchmarking."""
    client = await create_qdrant_client()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def qdrant_repository(qdrant_client):
    """Create Qdrant repository for benchmarking."""
    repository = QdrantRepository(qdrant_client)

    # Ensure collection exists
    await repository.create_collection(distance=Distance.COSINE)

    yield repository

    # Clean up
    try:
        await repository.delete_collection()
    except Exception:
        pass


@pytest_asyncio.fixture
async def benchmark(qdrant_repository):
    """Create benchmark instance."""
    return QdrantBenchmark(qdrant_repository)


@pytest.mark.benchmark
class TestQdrantPerformance:
    """Performance benchmark tests for Qdrant operations."""

    @pytest.mark.asyncio
    async def test_benchmark_single_insert(self, benchmark):
        """Benchmark single point insertion."""
        metrics = await benchmark.benchmark_insert(num_points=100, vector_dim=384)

        assert metrics.total_operations == 100
        assert metrics.success_count == 100
        assert metrics.error_count == 0
        assert metrics.operations_per_second > 0

        print(metrics)

    @pytest.mark.asyncio
    async def test_benchmark_batch_insert(self, benchmark):
        """Benchmark batch insertion."""
        metrics = await benchmark.benchmark_batch_insert(
            num_points=1000, batch_size=100, vector_dim=384
        )

        assert metrics.total_operations == 10  # 10 batches
        assert metrics.success_count == 10
        assert metrics.error_count == 0
        assert metrics.operations_per_second > 0

        print(metrics)

    @pytest.mark.asyncio
    async def test_benchmark_search(self, benchmark, qdrant_repository):
        """Benchmark similarity search."""
        # First, insert some test data
        points = [
            QdrantPoint(
                id=f"search_bench_{i}",
                vector=[0.1 * i] * 384,
                payload={"index": i},
            )
            for i in range(100)
        ]
        await qdrant_repository.store_points(points)

        metrics = await benchmark.benchmark_search(
            num_searches=50, vector_dim=384, limit=10
        )

        assert metrics.total_operations == 50
        assert metrics.success_count == 50
        assert metrics.error_count == 0
        assert metrics.operations_per_second > 0
        assert metrics.avg_latency_ms > 0

        print(metrics)

    @pytest.mark.asyncio
    async def test_benchmark_concurrent_operations(self, benchmark):
        """Benchmark concurrent insertions."""
        metrics = await benchmark.benchmark_concurrent_operations(
            num_operations=50, concurrency=10, vector_dim=384
        )

        assert metrics.total_operations == 50
        assert metrics.success_count == 50
        assert metrics.error_count == 0
        assert metrics.operations_per_second > 0

        print(metrics)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_benchmark_small_dataset(self, benchmark):
        """Run small dataset benchmark suite."""
        result = await benchmark.run_full_benchmark(
            small_dataset=True, medium_dataset=False, large_dataset=False
        )

        assert len(result.metrics) >= 4
        assert result.duration > 0
        assert all(m.error_count == 0 for m in result.metrics)

        print(result.summary())

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_benchmark_medium_dataset(self, benchmark):
        """Run medium dataset benchmark suite."""
        result = await benchmark.run_full_benchmark(
            small_dataset=False, medium_dataset=True, large_dataset=False
        )

        assert len(result.metrics) >= 3
        assert result.duration > 0
        assert all(m.error_count == 0 for m in result.metrics)

        print(result.summary())

    @pytest.mark.asyncio
    async def test_benchmark_insert_different_vector_dims(self, benchmark):
        """Benchmark insertions with different vector dimensions."""
        dims = [128, 384, 768, 1536]
        results = {}

        for dim in dims:
            metrics = await benchmark.benchmark_insert(num_points=50, vector_dim=dim)
            results[dim] = metrics
            assert metrics.success_count == 50

        # Print comparison
        print("\n\nVector Dimension Performance Comparison:")
        print(f"{'Dimension':<12} {'Ops/sec':<12} {'Avg Latency (ms)':<20}")
        print("-" * 44)
        for dim, metrics in results.items():
            print(
                f"{dim:<12} {metrics.operations_per_second:<12.2f} "
                f"{metrics.avg_latency_ms:<20.2f}"
            )

    @pytest.mark.asyncio
    async def test_benchmark_batch_sizes(self, benchmark):
        """Benchmark different batch sizes."""
        batch_sizes = [10, 50, 100, 500]
        results = {}

        for batch_size in batch_sizes:
            metrics = await benchmark.benchmark_batch_insert(
                num_points=1000, batch_size=batch_size, vector_dim=384
            )
            results[batch_size] = metrics

        # Print comparison
        print("\n\nBatch Size Performance Comparison:")
        print(
            f"{'Batch Size':<12} {'Batches':<12} {'Ops/sec':<12} {'Avg Latency (ms)':<20}"
        )
        print("-" * 56)
        for batch_size, metrics in results.items():
            print(
                f"{batch_size:<12} {metrics.total_operations:<12} "
                f"{metrics.operations_per_second:<12.2f} "
                f"{metrics.avg_latency_ms:<20.2f}"
            )

    @pytest.mark.asyncio
    async def test_benchmark_search_result_limits(self, benchmark, qdrant_repository):
        """Benchmark search with different result limits."""
        # Insert test data
        points = [
            QdrantPoint(
                id=f"limit_bench_{i}",
                vector=[0.1 * i] * 384,
                payload={"index": i},
            )
            for i in range(200)
        ]
        await qdrant_repository.store_points(points)

        limits = [1, 5, 10, 50, 100]
        results = {}

        for limit in limits:
            metrics = await benchmark.benchmark_search(
                num_searches=30, vector_dim=384, limit=limit
            )
            results[limit] = metrics

        # Print comparison
        print("\n\nSearch Result Limit Performance Comparison:")
        print(f"{'Limit':<12} {'Ops/sec':<12} {'Avg Latency (ms)':<20}")
        print("-" * 44)
        for limit, metrics in results.items():
            print(
                f"{limit:<12} {metrics.operations_per_second:<12.2f} "
                f"{metrics.avg_latency_ms:<20.2f}"
            )

    @pytest.mark.asyncio
    async def test_benchmark_concurrent_levels(self, benchmark):
        """Benchmark different concurrency levels."""
        concurrency_levels = [1, 5, 10, 20, 50]
        results = {}

        for concurrency in concurrency_levels:
            metrics = await benchmark.benchmark_concurrent_operations(
                num_operations=100, concurrency=concurrency, vector_dim=384
            )
            results[concurrency] = metrics

        # Print comparison
        print("\n\nConcurrency Level Performance Comparison:")
        print(f"{'Concurrency':<14} {'Ops/sec':<12} {'Avg Latency (ms)':<20}")
        print("-" * 46)
        for concurrency, metrics in results.items():
            print(
                f"{concurrency:<14} {metrics.operations_per_second:<12.2f} "
                f"{metrics.avg_latency_ms:<20.2f}"
            )

    @pytest.mark.asyncio
    async def test_benchmark_latency_percentiles(self, benchmark, qdrant_repository):
        """Test latency percentiles for search operations."""
        # Insert test data
        points = [
            QdrantPoint(
                id=f"percentile_bench_{i}",
                vector=[0.1 * i] * 384,
                payload={"index": i},
            )
            for i in range(100)
        ]
        await qdrant_repository.store_points(points)

        metrics = await benchmark.benchmark_search(
            num_searches=100, vector_dim=384, limit=10
        )

        # Verify percentile ordering
        assert metrics.min_latency_ms <= metrics.p50_latency_ms
        assert metrics.p50_latency_ms <= metrics.p95_latency_ms
        assert metrics.p95_latency_ms <= metrics.p99_latency_ms
        assert metrics.p99_latency_ms <= metrics.max_latency_ms

        print("\n\nLatency Percentile Distribution:")
        print(f"  Min: {metrics.min_latency_ms:.2f}ms")
        print(f"  P50: {metrics.p50_latency_ms:.2f}ms")
        print(f"  P95: {metrics.p95_latency_ms:.2f}ms")
        print(f"  P99: {metrics.p99_latency_ms:.2f}ms")
        print(f"  Max: {metrics.max_latency_ms:.2f}ms")


@pytest.mark.benchmark
@pytest.mark.slow
class TestQdrantScalability:
    """Scalability tests for large datasets."""

    @pytest.mark.asyncio
    async def test_scalability_insert(self, benchmark):
        """Test insert scalability across different dataset sizes."""
        sizes = [100, 500, 1000]
        results = {}

        for size in sizes:
            metrics = await benchmark.benchmark_insert(num_points=size, vector_dim=384)
            results[size] = metrics

        print("\n\nInsert Scalability Test:")
        print(f"{'Dataset Size':<14} {'Ops/sec':<12} {'Total Time (s)':<16}")
        print("-" * 42)
        for size, metrics in results.items():
            print(
                f"{size:<14} {metrics.operations_per_second:<12.2f} "
                f"{metrics.total_time:<16.2f}"
            )

    @pytest.mark.asyncio
    async def test_scalability_batch_insert(self, benchmark):
        """Test batch insert scalability."""
        sizes = [1000, 5000, 10000]
        batch_size = 100
        results = {}

        for size in sizes:
            metrics = await benchmark.benchmark_batch_insert(
                num_points=size, batch_size=batch_size, vector_dim=384
            )
            results[size] = metrics

        print("\n\nBatch Insert Scalability Test:")
        print(f"{'Dataset Size':<14} {'Ops/sec':<12} {'Total Time (s)':<16}")
        print("-" * 42)
        for size, metrics in results.items():
            print(
                f"{size:<14} {metrics.operations_per_second:<12.2f} "
                f"{metrics.total_time:<16.2f}"
            )

    @pytest.mark.asyncio
    async def test_search_performance_with_dataset_growth(
        self, benchmark, qdrant_repository
    ):
        """Test search performance as dataset grows."""
        results = {}
        dataset_sizes = [100, 500, 1000]

        for size in dataset_sizes:
            # Insert data
            points = [
                QdrantPoint(
                    id=f"growth_bench_{size}_{i}",
                    vector=[0.1 * i] * 384,
                    payload={"size": size, "index": i},
                )
                for i in range(size)
            ]
            await qdrant_repository.store_points(points)

            # Benchmark search
            metrics = await benchmark.benchmark_search(
                num_searches=30, vector_dim=384, limit=10
            )
            results[size] = metrics

        print("\n\nSearch Performance vs Dataset Size:")
        print(f"{'Dataset Size':<14} {'Ops/sec':<12} {'Avg Latency (ms)':<20}")
        print("-" * 46)
        for size, metrics in results.items():
            print(
                f"{size:<14} {metrics.operations_per_second:<12.2f} "
                f"{metrics.avg_latency_ms:<20.2f}"
            )
