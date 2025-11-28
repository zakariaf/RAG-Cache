"""
Pipeline Performance Monitoring.

Tracks and reports performance metrics for the query pipeline.

Sandi Metz Principles:
- Single Responsibility: Performance tracking
- Observable: Expose metrics
- Non-intrusive: Decorator-based instrumentation
"""

import asyncio
import functools
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""

    name: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds."""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def complete(self, success: bool = True, error: Optional[str] = None):
        """Mark operation as complete."""
        self.end_time = time.time()
        self.success = success
        self.error = error


@dataclass
class PipelineMetrics:
    """Aggregated pipeline metrics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    semantic_hits: int = 0
    llm_calls: int = 0

    # Timing stats (in ms)
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0

    # Per-operation timings
    operation_timings: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list)
    )

    @property
    def avg_latency_ms(self) -> float:
        """Get average latency."""
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def cache_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    @property
    def semantic_hit_rate(self) -> float:
        """Get semantic cache hit rate."""
        if self.cache_misses == 0:
            return 0.0
        return self.semantic_hits / (self.cache_misses + self.semantic_hits)

    @property
    def success_rate(self) -> float:
        """Get success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def record_latency(self, latency_ms: float):
        """Record a request latency."""
        self.total_latency_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)

    def record_operation(self, name: str, duration_ms: float):
        """Record operation timing."""
        self.operation_timings[name].append(duration_ms)

    def get_operation_avg(self, name: str) -> float:
        """Get average duration for operation."""
        timings = self.operation_timings.get(name, [])
        if not timings:
            return 0.0
        return sum(timings) / len(timings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.success_rate, 4),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "semantic_hits": self.semantic_hits,
            "semantic_hit_rate": round(self.semantic_hit_rate, 4),
            "llm_calls": self.llm_calls,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2)
            if self.min_latency_ms != float("inf")
            else 0,
            "max_latency_ms": round(self.max_latency_ms, 2),
            "operation_avgs": {
                name: round(self.get_operation_avg(name), 2)
                for name in self.operation_timings
            },
        }


class PerformanceMonitor:
    """
    Monitors pipeline performance.

    Collects and aggregates metrics.
    """

    def __init__(self):
        """Initialize monitor."""
        self._metrics = PipelineMetrics()
        self._current_operations: Dict[str, OperationMetrics] = {}
        self._lock = asyncio.Lock()

    @property
    def metrics(self) -> PipelineMetrics:
        """Get current metrics."""
        return self._metrics

    async def record_request_start(self) -> str:
        """
        Record start of a request.

        Returns:
            Request ID for tracking
        """
        import uuid

        request_id = str(uuid.uuid4())

        async with self._lock:
            self._metrics.total_requests += 1

        return request_id

    async def record_request_end(
        self,
        request_id: str,
        success: bool,
        latency_ms: float,
        cache_hit: bool = False,
        semantic_hit: bool = False,
        llm_called: bool = False,
    ):
        """
        Record end of a request.

        Args:
            request_id: Request identifier
            success: Whether request succeeded
            latency_ms: Total latency in ms
            cache_hit: Whether exact cache was hit
            semantic_hit: Whether semantic cache was hit
            llm_called: Whether LLM was called
        """
        async with self._lock:
            if success:
                self._metrics.successful_requests += 1
            else:
                self._metrics.failed_requests += 1

            if cache_hit:
                self._metrics.cache_hits += 1
            elif semantic_hit:
                self._metrics.semantic_hits += 1
                self._metrics.cache_misses += 1
            else:
                self._metrics.cache_misses += 1

            if llm_called:
                self._metrics.llm_calls += 1

            self._metrics.record_latency(latency_ms)

    async def start_operation(self, name: str) -> OperationMetrics:
        """
        Start tracking an operation.

        Args:
            name: Operation name

        Returns:
            OperationMetrics for tracking
        """
        op = OperationMetrics(name=name, start_time=time.time())
        self._current_operations[f"{name}_{id(op)}"] = op
        return op

    async def end_operation(
        self, op: OperationMetrics, success: bool = True, error: Optional[str] = None
    ):
        """
        End tracking an operation.

        Args:
            op: Operation metrics
            success: Whether succeeded
            error: Error message if failed
        """
        op.complete(success=success, error=error)

        async with self._lock:
            self._metrics.record_operation(op.name, op.duration_ms)

        # Log slow operations
        if op.duration_ms > 1000:  # > 1 second
            logger.warning(
                "Slow operation detected",
                operation=op.name,
                duration_ms=op.duration_ms,
            )

    def reset(self):
        """Reset all metrics."""
        self._metrics = PipelineMetrics()
        self._current_operations.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return self._metrics.to_dict()


# Global monitor instance
_monitor = PerformanceMonitor()


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor."""
    return _monitor


def track_operation(name: str):
    """
    Decorator to track operation performance.

    Args:
        name: Operation name

    Returns:
        Decorated function
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            monitor = get_monitor()
            op = await monitor.start_operation(name)
            try:
                result = await func(*args, **kwargs)
                await monitor.end_operation(op, success=True)
                return result
            except Exception as e:
                await monitor.end_operation(op, success=False, error=str(e))
                raise

        return wrapper

    return decorator
