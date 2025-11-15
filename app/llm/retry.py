"""
Retry logic for LLM providers.

Sandi Metz Principles:
- Single Responsibility: Manage retry logic
- Small methods: Each method < 10 lines
- Dependency Injection: Configuration injected
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from anthropic import (
    APIConnectionError as AnthropicConnectionError,
    APITimeoutError as AnthropicTimeoutError,
    InternalServerError as AnthropicInternalServerError,
    RateLimitError as AnthropicRateLimitError,
)
from openai import (
    APIConnectionError as OpenAIConnectionError,
    APITimeoutError as OpenAITimeoutError,
    InternalServerError as OpenAIInternalServerError,
    RateLimitError as OpenAIRateLimitError,
)

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Retry configuration."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0


class RetryHandler:
    """
    Exponential backoff retry handler.

    Retries failed operations with increasing delays.
    """

    def __init__(self, config: RetryConfig | None = None):
        """
        Initialize retry handler.

        Args:
            config: Retry configuration (uses defaults if None)
        """
        self._config = config or RetryConfig()

    async def execute(self, func: Callable[[], Any]) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute

        Returns:
            Function result

        Raises:
            Exception: If all retries exhausted
        """
        last_exception = None

        for attempt in range(1, self._config.max_attempts + 1):
            try:
                return await func()
            except self._get_retryable_exceptions() as e:
                last_exception = e
                if attempt == self._config.max_attempts:
                    logger.error(f"All {attempt} retry attempts failed", error=str(e))
                    raise

                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt} failed, retrying in {delay:.2f}s", error=str(e)
                )
                await asyncio.sleep(delay)

        raise last_exception  # type: ignore

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for attempt using exponential backoff.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        delay = self._config.initial_delay * (
            self._config.exponential_base ** (attempt - 1)
        )
        return min(delay, self._config.max_delay)

    @staticmethod
    def _get_retryable_exceptions() -> tuple:
        """
        Get tuple of retryable exceptions.

        Returns:
            Tuple of exception types that should be retried
        """
        return (
            # OpenAI errors
            OpenAIRateLimitError,
            OpenAITimeoutError,
            OpenAIConnectionError,
            OpenAIInternalServerError,
            # Anthropic errors
            AnthropicRateLimitError,
            AnthropicTimeoutError,
            AnthropicConnectionError,
            AnthropicInternalServerError,
        )
