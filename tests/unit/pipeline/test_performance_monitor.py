"""Unit tests for Performance Monitor."""

import pytest
import asyncio

from app.pipeline.performance_monitor import (
    OperationMetrics,
    PipelineMetrics,
    PerformanceMonitor,
    get_monitor,
    track_operation,
)


class TestOperationMetrics:
    """Tests for OperationMetrics."""

    def test_duration_in_progress(self):
        """Test duration calculation while in progress."""
        import time
        op = OperationMetrics(name="test", start_time=time.time() - 0.1)
        assert op.duration_ms >= 100

    def test_duration_completed(self):
        """Test duration calculation when completed."""
        import time
        start = time.time()
        op = OperationMetrics(name="test", start_time=start, end_time=start + 0.5)
        assert abs(op.duration_ms - 500) < 1

    def test_complete(self):
        """Test completing an operation."""
        import time
        op = OperationMetrics(name="test", start_time=time.time())
        op.complete(success=False, error="test error")

        assert op.success is False
        assert op.error == "test error"
        assert op.end_time is not None


class TestPipelineMetrics:
    """Tests for PipelineMetrics."""

    def test_avg_latency_empty(self):
        """Test average latency with no requests."""
        metrics = PipelineMetrics()
        assert metrics.avg_latency_ms == 0.0

    def test_avg_latency(self):
        """Test average latency calculation."""
        metrics = PipelineMetrics(total_requests=2, total_latency_ms=200)
        assert metrics.avg_latency_ms == 100.0

    def test_cache_hit_rate_empty(self):
        """Test cache hit rate with no requests."""
        metrics = PipelineMetrics()
        assert metrics.cache_hit_rate == 0.0

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        metrics = PipelineMetrics(cache_hits=3, cache_misses=7)
        assert metrics.cache_hit_rate == 0.3

    def test_success_rate(self):
        """Test success rate calculation."""
        metrics = PipelineMetrics(
            total_requests=10,
            successful_requests=8,
            failed_requests=2,
        )
        assert metrics.success_rate == 0.8

    def test_record_latency(self):
        """Test recording latency."""
        metrics = PipelineMetrics()
        metrics.record_latency(100)
        metrics.record_latency(200)

        assert metrics.total_latency_ms == 300
        assert metrics.min_latency_ms == 100
        assert metrics.max_latency_ms == 200

    def test_record_operation(self):
        """Test recording operation timing."""
        metrics = PipelineMetrics()
        metrics.record_operation("cache_check", 10)
        metrics.record_operation("cache_check", 20)

        assert metrics.get_operation_avg("cache_check") == 15.0

    def test_to_dict(self):
        """Test dictionary conversion."""
        metrics = PipelineMetrics(
            total_requests=10,
            successful_requests=8,
            cache_hits=3,
        )

        d = metrics.to_dict()

        assert d["total_requests"] == 10
        assert d["successful_requests"] == 8
        assert d["cache_hits"] == 3


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor."""

    @pytest.fixture
    def monitor(self):
        """Create fresh monitor."""
        m = PerformanceMonitor()
        m.reset()
        return m

    @pytest.mark.asyncio
    async def test_record_request_start(self, monitor):
        """Test recording request start."""
        request_id = await monitor.record_request_start()

        assert request_id is not None
        assert len(request_id) > 0
        assert monitor.metrics.total_requests == 1

    @pytest.mark.asyncio
    async def test_record_request_end_success(self, monitor):
        """Test recording successful request end."""
        req_id = await monitor.record_request_start()
        await monitor.record_request_end(
            req_id,
            success=True,
            latency_ms=100,
            cache_hit=True,
        )

        assert monitor.metrics.successful_requests == 1
        assert monitor.metrics.cache_hits == 1

    @pytest.mark.asyncio
    async def test_record_request_end_failure(self, monitor):
        """Test recording failed request end."""
        req_id = await monitor.record_request_start()
        await monitor.record_request_end(
            req_id,
            success=False,
            latency_ms=50,
        )

        assert monitor.metrics.failed_requests == 1

    @pytest.mark.asyncio
    async def test_start_end_operation(self, monitor):
        """Test tracking operation timing."""
        op = await monitor.start_operation("test_op")
        await asyncio.sleep(0.01)
        await monitor.end_operation(op, success=True)

        assert op.duration_ms >= 10
        assert "test_op" in monitor.metrics.operation_timings

    def test_reset(self, monitor):
        """Test resetting metrics."""
        monitor._metrics.total_requests = 100
        monitor.reset()
        assert monitor.metrics.total_requests == 0

    def test_get_summary(self, monitor):
        """Test getting metrics summary."""
        summary = monitor.get_summary()
        assert "total_requests" in summary
        assert "success_rate" in summary


class TestGetMonitor:
    """Tests for get_monitor function."""

    def test_returns_singleton(self):
        """Test monitor is singleton."""
        m1 = get_monitor()
        m2 = get_monitor()
        assert m1 is m2


class TestTrackOperation:
    """Tests for track_operation decorator."""

    @pytest.mark.asyncio
    async def test_decorator_tracks_success(self):
        """Test decorator tracks successful operation."""
        monitor = get_monitor()
        monitor.reset()

        @track_operation("test_decorated")
        async def test_func():
            return "result"

        result = await test_func()

        assert result == "result"
        assert "test_decorated" in monitor.metrics.operation_timings

    @pytest.mark.asyncio
    async def test_decorator_tracks_failure(self):
        """Test decorator tracks failed operation."""
        monitor = get_monitor()
        monitor.reset()

        @track_operation("failing_op")
        async def failing_func():
            raise ValueError("error")

        with pytest.raises(ValueError):
            await failing_func()

        assert "failing_op" in monitor.metrics.operation_timings

