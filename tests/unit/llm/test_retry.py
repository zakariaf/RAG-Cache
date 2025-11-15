"""
Tests for retry handler.
"""

import pytest
from openai import RateLimitError, APITimeoutError, APIConnectionError
from anthropic import RateLimitError as AnthropicRateLimitError

from app.llm.retry import RetryHandler, RetryConfig


class TestRetryHandler:
    """Test retry handler functionality."""

    @pytest.fixture
    def config(self) -> RetryConfig:
        """Create test retry config."""
        return RetryConfig(
            max_attempts=3, initial_delay=0.1, max_delay=1.0, exponential_base=2.0
        )

    @pytest.fixture
    def retry_handler(self, config: RetryConfig) -> RetryHandler:
        """Create retry handler instance."""
        return RetryHandler(config)

    @pytest.mark.asyncio
    async def test_execute_success_first_attempt(
        self, retry_handler: RetryHandler
    ) -> None:
        """Test successful execution on first attempt."""
        call_count = 0

        async def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_handler.execute(success_func)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_execute_retry_on_retryable_error(
        self, retry_handler: RetryHandler
    ) -> None:
        """Test retry on retryable errors."""
        call_count = 0

        async def failing_then_success() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("Rate limit exceeded", response=None, body=None)
            return "success"

        result = await retry_handler.execute(failing_then_success)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_exhausts_retries(self, retry_handler: RetryHandler) -> None:
        """Test that all retries are exhausted on persistent failure."""
        call_count = 0

        async def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise APITimeoutError("Timeout")

        with pytest.raises(APITimeoutError):
            await retry_handler.execute(always_fails)

        assert call_count == 3  # max_attempts

    @pytest.mark.asyncio
    async def test_execute_with_connection_error(
        self, retry_handler: RetryHandler
    ) -> None:
        """Test retry on API connection errors."""
        call_count = 0

        async def connection_error_then_success() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIConnectionError("Connection failed")
            return "success"

        result = await retry_handler.execute(connection_error_then_success)
        assert result == "success"
        assert call_count == 2

    def test_calculate_delay_exponential_backoff(
        self, retry_handler: RetryHandler
    ) -> None:
        """Test exponential backoff delay calculation."""
        # Initial delay = 0.1, base = 2.0
        assert retry_handler._calculate_delay(1) == 0.1  # 0.1 * 2^0
        assert retry_handler._calculate_delay(2) == 0.2  # 0.1 * 2^1
        assert retry_handler._calculate_delay(3) == 0.4  # 0.1 * 2^2

    def test_calculate_delay_respects_max(self, retry_handler: RetryHandler) -> None:
        """Test that delay respects maximum."""
        # Even with high attempt number, should not exceed max_delay
        delay = retry_handler._calculate_delay(20)
        assert delay == 1.0  # max_delay

    def test_get_retryable_exceptions(self, retry_handler: RetryHandler) -> None:
        """Test retryable exceptions list."""
        exceptions = retry_handler._get_retryable_exceptions()
        # OpenAI exceptions
        assert RateLimitError in exceptions
        assert APITimeoutError in exceptions
        assert APIConnectionError in exceptions
        # Anthropic exceptions
        assert AnthropicRateLimitError in exceptions

    @pytest.mark.asyncio
    async def test_execute_non_retryable_error_fails_immediately(
        self, retry_handler: RetryHandler
    ) -> None:
        """Test that non-retryable errors fail immediately."""
        call_count = 0

        async def non_retryable_error() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            await retry_handler.execute(non_retryable_error)

        assert call_count == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_default_config(self) -> None:
        """Test retry handler with default configuration."""
        handler = RetryHandler()
        call_count = 0

        async def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await handler.execute(success_func)
        assert result == "success"
        assert call_count == 1
