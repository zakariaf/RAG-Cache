"""Unit tests for Error Recovery."""

import pytest
from unittest.mock import AsyncMock

from app.exceptions import CacheError, LLMProviderError, EmbeddingError
from app.pipeline.error_recovery import (
    CacheErrorRecovery,
    LLMErrorRecovery,
    EmbeddingErrorRecovery,
    ErrorRecoveryStrategy,
    PipelineErrorHandler,
    RecoveryAction,
    RecoveryResult,
    with_recovery,
)


class TestErrorRecoveryStrategy:
    """Tests for ErrorRecoveryStrategy."""

    def test_should_retry_transient_error(self):
        """Test retry on transient errors."""
        strategy = ErrorRecoveryStrategy()

        # Transient errors should retry
        assert strategy.should_retry(Exception("connection timeout"), 0, 3) is True
        assert strategy.should_retry(Exception("rate limit exceeded"), 0, 3) is True

    def test_should_not_retry_after_max(self):
        """Test no retry after max attempts."""
        strategy = ErrorRecoveryStrategy()
        assert strategy.should_retry(Exception("timeout"), 3, 3) is False

    def test_should_not_retry_permanent_error(self):
        """Test no retry on permanent errors."""
        strategy = ErrorRecoveryStrategy()
        assert strategy.should_retry(Exception("invalid input"), 0, 3) is False

    def test_backoff_delay_exponential(self):
        """Test exponential backoff delay."""
        strategy = ErrorRecoveryStrategy()

        assert strategy.get_backoff_delay(1) == 0.2  # 2^1 * 0.1
        assert strategy.get_backoff_delay(2) == 0.4  # 2^2 * 0.1
        assert strategy.get_backoff_delay(3) == 0.8  # 2^3 * 0.1

    def test_backoff_delay_max(self):
        """Test backoff delay caps at max."""
        strategy = ErrorRecoveryStrategy()
        assert strategy.get_backoff_delay(10) == 10.0  # Capped at 10


class TestCacheErrorRecovery:
    """Tests for CacheErrorRecovery."""

    def test_should_not_retry(self):
        """Test cache errors don't retry."""
        strategy = CacheErrorRecovery()
        assert strategy.should_retry(CacheError("error"), 0, 3) is False

    def test_get_action_skip(self):
        """Test cache errors skip to LLM."""
        strategy = CacheErrorRecovery()
        action = strategy.get_action(CacheError("error"))
        assert action == RecoveryAction.SKIP


class TestLLMErrorRecovery:
    """Tests for LLMErrorRecovery."""

    def test_retry_on_transient(self):
        """Test LLM retries on transient errors."""
        strategy = LLMErrorRecovery()
        assert strategy.should_retry(LLMProviderError("timeout"), 0, 3) is True

    def test_get_action_retry(self):
        """Test LLM action is retry for transient."""
        strategy = LLMErrorRecovery()
        action = strategy.get_action(
            LLMProviderError("timeout"), attempt=0, max_retries=3
        )
        assert action == RecoveryAction.RETRY


class TestEmbeddingErrorRecovery:
    """Tests for EmbeddingErrorRecovery."""

    def test_get_action_skip(self):
        """Test embedding errors skip semantic cache."""
        strategy = EmbeddingErrorRecovery()
        action = strategy.get_action(EmbeddingError("error"))
        assert action == RecoveryAction.SKIP


class TestPipelineErrorHandler:
    """Tests for PipelineErrorHandler."""

    @pytest.fixture
    def handler(self):
        """Create error handler."""
        return PipelineErrorHandler(max_retries=3)

    def test_get_strategy_cache_error(self, handler):
        """Test getting strategy for cache error."""
        strategy = handler.get_strategy(CacheError("test"))
        assert isinstance(strategy, CacheErrorRecovery)

    def test_get_strategy_llm_error(self, handler):
        """Test getting strategy for LLM error."""
        strategy = handler.get_strategy(LLMProviderError("test"))
        assert isinstance(strategy, LLMErrorRecovery)

    def test_get_strategy_embedding_error(self, handler):
        """Test getting strategy for embedding error."""
        strategy = handler.get_strategy(EmbeddingError("test"))
        assert isinstance(strategy, EmbeddingErrorRecovery)

    def test_get_strategy_default(self, handler):
        """Test getting default strategy for unknown error."""
        strategy = handler.get_strategy(ValueError("test"))
        assert isinstance(strategy, ErrorRecoveryStrategy)

    @pytest.mark.asyncio
    async def test_execute_success(self, handler):
        """Test successful execution."""
        operation = AsyncMock(return_value="result")

        result = await handler.execute_with_recovery(operation, context="test")

        assert result.success is True
        assert result.result == "result"
        assert result.retries_used == 0

    @pytest.mark.asyncio
    async def test_execute_with_fallback(self, handler):
        """Test execution with fallback on failure."""
        operation = AsyncMock(side_effect=CacheError("failed"))
        fallback = AsyncMock(return_value="fallback result")

        result = await handler.execute_with_recovery(
            operation, fallback=fallback, context="test"
        )

        assert result.success is True
        assert result.result == "fallback result"
        assert result.action_taken == RecoveryAction.FALLBACK

    def test_should_skip_cache(self, handler):
        """Test should skip cache determination."""
        assert handler.should_skip_cache(CacheError("test")) is True
        assert handler.should_skip_cache(EmbeddingError("test")) is True
        assert handler.should_skip_cache(LLMProviderError("test")) is False


class TestWithRecovery:
    """Tests for with_recovery convenience function."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful operation."""
        operation = AsyncMock(return_value="success")

        result = await with_recovery(operation)

        assert result.success is True
        assert result.result == "success"

    @pytest.mark.asyncio
    async def test_failure(self):
        """Test failed operation."""
        operation = AsyncMock(side_effect=ValueError("permanent error"))

        result = await with_recovery(operation, max_retries=0)

        assert result.success is False
        assert result.action_taken == RecoveryAction.FAIL

