"""Test pipeline error recovery."""

from unittest.mock import AsyncMock, patch

import pytest

from app.processing.error_recovery import (
    ErrorRecoveryManager,
    ErrorRecoveryStrategy,
    FallbackStrategy,
    RecoveryAction,
    RetryStrategy,
    SkipStrategy,
    create_fallback_strategy,
    create_retry_strategy,
    create_skip_strategy,
)


@pytest.fixture
def mock_sleep():
    """Mock asyncio.sleep to make tests instant."""
    with patch("asyncio.sleep", new=AsyncMock()) as mock:
        yield mock


class TestRecoveryAction:
    """Test RecoveryAction enum."""

    def test_recovery_actions(self):
        """Test recovery action values."""
        assert RecoveryAction.RETRY.value == "retry"
        assert RecoveryAction.SKIP.value == "skip"
        assert RecoveryAction.FAIL.value == "fail"
        assert RecoveryAction.FALLBACK.value == "fallback"


class TestErrorRecoveryStrategy:
    """Test base ErrorRecoveryStrategy class."""

    def test_should_retry_default(self):
        """Test default should_retry returns False."""
        strategy = ErrorRecoveryStrategy()

        assert strategy.should_retry(Exception("test"), 1) is False

    def test_get_retry_delay_default(self):
        """Test default retry delay is 0."""
        strategy = ErrorRecoveryStrategy()

        assert strategy.get_retry_delay(1) == 0.0

    def test_handle_error_default(self):
        """Test default handle_error fails."""
        strategy = ErrorRecoveryStrategy()

        action, value = strategy.handle_error(Exception("test"), {})

        assert action == RecoveryAction.FAIL
        assert value is None


class TestRetryStrategy:
    """Test RetryStrategy class."""

    def test_initialization(self):
        """Test retry strategy initialization."""
        strategy = RetryStrategy(
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0,
        )

        assert strategy._max_retries == 5
        assert strategy._base_delay == 2.0
        assert strategy._max_delay == 30.0

    def test_should_retry_within_limit(self):
        """Test should_retry returns True within limit."""
        strategy = RetryStrategy(max_retries=3)

        assert strategy.should_retry(Exception("test"), 1) is True
        assert strategy.should_retry(Exception("test"), 2) is True
        assert strategy.should_retry(Exception("test"), 3) is True

    def test_should_retry_exceeds_limit(self):
        """Test should_retry returns False when exceeded."""
        strategy = RetryStrategy(max_retries=3)

        assert strategy.should_retry(Exception("test"), 4) is False
        assert strategy.should_retry(Exception("test"), 5) is False

    def test_get_retry_delay_exponential(self):
        """Test exponential backoff delay."""
        strategy = RetryStrategy(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=100.0,
        )

        # delay = base_delay * (exponential_base ** (attempt - 1))
        assert strategy.get_retry_delay(1) == 1.0  # 1 * 2^0
        assert strategy.get_retry_delay(2) == 2.0  # 1 * 2^1
        assert strategy.get_retry_delay(3) == 4.0  # 1 * 2^2
        assert strategy.get_retry_delay(4) == 8.0  # 1 * 2^3

    def test_get_retry_delay_max_limit(self):
        """Test retry delay respects max limit."""
        strategy = RetryStrategy(
            base_delay=10.0,
            exponential_base=2.0,
            max_delay=15.0,
        )

        # Would be 20.0 but capped at 15.0
        assert strategy.get_retry_delay(2) == 15.0

    def test_handle_error_retry(self):
        """Test handle_error returns retry action."""
        strategy = RetryStrategy(max_retries=3)

        action, delay = strategy.handle_error(
            Exception("test"),
            {"attempt": 1},
        )

        assert action == RecoveryAction.RETRY
        assert delay == 1.0  # base_delay

    def test_handle_error_fail_after_max_retries(self):
        """Test handle_error fails after max retries."""
        strategy = RetryStrategy(max_retries=3)

        action, value = strategy.handle_error(
            Exception("test"),
            {"attempt": 4},
        )

        assert action == RecoveryAction.FAIL
        assert value is None


class TestFallbackStrategy:
    """Test FallbackStrategy class."""

    def test_initialization_with_value(self):
        """Test initialization with fallback value."""
        strategy = FallbackStrategy(fallback="default", is_callable=False)

        assert strategy._fallback == "default"
        assert strategy._is_callable is False

    def test_initialization_with_callable(self):
        """Test initialization with callable fallback."""

        def fallback_fn(e, c):
            return "computed"

        strategy = FallbackStrategy(fallback=fallback_fn, is_callable=True)

        assert strategy._fallback == fallback_fn
        assert strategy._is_callable is True

    def test_handle_error_with_value(self):
        """Test handle_error returns fallback value."""
        strategy = FallbackStrategy(fallback="default", is_callable=False)

        action, value = strategy.handle_error(Exception("test"), {})

        assert action == RecoveryAction.FALLBACK
        assert value == "default"

    def test_handle_error_with_callable(self):
        """Test handle_error calls fallback function."""

        def fallback_fn(error, context):
            return f"fallback: {str(error)}"

        strategy = FallbackStrategy(fallback=fallback_fn, is_callable=True)

        action, value = strategy.handle_error(Exception("test error"), {})

        assert action == RecoveryAction.FALLBACK
        assert value == "fallback: test error"

    def test_handle_error_callable_fails(self):
        """Test handle_error when callable raises error."""

        def failing_fallback(error, context):
            raise Exception("Fallback failed")

        strategy = FallbackStrategy(fallback=failing_fallback, is_callable=True)

        action, value = strategy.handle_error(Exception("test"), {})

        assert action == RecoveryAction.FAIL
        assert value is None


