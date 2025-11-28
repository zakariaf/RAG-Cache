"""Unit tests for Result Aggregator."""

import pytest

from app.models.response import CacheInfo, QueryResponse, UsageMetrics
from app.pipeline.result_aggregator import (
    AggregatedResult,
    AggregationStrategy,
    BatchAggregator,
    BatchResult,
    ResultAggregator,
)


def create_response(
    response: str = "test response",
    latency: float = 100.0,
    cache_hit: bool = False,
) -> QueryResponse:
    """Helper to create test response."""
    return QueryResponse(
        response=response,
        provider="openai",
        model="gpt-4",
        usage=UsageMetrics.create(10, 20),
        cache_info=CacheInfo.exact_hit() if cache_hit else CacheInfo.miss(),
        latency_ms=latency,
    )


class TestAggregatedResult:
    """Tests for AggregatedResult."""

    def test_count(self):
        """Test response count."""
        responses = [create_response() for _ in range(3)]
        result = AggregatedResult(
            responses=responses,
            selected_response=responses[0],
            strategy_used=AggregationStrategy.FIRST,
        )
        assert result.count == 3

    def test_success_with_selection(self):
        """Test success when response selected."""
        response = create_response()
        result = AggregatedResult(
            responses=[response],
            selected_response=response,
            strategy_used=AggregationStrategy.FIRST,
        )
        assert result.success is True

    def test_failure_without_selection(self):
        """Test failure when no response selected."""
        result = AggregatedResult(
            responses=[],
            selected_response=None,
            strategy_used=AggregationStrategy.FIRST,
        )
        assert result.success is False


class TestBatchResult:
    """Tests for BatchResult."""

    def test_success_rate(self):
        """Test success rate calculation."""
        result = BatchResult(
            results=[create_response(), None, create_response()],
            successful=2,
            failed=1,
            total_latency_ms=200,
        )
        assert result.success_rate == pytest.approx(0.6667, rel=0.01)

    def test_avg_latency(self):
        """Test average latency calculation."""
        result = BatchResult(
            results=[create_response(), create_response()],
            successful=2,
            failed=0,
            total_latency_ms=200,
        )
        assert result.avg_latency_ms == 100.0


class TestResultAggregator:
    """Tests for ResultAggregator."""

    def test_aggregate_empty(self):
        """Test aggregating empty list."""
        aggregator = ResultAggregator(strategy=AggregationStrategy.FIRST)
        result = aggregator.aggregate([])

        assert result.success is False
        assert result.selected_response is None

    def test_aggregate_first_strategy(self):
        """Test FIRST aggregation strategy."""
        responses = [
            create_response("first"),
            create_response("second"),
        ]

        aggregator = ResultAggregator(strategy=AggregationStrategy.FIRST)
        result = aggregator.aggregate(responses)

        assert result.selected_response.response == "first"

    def test_aggregate_best_strategy(self):
        """Test BEST aggregation strategy."""
        responses = [
            create_response("slow", latency=1000),
            create_response("fast", latency=50, cache_hit=True),
        ]

        aggregator = ResultAggregator(strategy=AggregationStrategy.BEST)
        result = aggregator.aggregate(responses)

        # Cache hit with low latency should score higher
        assert result.selected_response.response == "fast"

    def test_aggregate_merge_strategy(self):
        """Test MERGE aggregation strategy."""
        responses = [
            create_response("response one"),
            create_response("response two"),
        ]

        aggregator = ResultAggregator(strategy=AggregationStrategy.MERGE)
        result = aggregator.aggregate(responses)

        assert "response one" in result.selected_response.response
        assert "response two" in result.selected_response.response

    def test_aggregate_vote_strategy(self):
        """Test VOTE aggregation strategy."""
        responses = [
            create_response("common"),
            create_response("common"),
            create_response("different"),
        ]

        aggregator = ResultAggregator(strategy=AggregationStrategy.VOTE)
        result = aggregator.aggregate(responses)

        assert result.selected_response.response == "common"

    def test_custom_quality_scorer(self):
        """Test custom quality scorer."""

        def custom_scorer(r):
            return len(r.response)  # Prefer longer responses

        responses = [
            create_response("short"),
            create_response("much longer response"),
        ]

        aggregator = ResultAggregator(
            strategy=AggregationStrategy.BEST,
            quality_scorer=custom_scorer,
        )
        result = aggregator.aggregate(responses)

        assert result.selected_response.response == "much longer response"

    def test_metadata_included(self):
        """Test metadata is included in result."""
        responses = [create_response(), create_response()]

        aggregator = ResultAggregator(strategy=AggregationStrategy.FIRST)
        result = aggregator.aggregate(responses)

        assert "count" in result.metadata
        assert result.metadata["count"] == 2


class TestBatchAggregator:
    """Tests for BatchAggregator."""

    def test_aggregate_batch(self):
        """Test batch aggregation."""
        aggregator = BatchAggregator()
        results = [
            create_response(),
            None,  # Failed
            create_response(),
        ]

        batch_result = aggregator.aggregate_batch(results)

        assert batch_result.successful == 2
        assert batch_result.failed == 1

    def test_summarize(self):
        """Test batch summary."""
        aggregator = BatchAggregator()
        batch_result = BatchResult(
            results=[create_response(cache_hit=True), create_response()],
            successful=2,
            failed=0,
            total_latency_ms=200,
        )

        summary = aggregator.summarize(batch_result)

        assert summary["total"] == 2
        assert summary["successful"] == 2
        assert summary["cache_hits"] == 1
        assert summary["avg_latency_ms"] == 100.0
