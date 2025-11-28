"""Unit tests for Async Query Processor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.query import QueryRequest
from app.pipeline.async_processor import (
    AsyncQueryProcessor,
    AsyncResult,
    run_async,
    run_with_fallback,
)


class TestAsyncResult:
    """Tests for AsyncResult."""

    def test_ok_result(self):
        """Test creating success result."""
        result = AsyncResult.ok("data", duration_ms=100)
        assert result.success is True
        assert result.result == "data"
        assert result.duration_ms == 100

    def test_fail_result(self):
        """Test creating failure result."""
        error = ValueError("error")
        result = AsyncResult.fail(error, duration_ms=50)
        assert result.success is False
        assert result.error is error
        assert result.duration_ms == 50


class TestAsyncQueryProcessor:
    """Tests for AsyncQueryProcessor."""

    @pytest.fixture
    def mock_query_service(self):
        """Create mock query service."""
        mock = MagicMock()
        mock.process = AsyncMock(return_value=MagicMock(response="test response"))
        return mock

    @pytest.fixture
    def processor(self, mock_query_service):
        """Create processor with mock service."""
        return AsyncQueryProcessor(
            query_service=mock_query_service,
            max_concurrent=5,
            timeout_seconds=10.0,
        )

    @pytest.mark.asyncio
    async def test_process_single_success(self, processor, mock_query_service):
        """Test processing single query successfully."""
        request = QueryRequest(query="test query")

        result = await processor.process_single(request)

        assert result.success is True
        assert result.result.response == "test response"
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_process_single_timeout(self, processor, mock_query_service):
        """Test processing with timeout."""

        async def slow_process(*args):
            await asyncio.sleep(20)
            return MagicMock()

        mock_query_service.process = slow_process
        processor._timeout = 0.1  # Very short timeout

        request = QueryRequest(query="test")
        result = await processor.process_single(request)

        assert result.success is False
        assert isinstance(result.error, TimeoutError)

    @pytest.mark.asyncio
    async def test_process_single_error(self, processor, mock_query_service):
        """Test processing with error."""
        mock_query_service.process = AsyncMock(side_effect=ValueError("test error"))

        request = QueryRequest(query="test")
        result = await processor.process_single(request)

        assert result.success is False
        assert isinstance(result.error, ValueError)

    @pytest.mark.asyncio
    async def test_process_batch(self, processor):
        """Test batch processing."""
        requests = [QueryRequest(query=f"query {i}") for i in range(3)]

        results = await processor.process_batch(requests)

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_process_batch_empty(self, processor):
        """Test batch processing with empty list."""
        results = await processor.process_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_process_stream(self, processor):
        """Test streaming results."""
        requests = [QueryRequest(query=f"q{i}") for i in range(2)]
        collected = []

        def callback(i, result):
            collected.append((i, result))

        results = await processor.process_stream(requests, callback)

        assert len(results) == 2
        assert len(collected) == 2
        assert collected[0][0] == 0
        assert collected[1][0] == 1


class TestRunAsync:
    """Tests for run_async function."""

    @pytest.mark.asyncio
    async def test_run_async_success(self):
        """Test successful async execution."""

        async def func():
            return "result"

        result = await run_async(func)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_run_async_timeout(self):
        """Test async execution with timeout."""

        async def slow_func():
            await asyncio.sleep(10)
            return "result"

        with pytest.raises(asyncio.TimeoutError):
            await run_async(slow_func, timeout=0.1)


class TestRunWithFallback:
    """Tests for run_with_fallback function."""

    @pytest.mark.asyncio
    async def test_primary_succeeds(self):
        """Test when primary succeeds."""

        async def primary():
            return "primary result"

        async def fallback():
            return "fallback result"

        result = await run_with_fallback(primary, fallback)
        assert result == "primary result"

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        """Test fallback when primary fails."""

        async def primary():
            raise ValueError("primary failed")

        async def fallback():
            return "fallback result"

        result = await run_with_fallback(primary, fallback)
        assert result == "fallback result"

    @pytest.mark.asyncio
    async def test_fallback_on_timeout(self):
        """Test fallback when primary times out."""

        async def primary():
            await asyncio.sleep(10)
            return "primary result"

        async def fallback():
            return "fallback result"

        result = await run_with_fallback(primary, fallback, timeout=0.1)
        assert result == "fallback result"