class TestSkipStrategy:
    """Test SkipStrategy class."""

    def test_handle_error(self):
        """Test handle_error returns skip action."""
        strategy = SkipStrategy()

        action, value = strategy.handle_error(Exception("test"), {})

        assert action == RecoveryAction.SKIP
        assert value is None


class TestErrorRecoveryManager:
    """Test ErrorRecoveryManager class."""

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution without errors."""
        manager = ErrorRecoveryManager()

        async def successful_operation():
            return "success"

        result = await manager.execute_with_recovery(
            successful_operation,
            "test_op",
        )

        assert result == "success"
        assert manager.get_error_count("test_op") == 0

    @pytest.mark.asyncio
    async def test_execute_with_retry(self, mock_sleep):
        """Test execution with retry strategy."""
        strategy = RetryStrategy(max_retries=3, base_delay=0.01)
        manager = ErrorRecoveryManager(strategy=strategy)

        call_count = []

        async def failing_then_success():
            call_count.append(1)
            if len(call_count) < 3:
                raise ValueError("Not yet")
            return "success"

        result = await manager.execute_with_recovery(
            failing_then_success,
            "test_op",
        )

        assert result == "success"
        assert len(call_count) == 3

    @pytest.mark.asyncio
    async def test_execute_retry_exhausted(self, mock_sleep):
        """Test execution fails after retry exhaustion."""
        strategy = RetryStrategy(max_retries=2, base_delay=0.01)
        manager = ErrorRecoveryManager(strategy=strategy)

        async def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await manager.execute_with_recovery(
                always_fails,
                "test_op",
            )

    @pytest.mark.asyncio
    async def test_execute_with_fallback(self):
        """Test execution with fallback strategy."""
        strategy = FallbackStrategy(fallback="fallback_value")
        manager = ErrorRecoveryManager(strategy=strategy)

        async def fails():
            raise ValueError("Failed")

        result = await manager.execute_with_recovery(
            fails,
            "test_op",
        )

        assert result == "fallback_value"

    @pytest.mark.asyncio
    async def test_execute_with_skip(self):
        """Test execution with skip strategy."""
        strategy = SkipStrategy()
        manager = ErrorRecoveryManager(strategy=strategy)

        async def fails():
            raise ValueError("Failed")

        result = await manager.execute_with_recovery(
            fails,
            "test_op",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_error_count_tracking(self, mock_sleep):
        """Test error count is tracked."""
        strategy = RetryStrategy(max_retries=2, base_delay=0.01)
        manager = ErrorRecoveryManager(strategy=strategy)

        async def fails_twice():
            if manager.get_error_count("test_op") < 2:
                raise ValueError("Not yet")
            return "success"

        await manager.execute_with_recovery(fails_twice, "test_op")

        # After success, error count should be reset
        assert manager.get_error_count("test_op") == 0

    @pytest.mark.asyncio
    async def test_reset_error_count(self, mock_sleep):
        """Test resetting error count."""
        strategy = RetryStrategy(max_retries=5, base_delay=0.01)
        manager = ErrorRecoveryManager(strategy=strategy)

        async def fails():
            raise ValueError("Failed")

        try:
            await manager.execute_with_recovery(fails, "test_op")
        except ValueError:
            pass

        # Error count should be > 0
        assert manager.get_error_count("test_op") > 0

        # Reset it
        manager.reset_error_count("test_op")
        assert manager.get_error_count("test_op") == 0

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test getting recovery statistics."""
        strategy = SkipStrategy()
        manager = ErrorRecoveryManager(strategy=strategy)

        async def fails():
            raise ValueError("Failed")

        await manager.execute_with_recovery(fails, "op1")
        await manager.execute_with_recovery(fails, "op2")

        stats = manager.get_statistics()

        assert stats["total_operations_with_errors"] == 2
        assert "op1" in stats["error_counts"]
        assert "op2" in stats["error_counts"]

    @pytest.mark.asyncio
    async def test_max_attempts_safety_limit(self, mock_sleep):
        """Test safety limit on max attempts."""
        # Strategy that always retries
        strategy = RetryStrategy(max_retries=999, base_delay=0.001)
        manager = ErrorRecoveryManager(strategy=strategy)

        async def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(RuntimeError, match="exceeded maximum attempts"):
            await manager.execute_with_recovery(always_fails, "test_op")


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_retry_strategy(self):
        """Test creating retry strategy."""
        strategy = create_retry_strategy(max_retries=5)

        assert isinstance(strategy, RetryStrategy)
        assert strategy._max_retries == 5

    def test_create_fallback_strategy(self):
        """Test creating fallback strategy."""
        strategy = create_fallback_strategy("default")

        assert isinstance(strategy, FallbackStrategy)
        assert strategy._fallback == "default"

    def test_create_skip_strategy(self):
        """Test creating skip strategy."""
        strategy = create_skip_strategy()

        assert isinstance(strategy, SkipStrategy)
