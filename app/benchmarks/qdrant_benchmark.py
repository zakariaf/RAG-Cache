"""
Qdrant performance benchmarking utilities.

Sandi Metz Principles:
- Single Responsibility: Performance measurement
- Small methods: Each benchmark isolated
- Clear naming: Descriptive method names
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.models.qdrant_point import QdrantPoint
from app.repositories.qdrant_repository import QdrantRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkMetrics:
    """Metrics collected during benchmark."""

    operation: str
    total_operations: int
    total_time: float
    operations_per_second: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    success_count: int
    error_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Format metrics as readable string."""
        return (
            f"\n{self.operation} Benchmark Results:\n"
            f"  Total Operations: {self.total_operations}\n"
            f"  Total Time: {self.total_time:.2f}s\n"
            f"  Throughput: {self.operations_per_second:.2f} ops/sec\n"
            f"  Avg Latency: {self.avg_latency_ms:.2f}ms\n"
            f"  Min Latency: {self.min_latency_ms:.2f}ms\n"
            f"  Max Latency: {self.max_latency_ms:.2f}ms\n"
            f"  P50 Latency: {self.p50_latency_ms:.2f}ms\n"
            f"  P95 Latency: {self.p95_latency_ms:.2f}ms\n"
            f"  P99 Latency: {self.p99_latency_ms:.2f}ms\n"
            f"  Success: {self.success_count} | Errors: {self.error_count}"
        )


