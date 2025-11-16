"""
Pipeline error recovery strategies.

Provides error recovery mechanisms for query processing pipeline.

Sandi Metz Principles:
- Single Responsibility: Error recovery
- Small classes: Focused recovery strategies
- Strategy Pattern: Pluggable recovery logic
"""

import time
from enum import Enum
from typing import Any, Callable, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class RecoveryAction(Enum):
    """Error recovery actions."""

    RETRY = "retry"
    SKIP = "skip"
    FAIL = "fail"
    FALLBACK = "fallback"


class ErrorRecoveryStrategy:
    """
    Base class for error recovery strategies.

    Defines how to handle errors in pipeline processing.
    """

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if operation should be retried.

        Args:
            error: Exception that occurred
            attempt: Current attempt number (1-indexed)

        Returns:
            True if should retry
        """
        return False

    def get_retry_delay(self, attempt: int) -> float:
        """
        Get delay before retry.

        Args:
            attempt: Current attempt number

        Returns:
            Delay in seconds
        """
        return 0.0

    def handle_error(
        self, error: Exception, context: dict
    ) -> tuple[RecoveryAction, Any]:
        """
        Handle error and determine recovery action.

        Args:
            error: Exception that occurred
            context: Error context dictionary

        Returns:
            Tuple of (action, value) where value depends on action
        """
        return RecoveryAction.FAIL, None


class RetryStrategy(ErrorRecoveryStrategy):
    """
    Retry error recovery strategy.

    Retries failed operations with exponential backoff.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
    ):
        """
        Initialize retry strategy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
        """
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._exponential_base = exponential_base

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Check if should retry."""
        return attempt <= self._max_retries

    def get_retry_delay(self, attempt: int) -> float:
        """Get exponential backoff delay."""
        delay = self._base_delay * (self._exponential_base ** (attempt - 1))
        return min(delay, self._max_delay)

    def handle_error(
        self, error: Exception, context: dict
    ) -> tuple[RecoveryAction, Any]:
        """Handle error with retry logic."""
        attempt = context.get("attempt", 1)

        if self.should_retry(error, attempt):
            delay = self.get_retry_delay(attempt)
            logger.info(
                "Retrying after error",
                attempt=attempt,
                max_retries=self._max_retries,
                delay=delay,
                error=str(error),
            )
            return RecoveryAction.RETRY, delay

        logger.error(
            "Max retries exceeded",
            attempt=attempt,
            error=str(error),
        )
        return RecoveryAction.FAIL, None


class FallbackStrategy(ErrorRecoveryStrategy):
    """
    Fallback error recovery strategy.

    Uses fallback value or function when error occurs.
    """

    def __init__(
        self,
        fallback: Any,
        is_callable: bool = False,
    ):
        """
        Initialize fallback strategy.

        Args:
            fallback: Fallback value or callable
            is_callable: If True, fallback is called to get value
        """
        self._fallback = fallback
        self._is_callable = is_callable

    def handle_error(
        self, error: Exception, context: dict
    ) -> tuple[RecoveryAction, Any]:
        """Handle error with fallback."""
        logger.warning(
            "Using fallback after error",
            error=str(error),
            has_callable=self._is_callable,
        )

        if self._is_callable and callable(self._fallback):
            try:
                fallback_value = self._fallback(error, context)
                return RecoveryAction.FALLBACK, fallback_value
            except Exception as fallback_error:
                logger.error(
                    "Fallback callable failed",
                    error=str(fallback_error),
                )
                return RecoveryAction.FAIL, None

        return RecoveryAction.FALLBACK, self._fallback


class SkipStrategy(ErrorRecoveryStrategy):
    """
    Skip error recovery strategy.

    Skips failed operations and continues.
    """

    def handle_error(
        self, error: Exception, context: dict
    ) -> tuple[RecoveryAction, Any]:
        """Handle error by skipping."""
        logger.warning(
            "Skipping after error",
            error=str(error),
        )
        return RecoveryAction.SKIP, None


class ErrorRecoveryManager:
    """
    Manages error recovery in pipelines.

    Coordinates recovery strategies and executes recovery actions.
    """

    def __init__(self, strategy: Optional[ErrorRecoveryStrategy] = None):
        """
        Initialize recovery manager.

        Args:
            strategy: Recovery strategy to use
        """
        self._strategy = strategy or ErrorRecoveryStrategy()
        self._error_counts: dict[str, int] = {}

    async def execute_with_recovery(
        self,
        operation: Callable,
        operation_id: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute operation with error recovery.

        Args:
            operation: Async operation to execute
            operation_id: Unique operation identifier
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Operation result

        Raises:
            Exception: If all recovery attempts fail
        """
        attempt = 1
        max_attempts = 10  # Safety limit

        while attempt <= max_attempts:
            try:
                # Execute operation
                logger.debug(
                    "Executing operation",
                    operation_id=operation_id,
                    attempt=attempt,
                )

                result = await operation(*args, **kwargs)

                # Success - reset error count
                if operation_id in self._error_counts:
                    del self._error_counts[operation_id]

                return result

            except Exception as error:
                # Track error
                self._error_counts[operation_id] = (
                    self._error_counts.get(operation_id, 0) + 1
                )

                # Get recovery action
                context = {
                    "operation_id": operation_id,
                    "attempt": attempt,
                    "error_count": self._error_counts[operation_id],
                }

                action, value = self._strategy.handle_error(error, context)

                # Execute recovery action
                if action == RecoveryAction.RETRY:
                    delay = value or 0.0
                    if delay > 0:
                        await self._delay(delay)
                    attempt += 1
                    continue

                elif action == RecoveryAction.FALLBACK:
                    logger.info(
                        "Using fallback value",
                        operation_id=operation_id,
                    )
                    return value

                elif action == RecoveryAction.SKIP:
                    logger.info(
                        "Skipping operation",
                        operation_id=operation_id,
                    )
                    return None

                else:  # FAIL
                    logger.error(
                        "Operation failed, no recovery",
                        operation_id=operation_id,
                        attempt=attempt,
                    )
                    raise

        # Safety limit reached
        raise RuntimeError(
            f"Operation {operation_id} exceeded maximum attempts ({max_attempts})"
        )

    async def _delay(self, seconds: float) -> None:
        """
        Delay execution.

        Args:
            seconds: Delay in seconds
        """
        import asyncio

        await asyncio.sleep(seconds)

    def get_error_count(self, operation_id: str) -> int:
        """
        Get error count for operation.

        Args:
            operation_id: Operation identifier

        Returns:
            Number of errors
        """
        return self._error_counts.get(operation_id, 0)

    def reset_error_count(self, operation_id: str) -> None:
        """
        Reset error count for operation.

        Args:
            operation_id: Operation identifier
        """
        if operation_id in self._error_counts:
            del self._error_counts[operation_id]

    def get_statistics(self) -> dict:
        """
        Get recovery statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_operations_with_errors": len(self._error_counts),
            "error_counts": self._error_counts.copy(),
        }


# Convenience functions
def create_retry_strategy(max_retries: int = 3) -> RetryStrategy:
    """
    Create retry strategy (convenience function).

    Args:
        max_retries: Maximum retry attempts

    Returns:
        RetryStrategy instance
    """
    return RetryStrategy(max_retries=max_retries)


def create_fallback_strategy(fallback: Any) -> FallbackStrategy:
    """
    Create fallback strategy (convenience function).

    Args:
        fallback: Fallback value

    Returns:
        FallbackStrategy instance
    """
    return FallbackStrategy(fallback=fallback)


def create_skip_strategy() -> SkipStrategy:
    """
    Create skip strategy (convenience function).

    Returns:
        SkipStrategy instance
    """
    return SkipStrategy()
