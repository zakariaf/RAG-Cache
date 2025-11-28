"""Tests for query optimizer."""

import asyncio
import pytest
from unittest.mock import AsyncMock

from app.optimization.query_optimizer import (
    QueryOptimizer,
    OptimizationConfig,
    QueryTimer,
)


class TestQueryOptimizer:
    """Test cases for QueryOptimizer."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return OptimizationConfig(
            enable_parallel_cache_check=True,
            parallel_timeout_seconds=1.0,
            target_total_latency_ms=100,
        )

    @pytest.fixture
    def optimizer(self, config):
        """Create optimizer instance."""
        return QueryOptimizer(config)

    @pytest.mark.asyncio
    async def test_parallel_cache_lookup_exact_hit(self, optimizer):
        """Test parallel lookup returns exact hit."""
        exact_lookup = AsyncMock(return_value="exact_result")
        semantic_lookup = AsyncMock(return_value="semantic_result")

        result, cache_type = await optimizer.optimize_cache_lookup(
            exact_lookup, semantic_lookup
        )

        assert result == "exact_result"
        assert cache_type == "exact"

    @pytest.mark.asyncio
    async def test_parallel_cache_lookup_semantic_hit(self, optimizer):
        """Test parallel lookup falls back to semantic."""
        exact_lookup = AsyncMock(return_value=None)
        semantic_lookup = AsyncMock(return_value="semantic_result")

        result, cache_type = await optimizer.optimize_cache_lookup(
            exact_lookup, semantic_lookup
        )

        assert result == "semantic_result"
        assert cache_type == "semantic"

    @pytest.mark.asyncio
    async def test_parallel_cache_lookup_miss(self, optimizer):
        """Test parallel lookup returns miss."""
        exact_lookup = AsyncMock(return_value=None)
        semantic_lookup = AsyncMock(return_value=None)

        result, cache_type = await optimizer.optimize_cache_lookup(
            exact_lookup, semantic_lookup
        )

        assert result is None
        assert cache_type == "miss"

    def test_should_skip_semantic_with_exact_hit(self, optimizer):
        """Test skip semantic when exact hit with high confidence."""
        result = optimizer.should_skip_semantic_search("result", confidence=1.0)
        assert result is True

    def test_should_not_skip_semantic_without_result(self, optimizer):
        """Test don't skip semantic without result."""
        result = optimizer.should_skip_semantic_search(None, confidence=1.0)
        assert result is False

    def test_record_timing(self, optimizer):
        """Test timing recording."""
        optimizer.record_timing(50.0)
        optimizer.record_timing(100.0)
        optimizer.record_timing(150.0)

        assert optimizer.get_average_latency() == 100.0

    def test_percentile_latency(self, optimizer):
        """Test percentile calculation."""
        for i in range(1, 101):
            optimizer.record_timing(float(i))

        p50 = optimizer.get_percentile_latency(50)
        p95 = optimizer.get_percentile_latency(95)

        assert p50 == 50.0
        assert p95 == 95.0

    def test_is_meeting_targets(self, optimizer):
        """Test target checking."""
        for _ in range(10):
            optimizer.record_timing(50.0)  # Under target

        targets = optimizer.is_meeting_targets()
        assert targets["avg_under_target"] is True
        assert targets["p95_under_target"] is True

    def test_optimization_suggestions_when_slow(self, optimizer):
        """Test suggestions when performance is slow."""
        for _ in range(10):
            optimizer.record_timing(200.0)  # Over target

        suggestions = optimizer.get_optimization_suggestions()
        assert len(suggestions) > 0


class TestQueryTimer:
    """Test cases for QueryTimer."""

    @pytest.mark.asyncio
    async def test_timer_measures_elapsed(self):
        """Test timer measures elapsed time."""
        async with QueryTimer() as timer:
            await asyncio.sleep(0.01)

        assert timer.elapsed_ms >= 10

    @pytest.mark.asyncio
    async def test_timer_records_to_optimizer(self):
        """Test timer records to optimizer."""
        optimizer = QueryOptimizer()

        async with QueryTimer(optimizer):
            await asyncio.sleep(0.01)

        assert len(optimizer._timing_history) == 1
