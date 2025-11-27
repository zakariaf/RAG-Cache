"""
Pipeline Error Recovery.

Handles errors and recovery strategies in the query pipeline.

Sandi Metz Principles:
- Single Responsibility: Error recovery
- Strategy Pattern: Pluggable recovery strategies
- Graceful degradation
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from app.exceptions import AppError, CacheError, EmbeddingError, LLMProviderError
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RecoveryAction(str, Enum):
    """Actions to take on error."""

    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    FAIL = "fail"


@dataclass
class RecoveryResult:
    """Result of recovery attempt."""

    success: bool
    action_taken: RecoveryAction
    result: Optional[Any] = None
    error: Optional[Exception] = None
    retries_used: int = 0


class ErrorRecoveryStrategy:
    """
    Base class for error recovery strategies.

    Override handle_error to implement custom recovery.
    """

    def should_retry(self, error: Exception, attempt: int, max_retries: int) -> bool:
        """
        Determine if operation should be retried.

        Args:
            error: The exception that occurred
            attempt: Current attempt number
            max_retries: Maximum allowed retries

        Returns:
            True if should retry
        """
        if attempt >= max_retries:
            return False

        # Retry on transient errors
        return self._is_transient_error(error)

    def _is_transient_error(self, error: Exception) -> bool:
        """Check if error is transient (worth retrying)."""
        transient_indicators = [
            "timeout",
            "connection",
            "temporary",
            "rate limit",
            "503",
            "502",
            "504",
        ]
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in transient_indicators)

    def get_backoff_delay(self, attempt: int) -> float:
        """
        Get exponential backoff delay.

        Args:
            attempt: Current attempt number

        Returns:
            Delay in seconds
        """
        return min(2**attempt * 0.1, 10.0)  # Max 10 seconds


class CacheErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for cache errors."""

    def should_retry(self, error: Exception, attempt: int, max_retries: int) -> bool:
        """Cache errors generally shouldn't block - skip to LLM."""
        return False

    def get_action(self, error: Exception) -> RecoveryAction:
        """Get action for cache error."""
        logger.warning("Cache error, skipping to LLM", error=str(error))
        return RecoveryAction.SKIP


class LLMErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for LLM errors."""

    def get_action(self, error: Exception, attempt: int, max_retries: int) -> RecoveryAction:
        """Get action for LLM error."""
        if self.should_retry(error, attempt, max_retries):
            return RecoveryAction.RETRY
        if self._has_fallback_provider():
            return RecoveryAction.FALLBACK
        return RecoveryAction.FAIL

    def _has_fallback_provider(self) -> bool:
        """Check if fallback provider is available."""
        # Would check config for fallback providers
        return False


class EmbeddingErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for embedding errors."""

    def get_action(self, error: Exception) -> RecoveryAction:
        """Get action for embedding error."""
        # Embedding errors skip semantic cache, try exact cache or LLM
        logger.warning("Embedding error, skipping semantic cache", error=str(error))
        return RecoveryAction.SKIP


class PipelineErrorHandler:
    """
    Centralized error handler for pipeline.

    Coordinates recovery strategies.
    """

    def __init__(
        self,
        max_retries: int = 3,
        enable_recovery: bool = True,
    ):
        """
        Initialize error handler.

        Args:
            max_retries: Maximum retry attempts
            enable_recovery: Whether to attempt recovery
        """
        self._max_retries = max_retries
        self._enable_recovery = enable_recovery

        # Strategy mapping
        self._strategies = {
            CacheError: CacheErrorRecovery(),
            LLMProviderError: LLMErrorRecovery(),
            EmbeddingError: EmbeddingErrorRecovery(),
        }
        self._default_strategy = ErrorRecoveryStrategy()

    def get_strategy(self, error: Exception) -> ErrorRecoveryStrategy:
        """Get recovery strategy for error type."""
        for error_type, strategy in self._strategies.items():
            if isinstance(error, error_type):
                return strategy
        return self._default_strategy

    async def execute_with_recovery(
        self,
        operation: Callable[[], T],
        fallback: Optional[Callable[[], T]] = None,
        context: str = "operation",
    ) -> RecoveryResult:
        """
        Execute operation with error recovery.

        Args:
            operation: Async operation to execute
            fallback: Optional fallback operation
            context: Context for logging

        Returns:
            RecoveryResult with outcome
        """
        attempt = 0

        while True:
            try:
                result = await operation()
                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.RETRY if attempt > 0 else RecoveryAction.SKIP,
                    result=result,
                    retries_used=attempt,
                )
            except Exception as e:
                attempt += 1
                strategy = self.get_strategy(e)

                logger.warning(
                    "Pipeline operation failed",
                    context=context,
                    attempt=attempt,
                    error=str(e),
                )

                # Check if should retry
                if strategy.should_retry(e, attempt, self._max_retries):
                    delay = strategy.get_backoff_delay(attempt)
                    logger.info(
                        "Retrying operation",
                        context=context,
                        attempt=attempt,
                        delay=delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                # Try fallback if available
                if fallback and self._enable_recovery:
                    try:
                        result = await fallback()
                        return RecoveryResult(
                            success=True,
                            action_taken=RecoveryAction.FALLBACK,
                            result=result,
                            retries_used=attempt,
                        )
                    except Exception as fallback_error:
                        logger.error(
                            "Fallback also failed",
                            context=context,
                            error=str(fallback_error),
                        )

                # Return failure
                return RecoveryResult(
                    success=False,
                    action_taken=RecoveryAction.FAIL,
                    error=e,
                    retries_used=attempt,
                )

    def should_skip_cache(self, error: Exception) -> bool:
        """Determine if cache should be skipped after error."""
        return isinstance(error, (CacheError, EmbeddingError))


# Convenience function
async def with_recovery(
    operation: Callable[[], T],
    fallback: Optional[Callable[[], T]] = None,
    max_retries: int = 3,
    context: str = "operation",
) -> RecoveryResult:
    """
    Execute operation with default recovery.

    Args:
        operation: Async operation to execute
        fallback: Optional fallback
        max_retries: Max retry attempts
        context: Context for logging

    Returns:
        RecoveryResult
    """
    handler = PipelineErrorHandler(max_retries=max_retries)
    return await handler.execute_with_recovery(operation, fallback, context)

