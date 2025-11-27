"""Unit tests for Query Deduplication."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.models.response import QueryResponse, CacheInfo, UsageMetrics
from app.pipeline.deduplication import (
    DeduplicationStats,
    DeduplicatingProcessor,
    PendingQuery,
    QueryDeduplicator,
)


class TestDeduplicationStats:
    """Tests for DeduplicationStats."""

    def test_dedup_rate_empty(self):
        """Test dedup rate with no queries."""
        stats = DeduplicationStats()
        assert stats.dedup_rate == 0.0

    def test_dedup_rate(self):
        """Test dedup rate calculation."""
        stats = DeduplicationStats(
            total_queries=10,
            deduplicated=3,
            unique=7,
        )
        assert stats.dedup_rate == 0.3


class TestQueryDeduplicator:
    """Tests for QueryDeduplicator."""

    @pytest.fixture
    def dedup(self):
        """Create deduplicator."""
        return QueryDeduplicator(window_seconds=5.0, max_pending=100)

    @pytest.mark.asyncio
    async def test_first_query_not_duplicate(self, dedup):
        """Test first query is not duplicate."""
        is_dup, future = await dedup.get_or_create("test query")

        assert is_dup is False
        assert future is not None
        assert dedup.pending_count == 1

    @pytest.mark.asyncio
    async def test_same_query_is_duplicate(self, dedup):
        """Test same query is marked as duplicate."""
        is_dup1, future1 = await dedup.get_or_create("test query")
        is_dup2, future2 = await dedup.get_or_create("test query")

        assert is_dup1 is False
        assert is_dup2 is True
        assert future1 is future2

    @pytest.mark.asyncio
    async def test_different_queries_not_duplicates(self, dedup):
        """Test different queries are not duplicates."""
        is_dup1, _ = await dedup.get_or_create("query one")
        is_dup2, _ = await dedup.get_or_create("query two")

        assert is_dup1 is False
        assert is_dup2 is False
        assert dedup.pending_count == 2

    @pytest.mark.asyncio
    async def test_complete_removes_pending(self, dedup):
        """Test completing removes from pending."""
        await dedup.get_or_create("test query")
        assert dedup.pending_count == 1

        await dedup.complete("test query", result=MagicMock())
        assert dedup.pending_count == 0

    @pytest.mark.asyncio
    async def test_complete_sets_result(self, dedup):
        """Test completing sets future result."""
        _, future = await dedup.get_or_create("test query")

        result = MagicMock()
        await dedup.complete("test query", result=result)

        assert future.result() is result

    @pytest.mark.asyncio
    async def test_complete_sets_error(self, dedup):
        """Test completing sets future error."""
        _, future = await dedup.get_or_create("test query")

        error = ValueError("test error")
        await dedup.complete("test query", error=error)

        with pytest.raises(ValueError):
            future.result()

    @pytest.mark.asyncio
    async def test_stats_tracking(self, dedup):
        """Test statistics are tracked."""
        await dedup.get_or_create("query1")
        await dedup.get_or_create("query1")  # duplicate
        await dedup.get_or_create("query2")

        assert dedup.stats.total_queries == 3
        assert dedup.stats.deduplicated == 1
        assert dedup.stats.unique == 2

    def test_reset_stats(self, dedup):
        """Test resetting statistics."""
        dedup._stats.total_queries = 100
        dedup.reset_stats()
        assert dedup.stats.total_queries == 0

    @pytest.mark.asyncio
    async def test_max_pending_enforced(self):
        """Test max pending limit is enforced."""
        dedup = QueryDeduplicator(max_pending=3)

        await dedup.get_or_create("q1")
        await dedup.get_or_create("q2")
        await dedup.get_or_create("q3")
        await dedup.get_or_create("q4")

        assert dedup.pending_count <= 3


class TestDeduplicatingProcessor:
    """Tests for DeduplicatingProcessor."""

    @pytest.fixture
    def mock_query_service(self):
        """Create mock query service."""
        mock = MagicMock()
        mock.process = AsyncMock(
            return_value=QueryResponse(
                response="response",
                provider="openai",
                model="gpt-4",
                usage=UsageMetrics.create(10, 20),
                cache_info=CacheInfo.miss(),
                latency_ms=100,
            )
        )
        return mock

    @pytest.fixture
    def processor(self, mock_query_service):
        """Create processor."""
        return DeduplicatingProcessor(
            query_service=mock_query_service,
            window_seconds=5.0,
        )

    @pytest.mark.asyncio
    async def test_process_single_query(self, processor, mock_query_service):
        """Test processing single query."""
        request = MagicMock()
        request.query = "test query"

        response = await processor.process(request)

        assert response.response == "response"
        mock_query_service.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_deduplicated_queries_same_result(
        self, processor, mock_query_service
    ):
        """Test duplicate queries get same result."""
        request = MagicMock()
        request.query = "duplicate query"

        # Make the mock take some time to process
        async def slow_process(*args):
            await asyncio.sleep(0.1)
            return QueryResponse(
                response="response",
                provider="openai",
                model="gpt-4",
                usage=UsageMetrics.create(10, 20),
                cache_info=CacheInfo.miss(),
                latency_ms=100,
            )

        mock_query_service.process = slow_process

        # Start both tasks nearly simultaneously
        task1 = asyncio.create_task(processor.process(request))
        await asyncio.sleep(0.01)  # Small delay to ensure first is registered
        task2 = asyncio.create_task(processor.process(request))

        result1, result2 = await asyncio.gather(task1, task2)

        # Both should get same result
        assert result1.response == result2.response

    def test_stats_property(self, processor):
        """Test stats property."""
        stats = processor.stats
        assert stats is not None
        assert hasattr(stats, "total_queries")

