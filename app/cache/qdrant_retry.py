"""
Retry mechanism for Qdrant operations.

Sandi Metz Principles:
- Single Responsibility: Retry logic
- Small methods: Each retry strategy isolated
- Clear naming: Descriptive function names
"""

import asyncio
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from app.cache.qdrant_errors import is_retryable_error
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryConfig:
    """
    Configuration for retry behavior.

    Defines retry parameters and backoff strategy.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        import random

        # Exponential backoff
        delay = self.initial_delay * (self.exponential_base**attempt)

        # Cap at max delay
        delay = min(delay, self.max_delay)

        # Add jitter if enabled
        if self.jitter:
            delay = delay * (0.5 + random.random())

        return delay


def retry_on_error(
    config: Optional[RetryConfig] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to retry async functions on transient errors.

    Args:
        config: Retry configuration

    Returns:
        Decorator function
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Optional[Exception] = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    # Check if error is retryable
                    if not is_retryable_error(e):
                        logger.warning(
                            f"Non-retryable error in {func.__name__}",
                            error=str(e),
                        )
                        raise

                    # Check if this was the last attempt
                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"Max retries exceeded for {func.__name__}",
                            attempts=config.max_attempts,
                            error=str(e),
                        )
                        raise

                    # Calculate delay and wait
                    delay = config.get_delay(attempt)
                    logger.warning(
                        f"Retrying {func.__name__} after error",
                        attempt=attempt + 1,
                        max_attempts=config.max_attempts,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)

            # Should never reach here, but just in case
            if last_error:
                raise last_error
            raise RuntimeError(f"Retry logic failed for {func.__name__}")

        return wrapper

    return decorator


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    config: Optional[RetryConfig] = None,
    **kwargs: Any,
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments for function
        config: Retry configuration
        **kwargs: Keyword arguments for function

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()

    last_error: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e

            if not is_retryable_error(e):
                raise

            if attempt == config.max_attempts - 1:
                logger.error(
                    "Max retries exceeded",
                    function=func.__name__,
                    attempts=config.max_attempts,
                    error=str(e),
                )
                raise

            delay = config.get_delay(attempt)
            logger.warning(
                "Retrying after error",
                function=func.__name__,
                attempt=attempt + 1,
                max_attempts=config.max_attempts,
                delay=delay,
                error=str(e),
            )
            await asyncio.sleep(delay)

    if last_error:
        raise last_error
    raise RuntimeError("Retry logic failed")


class RetryPolicy:
    """
    Retry policy for different operation types.

    Provides predefined retry configurations.
    """

    # Quick operations (search, get)
    QUICK = RetryConfig(
        max_attempts=2,
        initial_delay=0.5,
        max_delay=2.0,
        exponential_base=2.0,
    )

    # Standard operations (upsert, delete)
    STANDARD = RetryConfig(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        exponential_base=2.0,
    )

    # Long operations (batch, collection create)
    LONG = RetryConfig(
        max_attempts=5,
        initial_delay=2.0,
        max_delay=60.0,
        exponential_base=2.0,
    )

    # Critical operations (health check, ping)
    CRITICAL = RetryConfig(
        max_attempts=3,
        initial_delay=0.1,
        max_delay=1.0,
        exponential_base=1.5,
    )
