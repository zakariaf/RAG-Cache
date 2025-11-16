"""
LLM circuit breaker.

Sandi Metz Principles:
- Single Responsibility: Prevent cascading failures
- Small methods: Each method < 10 lines
- Clear naming: Self-documenting code
"""

import time
from enum import Enum
from typing import Awaitable, Callable, TypeVar

from app.exceptions import LLMProviderError
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker configuration.

        Args:
            failure_threshold: Failures before opening circuit (default: 5)
            recovery_timeout: Seconds before attempting recovery (default: 60)
            success_threshold: Successes needed to close from half-open (default: 2)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold


class CircuitBreaker:
    """
    Circuit breaker for LLM providers.

    Prevents cascading failures by blocking requests when error rate is high.
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        """
        Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration (creates default if None)
        """
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None

    async def execute(self, operation: Callable[[], Awaitable[T]]) -> T:
        """
        Execute operation through circuit breaker.

        Args:
            operation: Async function to execute

        Returns:
            Operation result

        Raises:
            LLMProviderError: If circuit is open or operation fails
        """
        if self._is_open():
            raise LLMProviderError("Circuit breaker is OPEN")

        try:
            result = await operation()
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _is_open(self) -> bool:
        """
        Check if circuit should be open.

        Returns:
            True if circuit is open and not ready to retry
        """
        if self._state == CircuitState.CLOSED:
            return False

        if self._state == CircuitState.HALF_OPEN:
            return False

        # Circuit is OPEN - check if recovery timeout has passed
        if self._should_attempt_reset():
            self._transition_to_half_open()
            return False

        return True

    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt recovery.

        Returns:
            True if recovery timeout has elapsed
        """
        if not self._last_failure_time:
            return False

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self._config.recovery_timeout

    def _on_success(self) -> None:
        """Handle successful operation."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                self._transition_to_closed()
        else:
            # Reset failure count on success in CLOSED state
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failure in half-open immediately reopens circuit
            self._transition_to_open()
        elif self._failure_count >= self._config.failure_threshold:
            self._transition_to_open()

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        logger.info("Circuit breaker closing", state="CLOSED")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        logger.warning("Circuit breaker opening", state="OPEN")
        self._state = CircuitState.OPEN
        self._success_count = 0

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        logger.info("Circuit breaker half-open", state="HALF_OPEN")
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._failure_count = 0

    def get_state(self) -> CircuitState:
        """
        Get current circuit state.

        Returns:
            Current circuit state
        """
        return self._state

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        logger.info("Circuit breaker manual reset")
        self._transition_to_closed()

    def get_failure_count(self) -> int:
        """
        Get current failure count.

        Returns:
            Number of consecutive failures
        """
        return self._failure_count

    def get_success_count(self) -> int:
        """
        Get current success count.

        Returns:
            Number of consecutive successes
        """
        return self._success_count