@dataclass
class BenchmarkResult:
    """Complete benchmark results."""

    benchmark_name: str
    metrics: List[BenchmarkMetrics]
    duration: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Generate summary report."""
        lines = [
            f"\n{'=' * 60}",
            f"Benchmark: {self.benchmark_name}",
            f"Duration: {self.duration:.2f}s",
            f"Timestamp: {self.timestamp}",
            f"{'=' * 60}",
        ]

        for metric in self.metrics:
            lines.append(str(metric))
            lines.append("-" * 60)

        return "\n".join(lines)


class QdrantBenchmark:
    """
    Performance benchmarking for Qdrant operations.

    Measures throughput, latency, and resource usage.
    """

    def __init__(self, repository: QdrantRepository):
        """
        Initialize benchmark.

        Args:
            repository: Qdrant repository instance
        """
        self._repository = repository
        self._logger = logger

    async def benchmark_operation(
        self,
        operation_name: str,
        operation_func: Callable,
        iterations: int = 100,
        **kwargs: Any,
    ) -> BenchmarkMetrics:
        """
        Benchmark a single operation.

        Args:
            operation_name: Name of operation
            operation_func: Async function to benchmark
            iterations: Number of iterations
            **kwargs: Additional operation arguments

        Returns:
            BenchmarkMetrics with results
        """
        latencies: List[float] = []
        success_count = 0
        error_count = 0

        self._logger.info(
            "Starting benchmark",
            operation=operation_name,
            iterations=iterations,
        )

        start_time = time.time()

        for i in range(iterations):
            op_start = time.time()
            try:
                await operation_func(**kwargs)
                success_count += 1
            except Exception as e:
                error_count += 1
                self._logger.warning(
                    "Operation failed",
                    operation=operation_name,
                    iteration=i,
                    error=str(e),
                )

            op_end = time.time()
            latencies.append((op_end - op_start) * 1000)  # Convert to ms

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p50_idx = int(len(sorted_latencies) * 0.50)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        metrics = BenchmarkMetrics(
            operation=operation_name,
            total_operations=iterations,
            total_time=total_time,
            operations_per_second=iterations / total_time if total_time > 0 else 0,
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p50_latency_ms=sorted_latencies[p50_idx] if sorted_latencies else 0,
            p95_latency_ms=sorted_latencies[p95_idx] if sorted_latencies else 0,
            p99_latency_ms=sorted_latencies[p99_idx] if sorted_latencies else 0,
            success_count=success_count,
            error_count=error_count,
        )

        self._logger.info("Benchmark completed", operation=operation_name)
        return metrics

    async def benchmark_insert(
        self, num_points: int = 1000, vector_dim: int = 384
    ) -> BenchmarkMetrics:
        """
        Benchmark point insertion.

        Args:
            num_points: Number of points to insert
            vector_dim: Vector dimensions

        Returns:
            BenchmarkMetrics for insertions
        """

        async def insert_point(point_id: str, vector: List[float]) -> None:
            point = QdrantPoint(
                id=point_id,
                vector=vector,
                payload={"benchmark": True, "index": point_id},
            )
            await self._repository.store_point(point)

        # Generate test data
        test_vectors = [[0.1 * (i % 100)] * vector_dim for i in range(num_points)]

        latencies: List[float] = []
        start_time = time.time()

        for i, vector in enumerate(test_vectors):
            op_start = time.time()
            await insert_point(f"bench_insert_{i}", vector)
            op_end = time.time()
            latencies.append((op_end - op_start) * 1000)

        end_time = time.time()
        total_time = end_time - start_time

        sorted_latencies = sorted(latencies)
        p50_idx = int(len(sorted_latencies) * 0.50)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        return BenchmarkMetrics(
            operation="insert",
            total_operations=num_points,
            total_time=total_time,
            operations_per_second=num_points / total_time,
            avg_latency_ms=sum(latencies) / len(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            p50_latency_ms=sorted_latencies[p50_idx],
            p95_latency_ms=sorted_latencies[p95_idx],
            p99_latency_ms=sorted_latencies[p99_idx],
            success_count=num_points,
            error_count=0,
            metadata={"vector_dim": vector_dim},
        )

    async def benchmark_batch_insert(
        self,
        num_points: int = 1000,
        batch_size: int = 100,
        vector_dim: int = 384,
    ) -> BenchmarkMetrics:
        """
        Benchmark batch insertion.

        Args:
            num_points: Total points to insert
            batch_size: Points per batch
            vector_dim: Vector dimensions

        Returns:
            BenchmarkMetrics for batch insertions
        """
        num_batches = (num_points + batch_size - 1) // batch_size
        latencies: List[float] = []
        start_time = time.time()

        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, num_points)
            batch_points = [
                QdrantPoint(
                    id=f"bench_batch_{i}",
                    vector=[0.1 * (i % 100)] * vector_dim,
                    payload={"benchmark": True, "batch": batch_idx},
                )
                for i in range(start_idx, end_idx)
            ]

            op_start = time.time()
            await self._repository.store_points(batch_points)
            op_end = time.time()
            latencies.append((op_end - op_start) * 1000)

        end_time = time.time()
        total_time = end_time - start_time

        sorted_latencies = sorted(latencies)
        p50_idx = int(len(sorted_latencies) * 0.50)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        return BenchmarkMetrics(
            operation="batch_insert",
            total_operations=num_batches,
            total_time=total_time,
            operations_per_second=num_batches / total_time,
            avg_latency_ms=sum(latencies) / len(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            p50_latency_ms=sorted_latencies[p50_idx],
            p95_latency_ms=sorted_latencies[p95_idx],
            p99_latency_ms=sorted_latencies[p99_idx],
            success_count=num_batches,
            error_count=0,
            metadata={
                "total_points": num_points,
                "batch_size": batch_size,
                "vector_dim": vector_dim,
            },
        )

    async def benchmark_search(
        self,
        num_searches: int = 100,
        vector_dim: int = 384,
        limit: int = 10,
    ) -> BenchmarkMetrics:
        """
        Benchmark similarity search.

        Args:
            num_searches: Number of searches to perform
            vector_dim: Vector dimensions
            limit: Results per search

        Returns:
            BenchmarkMetrics for searches
        """
        query_vector = [0.1] * vector_dim
        latencies: List[float] = []
        start_time = time.time()

        for _ in range(num_searches):
            op_start = time.time()
            await self._repository.search_similar(query_vector, limit=limit)
            op_end = time.time()
            latencies.append((op_end - op_start) * 1000)

        end_time = time.time()
        total_time = end_time - start_time

        sorted_latencies = sorted(latencies)
        p50_idx = int(len(sorted_latencies) * 0.50)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        return BenchmarkMetrics(
            operation="search",
            total_operations=num_searches,
            total_time=total_time,
            operations_per_second=num_searches / total_time,
            avg_latency_ms=sum(latencies) / len(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            p50_latency_ms=sorted_latencies[p50_idx],
            p95_latency_ms=sorted_latencies[p95_idx],
            p99_latency_ms=sorted_latencies[p99_idx],
            success_count=num_searches,
            error_count=0,
            metadata={"vector_dim": vector_dim, "result_limit": limit},
        )

    async def benchmark_concurrent_operations(
        self,
        num_operations: int = 100,
        concurrency: int = 10,
        vector_dim: int = 384,
    ) -> BenchmarkMetrics:
        """
        Benchmark concurrent operations.

        Args:
            num_operations: Total operations
            concurrency: Concurrent tasks
            vector_dim: Vector dimensions

        Returns:
            BenchmarkMetrics for concurrent ops
        """

        async def concurrent_insert(idx: int) -> None:
            point = QdrantPoint(
                id=f"bench_concurrent_{idx}",
                vector=[0.1 * idx] * vector_dim,
                payload={"benchmark": True, "index": idx},
            )
            await self._repository.store_point(point)

        start_time = time.time()
        tasks = [concurrent_insert(i) for i in range(num_operations)]

        # Execute in batches of 'concurrency'
        for i in range(0, len(tasks), concurrency):
            batch = tasks[i : i + concurrency]
            await asyncio.gather(*batch, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        return BenchmarkMetrics(
            operation="concurrent_insert",
            total_operations=num_operations,
            total_time=total_time,
            operations_per_second=num_operations / total_time,
            avg_latency_ms=(total_time / num_operations) * 1000,
            min_latency_ms=0,
            max_latency_ms=0,
            p50_latency_ms=0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            success_count=num_operations,
            error_count=0,
            metadata={"concurrency": concurrency, "vector_dim": vector_dim},
        )

    async def run_full_benchmark(
        self,
        small_dataset: bool = True,
        medium_dataset: bool = False,
        large_dataset: bool = False,
    ) -> BenchmarkResult:
        """
        Run comprehensive benchmark suite.

        Args:
            small_dataset: Run small dataset tests (1K points)
            medium_dataset: Run medium dataset tests (10K points)
            large_dataset: Run large dataset tests (100K points)

        Returns:
            BenchmarkResult with all metrics
        """
        start_time = time.time()
        all_metrics: List[BenchmarkMetrics] = []

        self._logger.info("Starting full benchmark suite")

        if small_dataset:
            self._logger.info("Running small dataset benchmarks (1K points)")
            all_metrics.append(await self.benchmark_insert(1000, 384))
            all_metrics.append(await self.benchmark_batch_insert(1000, 100, 384))
            all_metrics.append(await self.benchmark_search(100, 384, 10))
            all_metrics.append(await self.benchmark_concurrent_operations(100, 10, 384))

        if medium_dataset:
            self._logger.info("Running medium dataset benchmarks (10K points)")
            all_metrics.append(await self.benchmark_insert(10000, 384))
            all_metrics.append(await self.benchmark_batch_insert(10000, 500, 384))
            all_metrics.append(await self.benchmark_search(200, 384, 10))

        if large_dataset:
            self._logger.info("Running large dataset benchmarks (100K points)")
            all_metrics.append(await self.benchmark_batch_insert(100000, 1000, 384))
            all_metrics.append(await self.benchmark_search(500, 384, 10))

        end_time = time.time()
        duration = end_time - start_time

        result = BenchmarkResult(
            benchmark_name="Qdrant Full Suite",
            metrics=all_metrics,
            duration=duration,
            timestamp=start_time,
            metadata={
                "small_dataset": small_dataset,
                "medium_dataset": medium_dataset,
                "large_dataset": large_dataset,
            },
        )

        self._logger.info(
            "Benchmark suite completed",
            duration=duration,
            num_metrics=len(all_metrics),
        )

        return result


# Convenience function
async def run_quick_benchmark(repository: QdrantRepository) -> BenchmarkResult:
    """
    Run quick performance benchmark.

    Args:
        repository: Qdrant repository

    Returns:
        BenchmarkResult
    """
    benchmark = QdrantBenchmark(repository)
    return await benchmark.run_full_benchmark(
        small_dataset=True,
        medium_dataset=False,
        large_dataset=False,
    )
