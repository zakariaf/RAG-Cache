"""
LLM timeout handler.

Sandi Metz Principles:
- Single Responsibility: Handle request timeouts
- Small methods: Each method < 10 lines
- Clear naming: Self-documenting code
"""

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

from app.exceptions import LLMProviderError
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class TimeoutConfig:
    """Configuration for timeout handling."""

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        raise_on_timeout: bool = True,
    ):
        """
        Initialize timeout configuration.

        Args:
            timeout_seconds: Timeout in seconds (default: 30)
            raise_on_timeout: Raise exception on timeout (default: True)
        """
        self.timeout_seconds = timeout_seconds
        self.raise_on_timeout = raise_on_timeout


class TimeoutHandler:
    """
    Handler for managing request timeouts.

    Wraps async operations with timeout protection.
    """

    def __init__(self, config: TimeoutConfig | None = None):
        """
        Initialize timeout handler.

        Args:
            config: Timeout configuration (creates default if None)
        """
        self._config = config or TimeoutConfig()

    async def execute(
        self,
        operation: Callable[[], Awaitable[T]],
        timeout_seconds: float | None = None,
    ) -> T:
        """
        Execute operation with timeout.

        Args:
            operation: Async function to execute
            timeout_seconds: Optional override timeout (uses config if None)

        Returns:
            Operation result

        Raises:
            LLMProviderError: If operation times out and raise_on_timeout is True
        """
        timeout = timeout_seconds or self._config.timeout_seconds

        try:
            return await asyncio.wait_for(operation(), timeout=timeout)
        except asyncio.TimeoutError as e:
            return self._handle_timeout(timeout, e)

    def _handle_timeout(self, timeout: float, error: Exception) -> Any:
        """
        Handle timeout error.

        Args:
            timeout: Timeout value that was exceeded
            error: Timeout exception

        Returns:
            None (or raises exception)

        Raises:
            LLMProviderError: If raise_on_timeout is True
        """
        error_msg = f"Request timed out after {timeout} seconds"
        logger.error("Request timeout", timeout=timeout)

        if self._config.raise_on_timeout:
            raise LLMProviderError(error_msg) from error

        return None

    def get_timeout(self) -> float:
        """
        Get configured timeout value.

        Returns:
            Timeout in seconds
        """
        return self._config.timeout_seconds

    def update_timeout(self, timeout_seconds: float) -> None:
        """
        Update timeout configuration.

        Args:
            timeout_seconds: New timeout value in seconds
        """
        self._config.timeout_seconds = timeout_seconds
        logger.info("Updated timeout", timeout=timeout_seconds)
