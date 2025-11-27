"""
Async operation optimization.

Sandi Metz Principles:
- Single Responsibility: Async optimization
- Small methods: Each optimization isolated
- Configurable: Flexible concurrency settings
"""

import asyncio
import functools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class ConcurrencyConfig:
    """Concurrency configuration."""

    # Limits
    max_concurrent_tasks: int = 100
    max_concurrent_per_operation: int = 10

    # Timeouts
    default_timeout_seconds: float = 30.0

    # Batching
    enable_auto_batching: bool = True
    batch_size: int = 10
    batch_delay_ms: int = 10


class ConcurrencyLimiter:
    """
    Limits concurrent operations to prevent resource exhaustion.

    Uses semaphores for efficient concurrency control.
    """

    def __init__(self, max_concurrent: int = 100):
        """
        Initialize limiter.

        Args:
            max_concurrent: Maximum concurrent operations
        """
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._peak_count = 0
        self._total_operations = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a slot for operation."""
        await self._semaphore.acquire()
        async with self._lock:
            self._active_count += 1
            self._total_operations += 1
            if self._active_count > self._peak_count:
                self._peak_count = self._active_count

    def release(self) -> None:
        """Release a slot."""
        self._semaphore.release()
        self._active_count = max(0, self._active_count - 1)

    @property
    def active_count(self) -> int:
        """Get current active operation count."""
        return self._active_count

    @property
    def available_slots(self) -> int:
        """Get available slots."""
        return self._semaphore._value

    def get_stats(self) -> Dict[str, int]:
        """Get limiter statistics."""
        return {
            "active_count": self._active_count,
            "peak_count": self._peak_count,
            "total_operations": self._total_operations,
            "available_slots": self.available_slots,
        }


class AsyncOptimizer:
    """
    Optimizes async operations for better performance.

    Provides utilities for batching, timeouts, and concurrency.
    """

    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        """
        Initialize optimizer.

        Args:
            config: Concurrency configuration
        """
        self._config = config or ConcurrencyConfig()
        self._global_limiter = ConcurrencyLimiter(
            self._config.max_concurrent_tasks
        )
        self._operation_limiters: Dict[str, ConcurrencyLimiter] = {}
        self._stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "timeout_operations": 0,
            "batched_operations": 0,
        }

    def get_limiter(self, operation: str) -> ConcurrencyLimiter:
        """
        Get or create a limiter for a specific operation.

        Args:
            operation: Operation name

        Returns:
            Concurrency limiter for the operation
        """
        if operation not in self._operation_limiters:
            self._operation_limiters[operation] = ConcurrencyLimiter(
                self._config.max_concurrent_per_operation
            )
        return self._operation_limiters[operation]

    async def execute_with_limit(
        self,
        coro: Callable[[], T],
        operation: str = "default",
        timeout: Optional[float] = None
    ) -> T:
        """
        Execute coroutine with concurrency limiting.

        Args:
            coro: Coroutine to execute
            operation: Operation name for per-operation limiting
            timeout: Optional timeout override

        Returns:
            Result of coroutine
        """
        timeout = timeout or self._config.default_timeout_seconds
        limiter = self.get_limiter(operation)

        self._stats["total_operations"] += 1

        try:
            await self._global_limiter.acquire()
            await limiter.acquire()

            try:
                result = await asyncio.wait_for(coro(), timeout=timeout)
                self._stats["successful_operations"] += 1
                return result
            except asyncio.TimeoutError:
                self._stats["timeout_operations"] += 1
                self._stats["failed_operations"] += 1
                raise
            except Exception:
                self._stats["failed_operations"] += 1
                raise
            finally:
                limiter.release()
                self._global_limiter.release()

        except Exception:
            self._global_limiter.release()
            raise

    async def gather_with_limit(
        self,
        coros: List[Callable[[], T]],
        operation: str = "default",
        timeout: Optional[float] = None,
        return_exceptions: bool = False
    ) -> List[T]:
        """
        Execute multiple coroutines with limiting.

        Args:
            coros: List of coroutines
            operation: Operation name
            timeout: Timeout for each operation
            return_exceptions: Return exceptions instead of raising

        Returns:
            List of results
        """
        tasks = [
            self.execute_with_limit(coro, operation, timeout)
            for coro in coros
        ]

        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    async def execute_batched(
        self,
        items: List[Any],
        process_fn: Callable[[List[Any]], T],
        batch_size: Optional[int] = None
    ) -> List[T]:
        """
        Process items in batches.

        Args:
            items: Items to process
            process_fn: Function to process a batch
            batch_size: Override batch size

        Returns:
            List of results
        """
        batch_size = batch_size or self._config.batch_size
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            result = await process_fn(batch)
            results.append(result)
            self._stats["batched_operations"] += 1

            # Small delay between batches
            if self._config.batch_delay_ms > 0:
                await asyncio.sleep(self._config.batch_delay_ms / 1000)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        return {
            **self._stats,
            "global_limiter": self._global_limiter.get_stats(),
            "operation_limiters": {
                name: limiter.get_stats()
                for name, limiter in self._operation_limiters.items()
            },
        }


def with_concurrency_limit(
    max_concurrent: int = 10,
    timeout: Optional[float] = None
):
    """
    Decorator to limit concurrent executions of a function.

    Args:
        max_concurrent: Maximum concurrent executions
        timeout: Optional timeout

    Returns:
        Decorated function
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async with semaphore:
                if timeout:
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout
                    )
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def with_timeout(timeout_seconds: float):
    """
    Decorator to add timeout to async function.

    Args:
        timeout_seconds: Timeout in seconds

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout_seconds
            )

        return wrapper

    return decorator


def with_retry(
    max_retries: int = 3,
    delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to add retry logic to async function.

    Args:
        max_retries: Maximum retry attempts
        delay_seconds: Initial delay between retries
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Exception types to retry on

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            delay = delay_seconds
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(delay)
                        delay *= backoff_multiplier

            raise last_exception

        return wrapper

    return decorator

