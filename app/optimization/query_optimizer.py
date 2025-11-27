"""
Query response time optimization.

Sandi Metz Principles:
- Single Responsibility: Query optimization
- Small methods: Each optimization isolated
- Configurable: Flexible optimization settings
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class OptimizationConfig:
    """
    Query optimization configuration.

    Configures optimization behavior and thresholds.
    """

    # Parallel processing
    enable_parallel_cache_check: bool = True
    parallel_timeout_seconds: float = 1.0

    # Early termination
    enable_early_termination: bool = True
    exact_match_threshold: float = 1.0

    # Query preprocessing
    enable_query_normalization: bool = True
    enable_query_deduplication: bool = True

    # Caching
    enable_result_caching: bool = True
    cache_warm_threshold: float = 0.9

    # Performance targets (milliseconds)
    target_cache_hit_latency_ms: int = 50
    target_total_latency_ms: int = 2000


@dataclass
class OptimizationResult:
    """
    Result of optimization analysis.

    Contains timing and optimization metrics.
    """

    original_latency_ms: float
    optimized_latency_ms: float
    improvement_percent: float
    optimizations_applied: List[str] = field(default_factory=list)
    cache_hit: bool = False
    cache_type: Optional[str] = None


class QueryOptimizer:
    """
    Optimizes query processing for minimal latency.

    Applies various optimization strategies.
    """

    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Initialize optimizer.

        Args:
            config: Optimization configuration
        """
        self._config = config or OptimizationConfig()
        self._timing_history: List[float] = []
        self._max_history = 1000

    async def optimize_cache_lookup(
        self,
        exact_lookup: Callable[[], T],
        semantic_lookup: Callable[[], T],
    ) -> tuple[Optional[T], str]:
        """
        Optimize cache lookup with parallel execution.

        Args:
            exact_lookup: Function for exact cache lookup
            semantic_lookup: Function for semantic cache lookup

        Returns:
            Tuple of (result, cache_type)
        """
        if not self._config.enable_parallel_cache_check:
            # Sequential lookup
            result = await exact_lookup()
            if result:
                return result, "exact"

            result = await semantic_lookup()
            if result:
                return result, "semantic"

            return None, "miss"

        # Parallel lookup with early termination
        try:
            async with asyncio.timeout(self._config.parallel_timeout_seconds):
                # Create tasks
                exact_task = asyncio.create_task(exact_lookup())
                semantic_task = asyncio.create_task(semantic_lookup())

                # Wait for first result
                done, pending = await asyncio.wait(
                    [exact_task, semantic_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Check exact match first (higher priority)
                if exact_task in done:
                    result = exact_task.result()
                    if result:
                        # Cancel semantic if still running
                        if semantic_task in pending:
                            semantic_task.cancel()
                        return result, "exact"

                # Check semantic match
                if semantic_task in done:
                    result = semantic_task.result()
                    if result:
                        return result, "semantic"

                # Wait for remaining task if no hits yet
                if pending:
                    remaining = await asyncio.gather(*pending, return_exceptions=True)
                    for r in remaining:
                        if r and not isinstance(r, Exception):
                            return r, "semantic"

                return None, "miss"

        except asyncio.TimeoutError:
            logger.warning("Cache lookup timeout")
            return None, "timeout"

    def should_skip_semantic_search(
        self,
        exact_result: Optional[Any],
        confidence: float = 1.0
    ) -> bool:
        """
        Determine if semantic search should be skipped.

        Args:
            exact_result: Result from exact match
            confidence: Confidence in exact match

        Returns:
            True if semantic search should be skipped
        """
        if not self._config.enable_early_termination:
            return False

        if exact_result and confidence >= self._config.exact_match_threshold:
            return True

        return False

    def record_timing(self, latency_ms: float) -> None:
        """
        Record query timing for analysis.

        Args:
            latency_ms: Query latency in milliseconds
        """
        self._timing_history.append(latency_ms)
        if len(self._timing_history) > self._max_history:
            self._timing_history.pop(0)

    def get_average_latency(self) -> float:
        """Get average query latency."""
        if not self._timing_history:
            return 0.0
        return sum(self._timing_history) / len(self._timing_history)

    def get_percentile_latency(self, percentile: float) -> float:
        """
        Get latency percentile.

        Args:
            percentile: Percentile (0-100)

        Returns:
            Latency at percentile
        """
        if not self._timing_history:
            return 0.0

        sorted_times = sorted(self._timing_history)
        idx = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    def is_meeting_targets(self) -> Dict[str, bool]:
        """
        Check if performance targets are being met.

        Returns:
            Dict of target status
        """
        avg_latency = self.get_average_latency()
        p95_latency = self.get_percentile_latency(95)

        return {
            "avg_under_target": avg_latency < self._config.target_total_latency_ms,
            "p95_under_target": p95_latency < self._config.target_total_latency_ms * 1.5,
        }

    def get_optimization_suggestions(self) -> List[str]:
        """
        Get suggestions for improving performance.

        Returns:
            List of optimization suggestions
        """
        suggestions = []
        avg_latency = self.get_average_latency()
        target = self._config.target_total_latency_ms

        if avg_latency > target:
            suggestions.append(
                f"Average latency ({avg_latency:.0f}ms) exceeds target ({target}ms)"
            )

            if not self._config.enable_parallel_cache_check:
                suggestions.append("Enable parallel cache checking")

            if not self._config.enable_early_termination:
                suggestions.append("Enable early termination on exact match")

        p95 = self.get_percentile_latency(95)
        if p95 > target * 2:
            suggestions.append(
                f"P95 latency ({p95:.0f}ms) is very high - check for outliers"
            )

        return suggestions


class QueryTimer:
    """
    Context manager for timing query operations.

    Usage:
        async with QueryTimer() as timer:
            result = await process_query()
        print(f"Took {timer.elapsed_ms}ms")
    """

    def __init__(self, optimizer: Optional[QueryOptimizer] = None):
        """
        Initialize timer.

        Args:
            optimizer: Optional optimizer to record timing
        """
        self._start_time: float = 0
        self._end_time: float = 0
        self._optimizer = optimizer

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return (self._end_time - self._start_time) * 1000

    async def __aenter__(self) -> "QueryTimer":
        """Start timing."""
        self._start_time = time.perf_counter()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop timing and record."""
        self._end_time = time.perf_counter()
        if self._optimizer:
            self._optimizer.record_timing(self.elapsed_ms)

