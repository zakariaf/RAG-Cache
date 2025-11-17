"""Tests for LLM circuit breaker."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions import LLMProviderError
from app.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)


@pytest.fixture
def mock_sleep():
    """Mock asyncio.sleep to make tests instant."""
    with patch("asyncio.sleep", new=AsyncMock()) as mock:
        yield mock


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 2

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=30.0, success_threshold=1
        )

        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.success_threshold == 1


class TestCircuitBreaker:
    """Test circuit breaker."""

    @pytest.mark.asyncio
    async def test_execute_successful_operation(self):
        """Test executing successful operation."""
        breaker = CircuitBreaker()

        async def success_operation():
            return "success"

        result = await breaker.execute(success_operation)

        assert result == "success"
        assert breaker.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_execute_failed_operation(self):
        """Test executing failed operation."""
        breaker = CircuitBreaker()

        async def failing_operation():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await breaker.execute(failing_operation)

        assert breaker.get_failure_count() == 1
        assert breaker.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        async def failing_operation():
            raise ValueError("fail")

        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.execute(failing_operation)

        # Circuit should be open
        assert breaker.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_blocks_requests(self):
        """Test open circuit blocks new requests."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)

        async def failing_operation():
            raise ValueError("fail")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.execute(failing_operation)

        # Next request should be blocked
        with pytest.raises(LLMProviderError) as exc_info:
            await breaker.execute(failing_operation)

        assert "OPEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, mock_sleep):
        """Test circuit transitions to half-open after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=0.1  # Short timeout for testing
        )
        breaker = CircuitBreaker(config)

        async def failing_operation():
            raise ValueError("fail")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.execute(failing_operation)

        assert breaker.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Check state before executing - circuit should still be OPEN
        # but will transition to HALF_OPEN on next request
        assert breaker.get_state() == CircuitState.OPEN

        # This should transition to half-open and fail
        with pytest.raises(ValueError):
            await breaker.execute(failing_operation)

        # After failure in half-open, should be OPEN again
        assert breaker.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self, mock_sleep):
        """Test successful operations in half-open close circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=0.1, success_threshold=2
        )
        breaker = CircuitBreaker(config)

        call_count = 0

        async def conditional_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("fail")
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.execute(conditional_operation)

        assert breaker.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Execute 2 successful operations to close circuit
        result1 = await breaker.execute(conditional_operation)
        result2 = await breaker.execute(conditional_operation)

        assert result1 == "success"
        assert result2 == "success"
        assert breaker.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, mock_sleep):
        """Test failure in half-open reopens circuit."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        breaker = CircuitBreaker(config)

        async def failing_operation():
            raise ValueError("fail")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.execute(failing_operation)

        # Wait for recovery
        await asyncio.sleep(0.15)

        # Fail in half-open state
        with pytest.raises(ValueError):
            await breaker.execute(failing_operation)

        # Circuit should be open again
        assert breaker.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Test success resets failure count in closed state."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        call_count = 0

        async def conditional_operation():
            nonlocal call_count
            call_count += 1
            if call_count in [1, 2]:  # First two calls fail
                raise ValueError("fail")
            return "success"

        # Two failures
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.execute(conditional_operation)

        assert breaker.get_failure_count() == 2

        # One success
        await breaker.execute(conditional_operation)

        # Failure count should be reset
        assert breaker.get_failure_count() == 0
        assert breaker.get_state() == CircuitState.CLOSED

    def test_get_state(self):
        """Test getting circuit state."""
        breaker = CircuitBreaker()

        assert breaker.get_state() == CircuitState.CLOSED

    def test_reset(self):
        """Test manual reset of circuit breaker."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)

        # Manually set to open (simulate failures)
        breaker._state = CircuitState.OPEN
        breaker._failure_count = 5

        breaker.reset()

        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.get_failure_count() == 0

    def test_get_failure_count(self):
        """Test getting failure count."""
        breaker = CircuitBreaker()

        assert breaker.get_failure_count() == 0

        breaker._failure_count = 3

        assert breaker.get_failure_count() == 3

    def test_get_success_count(self):
        """Test getting success count."""
        breaker = CircuitBreaker()

        assert breaker.get_success_count() == 0

        breaker._success_count = 2

        assert breaker.get_success_count() == 2

    @pytest.mark.asyncio
    async def test_multiple_successes_keep_circuit_closed(self):
        """Test multiple successes keep circuit closed."""
        breaker = CircuitBreaker()

        async def success_operation():
            return "ok"

        for _ in range(10):
            result = await breaker.execute(success_operation)
            assert result == "ok"

        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.get_failure_count() == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_different_exceptions(self):
        """Test circuit breaker handles different exception types."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)

        async def value_error():
            raise ValueError("error1")

        async def type_error():
            raise TypeError("error2")

        # Different exceptions should all count as failures
        with pytest.raises(ValueError):
            await breaker.execute(value_error)

        with pytest.raises(TypeError):
            await breaker.execute(type_error)

        # Circuit should be open
        assert breaker.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_recovery_timeout_calculation(self, mock_sleep):
        """Test recovery timeout is properly calculated."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=1.0)
        breaker = CircuitBreaker(config)

        async def failing_operation():
            raise ValueError("fail")

        # Open circuit
        with pytest.raises(ValueError):
            await breaker.execute(failing_operation)

        assert breaker.get_state() == CircuitState.OPEN

        # Should still be blocked before timeout
        with pytest.raises(LLMProviderError):
            await breaker.execute(failing_operation)

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Should attempt recovery (transition to half-open)
        with pytest.raises(ValueError):
            await breaker.execute(failing_operation)

    @pytest.mark.asyncio
    async def test_state_transitions_logged(self, mock_sleep):
        """Test that state transitions occur correctly."""
        config = CircuitBreakerConfig(
            failure_threshold=1, recovery_timeout=0.1, success_threshold=1
        )
        breaker = CircuitBreaker(config)

        call_count = 0

        async def conditional_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("fail")
            return "success"

        # Start in CLOSED
        assert breaker.get_state() == CircuitState.CLOSED

        # Transition to OPEN
        with pytest.raises(ValueError):
            await breaker.execute(conditional_operation)
        assert breaker.get_state() == CircuitState.OPEN

        # Wait and transition to HALF_OPEN, then to CLOSED
        await asyncio.sleep(0.15)
        await breaker.execute(conditional_operation)
        assert breaker.get_state() == CircuitState.CLOSED
