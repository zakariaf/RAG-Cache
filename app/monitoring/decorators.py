"""
Metrics decorators for easy instrumentation.

Sandi Metz Principles:
- Single Responsibility: One decorator per metric type
- Non-intrusive: Minimal impact on decorated code
- Composable: Decorators can be combined
"""

import functools
import time
from typing import Any, Callable, Optional, TypeVar

from app.monitoring.prometheus import get_metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def track_request(
    method: str = "POST",
    path: str = "/api/v1/query"
) -> Callable[[F], F]:
    """
    Decorator to track HTTP request metrics.

    Args:
        method: HTTP method
        path: Request path

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()
            status_code = 200

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                metrics.track_request(method, path, status_code, duration)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()
            status_code = 200

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                metrics.track_request(method, path, status_code, duration)

        if asyncio_iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def track_cache_operation(
    operation: str = "query",
    cache_type: str = "exact"
) -> Callable[[F], F]:
    """
    Decorator to track cache operation metrics.

    Args:
        operation: Type of operation (query, store, delete)
        cache_type: Cache type (exact, semantic)

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                duration = time.time() - start_time

                # Determine if hit or miss based on result
                if result is not None:
                    metrics.track_cache_hit(cache_type)
                else:
                    metrics.track_cache_miss()

                return result
            except Exception as e:
                metrics.inc_counter(
                    "ragcache_cache_errors_total",
                    labels={"operation": operation, "type": cache_type}
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time

                if result is not None:
                    metrics.track_cache_hit(cache_type)
                else:
                    metrics.track_cache_miss()

                return result
            except Exception as e:
                metrics.inc_counter(
                    "ragcache_cache_errors_total",
                    labels={"operation": operation, "type": cache_type}
                )
                raise

        if asyncio_iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def track_llm_call(
    provider: str = "openai",
    model: str = "gpt-3.5-turbo"
) -> Callable[[F], F]:
    """
    Decorator to track LLM API call metrics.

    Args:
        provider: LLM provider name
        model: Model name

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()
            success = True

            try:
                result = await func(*args, **kwargs)

                # Extract token info from result if available
                tokens = 0
                cost = 0.0
                if hasattr(result, "total_tokens"):
                    tokens = result.total_tokens
                if hasattr(result, "cost"):
                    cost = result.cost

                duration = time.time() - start_time
                metrics.track_llm_call(
                    provider=provider,
                    model=model,
                    tokens=tokens,
                    cost=cost,
                    latency_seconds=duration,
                    success=True,
                )

                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics.track_llm_call(
                    provider=provider,
                    model=model,
                    tokens=0,
                    cost=0.0,
                    latency_seconds=duration,
                    success=False,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                tokens = 0
                cost = 0.0
                if hasattr(result, "total_tokens"):
                    tokens = result.total_tokens
                if hasattr(result, "cost"):
                    cost = result.cost

                duration = time.time() - start_time
                metrics.track_llm_call(
                    provider=provider,
                    model=model,
                    tokens=tokens,
                    cost=cost,
                    latency_seconds=duration,
                    success=True,
                )

                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics.track_llm_call(
                    provider=provider,
                    model=model,
                    tokens=0,
                    cost=0.0,
                    latency_seconds=duration,
                    success=False,
                )
                raise

        if asyncio_iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def track_latency(
    metric_name: str,
    labels: Optional[dict] = None
) -> Callable[[F], F]:
    """
    Generic decorator to track operation latency.

    Args:
        metric_name: Name of the histogram metric
        labels: Optional labels for the metric

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metrics.observe_histogram(metric_name, duration, labels)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metrics.observe_histogram(metric_name, duration, labels)

        if asyncio_iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def asyncio_iscoroutinefunction(func: Callable) -> bool:
    """Check if function is async."""
    import asyncio
    return asyncio.iscoroutinefunction(func)


class MetricsContext:
    """
    Context manager for tracking operation metrics.

    Usage:
        with MetricsContext("operation_name") as ctx:
            # do operation
            ctx.set_labels({"key": "value"})
    """

    def __init__(
        self,
        operation_name: str,
        labels: Optional[dict] = None,
        track_errors: bool = True
    ):
        """
        Initialize context.

        Args:
            operation_name: Name of the operation
            labels: Optional labels
            track_errors: Whether to track errors
        """
        self._operation = operation_name
        self._labels = labels or {}
        self._track_errors = track_errors
        self._start_time: float = 0.0
        self._metrics = get_metrics()

    def set_labels(self, labels: dict) -> None:
        """Update labels."""
        self._labels.update(labels)

    def __enter__(self) -> "MetricsContext":
        """Enter context."""
        self._start_time = time.time()
        self._metrics.inc_gauge(
            f"ragcache_{self._operation}_in_progress",
            labels=self._labels
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context."""
        duration = time.time() - self._start_time

        self._metrics.dec_gauge(
            f"ragcache_{self._operation}_in_progress",
            labels=self._labels
        )

        self._metrics.observe_histogram(
            f"ragcache_{self._operation}_duration_seconds",
            duration,
            self._labels
        )

        self._metrics.inc_counter(
            f"ragcache_{self._operation}_total",
            labels=self._labels
        )

        if exc_type is not None and self._track_errors:
            self._metrics.inc_counter(
                f"ragcache_{self._operation}_errors_total",
                labels={**self._labels, "error_type": exc_type.__name__}
            )

    async def __aenter__(self) -> "MetricsContext":
        """Async enter context."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async exit context."""
        self.__exit__(exc_type, exc_val, exc_tb)

