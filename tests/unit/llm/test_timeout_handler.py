"""Tests for LLM timeout handler."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions import LLMProviderError
from app.llm.timeout_handler import TimeoutConfig, TimeoutHandler


@pytest.fixture
def mock_sleep():
    """Mock asyncio.sleep to make tests instant."""
    with patch("asyncio.sleep", new=AsyncMock()) as mock:
        yield mock


class TestTimeoutConfig:
    """Test timeout configuration."""

    def test_default_config(self):
        """Test default timeout configuration."""
        config = TimeoutConfig()

        assert config.timeout_seconds == 30.0
        assert config.raise_on_timeout is True

    def test_custom_timeout(self):
        """Test custom timeout value."""
        config = TimeoutConfig(timeout_seconds=60.0)

        assert config.timeout_seconds == 60.0

    def test_custom_raise_on_timeout(self):
        """Test custom raise_on_timeout."""
        config = TimeoutConfig(raise_on_timeout=False)

        assert config.raise_on_timeout is False

    def test_full_custom_config(self):
        """Test fully custom configuration."""
        config = TimeoutConfig(timeout_seconds=45.0, raise_on_timeout=False)

        assert config.timeout_seconds == 45.0
        assert config.raise_on_timeout is False


class TestTimeoutHandler:
    """Test timeout handler."""

    @pytest.mark.asyncio
    async def test_execute_successful_operation(self, mock_sleep):
        """Test executing operation that completes in time."""
        handler = TimeoutHandler()

        async def fast_operation():
            await asyncio.sleep(0.01)
            return "success"

        result = await handler.execute(fast_operation)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_timeout_raises_error(self, mock_sleep):
        """Test timeout raises error when configured."""
        config = TimeoutConfig(timeout_seconds=0.1, raise_on_timeout=True)
        handler = TimeoutHandler(config)

        async def slow_operation():
            await asyncio.sleep(1.0)
            return "never"

        with pytest.raises(LLMProviderError) as exc_info:
            await handler.execute(slow_operation)

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_with_timeout_returns_none(self, mock_sleep):
        """Test timeout returns None when not raising."""
        config = TimeoutConfig(timeout_seconds=0.1, raise_on_timeout=False)
        handler = TimeoutHandler(config)

        async def slow_operation():
            await asyncio.sleep(1.0)
            return "never"

        result = await handler.execute(slow_operation)

        assert result is None

    @pytest.mark.asyncio
    async def test_execute_with_custom_timeout(self, mock_sleep):
        """Test execute with custom timeout override."""
        config = TimeoutConfig(timeout_seconds=1.0)
        handler = TimeoutHandler(config)

        async def medium_operation():
            await asyncio.sleep(0.2)
            return "done"

        # Should timeout with 0.1 override
        with pytest.raises(LLMProviderError):
            await handler.execute(medium_operation, timeout_seconds=0.1)

    @pytest.mark.asyncio
    async def test_execute_custom_timeout_success(self, mock_sleep):
        """Test execute with custom timeout that succeeds."""
        config = TimeoutConfig(timeout_seconds=0.1)
        handler = TimeoutHandler(config)

        async def medium_operation():
            await asyncio.sleep(0.2)
            return "done"

        # Should succeed with 1.0 override
        result = await handler.execute(medium_operation, timeout_seconds=1.0)

        assert result == "done"

    @pytest.mark.asyncio
    async def test_execute_with_return_value(self):
        """Test execute returns correct value."""
        handler = TimeoutHandler()

        async def operation_with_value():
            return 42

        result = await handler.execute(operation_with_value)

        assert result == 42

    @pytest.mark.asyncio
    async def test_execute_with_complex_return(self):
        """Test execute with complex return type."""
        handler = TimeoutHandler()

        async def operation_with_dict():
            return {"key": "value", "number": 123}

        result = await handler.execute(operation_with_dict)

        assert result == {"key": "value", "number": 123}

    def test_get_timeout(self):
        """Test getting timeout value."""
        config = TimeoutConfig(timeout_seconds=45.0)
        handler = TimeoutHandler(config)

        timeout = handler.get_timeout()

        assert timeout == 45.0

    def test_get_timeout_default(self):
        """Test getting default timeout."""
        handler = TimeoutHandler()

        timeout = handler.get_timeout()

        assert timeout == 30.0

    def test_update_timeout(self):
        """Test updating timeout value."""
        handler = TimeoutHandler()

        handler.update_timeout(60.0)

        assert handler.get_timeout() == 60.0

    @pytest.mark.asyncio
    async def test_updated_timeout_takes_effect(self, mock_sleep):
        """Test that updated timeout is used in execution."""
        config = TimeoutConfig(timeout_seconds=0.1, raise_on_timeout=True)
        handler = TimeoutHandler(config)

        async def medium_operation():
            await asyncio.sleep(0.2)
            return "done"

        # Should timeout with initial config
        with pytest.raises(LLMProviderError):
            await handler.execute(medium_operation)

        # Update timeout and try again
        handler.update_timeout(1.0)
        result = await handler.execute(medium_operation)

        assert result == "done"

    @pytest.mark.asyncio
    async def test_execute_handles_immediate_return(self):
        """Test execute with operation that returns immediately."""
        handler = TimeoutHandler()

        async def immediate_operation():
            return "instant"

        result = await handler.execute(immediate_operation)

        assert result == "instant"

    @pytest.mark.asyncio
    async def test_multiple_executions(self):
        """Test handler can be reused for multiple operations."""
        handler = TimeoutHandler()

        async def operation1():
            return "first"

        async def operation2():
            return "second"

        result1 = await handler.execute(operation1)
        result2 = await handler.execute(operation2)

        assert result1 == "first"
        assert result2 == "second"

    @pytest.mark.asyncio
    async def test_timeout_error_message_includes_duration(self, mock_sleep):
        """Test timeout error message includes timeout duration."""
        config = TimeoutConfig(timeout_seconds=0.5, raise_on_timeout=True)
        handler = TimeoutHandler(config)

        async def slow_operation():
            await asyncio.sleep(2.0)

        with pytest.raises(LLMProviderError) as exc_info:
            await handler.execute(slow_operation)

        assert "0.5" in str(exc_info.value)
