"""Tests for batch processor."""

import pytest

from app.optimization.batch_processor import (
    BatchProcessor,
    BatchConfig,
    BatchResult,
    AdaptiveBatchProcessor,
)


class TestBatchResult:
    """Test cases for BatchResult."""

    def test_success_rate_all_success(self):
        """Test success rate with all successful."""
        result = BatchResult(
            results=[1, 2, 3],
            errors=[],
            total_items=3,
            successful_items=3,
            failed_items=0,
            processing_time_ms=100,
        )
        assert result.success_rate == 1.0

    def test_success_rate_partial_failure(self):
        """Test success rate with partial failure."""
        result = BatchResult(
            results=[1, 2],
            errors=[(2, Exception("error"))],
            total_items=3,
            successful_items=2,
            failed_items=1,
            processing_time_ms=100,
        )
        assert result.success_rate == pytest.approx(0.666, rel=0.01)

    def test_success_rate_empty(self):
        """Test success rate with no items."""
        result = BatchResult(
            results=[],
            errors=[],
            total_items=0,
            successful_items=0,
            failed_items=0,
            processing_time_ms=0,
        )
        assert result.success_rate == 0.0


class TestBatchProcessor:
    """Test cases for BatchProcessor."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BatchConfig(
            batch_size=5,
            max_wait_ms=10,
        )

    @pytest.fixture
    def process_fn(self):
        """Create processing function."""

        def fn(items):
            return [item * 2 for item in items]

        return fn

    @pytest.fixture
    def processor(self, process_fn, config):
        """Create processor instance."""
        return BatchProcessor(process_fn, config)

    @pytest.mark.asyncio
    async def test_process_many_success(self, processor):
        """Test processing many items."""
        items = [1, 2, 3, 4, 5]

        result = await processor.process_many(items)

        assert result.results == [2, 4, 6, 8, 10]
        assert result.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_process_many_empty(self, processor):
        """Test processing empty list."""
        result = await processor.process_many([])

        assert result.results == []
        assert result.total_items == 0

    @pytest.mark.asyncio
    async def test_process_many_batched(self, processor):
        """Test items are batched correctly."""
        items = list(range(12))

        result = await processor.process_many(items)

        # Should process in batches of 5
        assert len(result.results) == 12

    def test_get_stats(self, processor):
        """Test getting processor stats."""
        stats = processor.get_stats()

        assert "total_items" in stats
        assert "batches_processed" in stats
        assert "pending_items" in stats


class TestAdaptiveBatchProcessor:
    """Test cases for AdaptiveBatchProcessor."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BatchConfig(
            batch_size=10,
            min_batch_size=1,
            max_batch_size=100,
        )

    @pytest.fixture
    def processor(self, config):
        """Create adaptive processor."""

        def fn(items):
            return [item * 2 for item in items]

        return AdaptiveBatchProcessor(fn, config, target_latency_ms=50)

    def test_initial_batch_size(self, processor):
        """Test initial batch size."""
        assert processor.current_batch_size == 10

    @pytest.mark.asyncio
    async def test_batch_size_adapts(self, processor):
        """Test batch size adaptation."""
        # Process items to trigger adaptation
        for _ in range(10):
            await processor.process_many(list(range(10)))

        # Stats should be updated
        stats = processor.get_stats()
        assert stats["batches_processed"] >= 10
