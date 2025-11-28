"""Tests for Prometheus metrics."""

import pytest
import time

from app.monitoring.prometheus import (
    PrometheusMetrics,
    MetricsMiddleware,
    get_metrics,
    HistogramValue,
)


class TestPrometheusMetrics:
    """Test Prometheus metrics functionality."""

    @pytest.fixture
    def metrics(self):
        """Create fresh metrics instance."""
        return PrometheusMetrics()

    def test_init_creates_core_metrics(self, metrics):
        """Test initialization creates core metrics."""
        assert "ragcache_requests_total" in metrics._counters
        assert "ragcache_cache_hit_rate" in metrics._gauges
        assert "ragcache_request_duration_seconds" in metrics._histograms

    def test_inc_counter_without_labels(self, metrics):
        """Test incrementing counter without labels."""
        metrics.inc_counter("test_counter")
        metrics.inc_counter("test_counter", value=2.0)

        assert metrics._counters["test_counter"]["test_counter"] == 3.0

    def test_inc_counter_with_labels(self, metrics):
        """Test incrementing counter with labels."""
        metrics.inc_counter("test_counter", labels={"method": "GET"})
        metrics.inc_counter("test_counter", labels={"method": "POST"})

        assert 'test_counter{method="GET"}' in metrics._counters["test_counter"]
        assert 'test_counter{method="POST"}' in metrics._counters["test_counter"]

    def test_set_gauge(self, metrics):
        """Test setting gauge value."""
        metrics.set_gauge("test_gauge", 42.0)

        assert metrics._gauges["test_gauge"]["test_gauge"] == 42.0

    def test_set_gauge_with_labels(self, metrics):
        """Test setting gauge with labels."""
        metrics.set_gauge("test_gauge", 10.0, labels={"type": "exact"})

        assert 'test_gauge{type="exact"}' in metrics._gauges["test_gauge"]

    def test_inc_gauge(self, metrics):
        """Test incrementing gauge."""
        metrics.set_gauge("test_gauge", 10.0)
        metrics.inc_gauge("test_gauge", 5.0)

        assert metrics._gauges["test_gauge"]["test_gauge"] == 15.0

    def test_dec_gauge(self, metrics):
        """Test decrementing gauge."""
        metrics.set_gauge("test_gauge", 10.0)
        metrics.dec_gauge("test_gauge", 3.0)

        assert metrics._gauges["test_gauge"]["test_gauge"] == 7.0

    def test_observe_histogram(self, metrics):
        """Test observing histogram value."""
        metrics.observe_histogram("test_histogram", 0.5)
        metrics.observe_histogram("test_histogram", 0.1)

        hist = metrics._histograms["test_histogram"]["test_histogram"]
        assert hist.count == 2
        assert hist.sum_value == 0.6

    def test_observe_histogram_buckets(self, metrics):
        """Test histogram bucket counting."""
        metrics.observe_histogram("test_histogram", 0.01)  # fits in 0.01 bucket
        metrics.observe_histogram("test_histogram", 0.5)  # fits in 0.5 bucket

        hist = metrics._histograms["test_histogram"]["test_histogram"]
        assert hist.buckets[0.01] == 1
        assert hist.buckets[0.5] == 2  # 0.01 also fits in 0.5

    def test_track_request(self, metrics):
        """Test tracking HTTP request."""
        metrics.track_request("GET", "/api/v1/query", 200, 0.1)

        assert "ragcache_requests_total" in metrics._counters
        assert "ragcache_request_duration_seconds" in metrics._histograms

    def test_track_request_error(self, metrics):
        """Test tracking error request."""
        metrics.track_request("POST", "/api/v1/query", 500, 0.5)

        errors = metrics._counters.get("ragcache_requests_errors_total", {})
        assert len([k for k in errors if not k.startswith("_")]) > 0

    def test_track_cache_hit(self, metrics):
        """Test tracking cache hit."""
        metrics.track_cache_hit("exact")
        metrics.track_cache_hit("semantic")

        hits = metrics._counters.get("ragcache_cache_hits_total", {})
        assert 'ragcache_cache_hits_total{type="exact"}' in hits
        assert 'ragcache_cache_hits_total{type="semantic"}' in hits

    def test_track_cache_miss(self, metrics):
        """Test tracking cache miss."""
        metrics.track_cache_miss()

        misses = metrics._counters.get("ragcache_cache_misses_total", {})
        assert len([k for k in misses if not k.startswith("_")]) > 0

    def test_track_llm_call(self, metrics):
        """Test tracking LLM call."""
        metrics.track_llm_call(
            provider="openai",
            model="gpt-3.5-turbo",
            tokens=100,
            cost=0.001,
            latency_seconds=0.5,
        )

        assert "ragcache_llm_requests_total" in metrics._counters
        assert "ragcache_llm_tokens_total" in metrics._counters
        assert "ragcache_llm_latency_seconds" in metrics._histograms

    def test_get_uptime_seconds(self, metrics):
        """Test getting uptime."""
        time.sleep(0.1)
        uptime = metrics.get_uptime_seconds()

        assert uptime >= 0.1
        assert uptime < 1.0

    def test_export_prometheus_format(self, metrics):
        """Test exporting to Prometheus format."""
        metrics.inc_counter("test_counter")
        metrics.set_gauge("test_gauge", 42.0)

        output = metrics.export_prometheus()

        assert "# HELP" in output
        assert "# TYPE" in output
        assert "test_counter" in output
        assert "test_gauge 42.0" in output

    def test_get_summary(self, metrics):
        """Test getting metrics summary."""
        metrics.inc_counter("test_counter")

        summary = metrics.get_summary()

        assert "uptime_seconds" in summary
        assert "counters" in summary
        assert "gauges" in summary


class TestGlobalMetrics:
    """Test global metrics singleton."""

    def test_get_metrics_returns_same_instance(self):
        """Test get_metrics returns singleton."""
        m1 = get_metrics()
        m2 = get_metrics()

        assert m1 is m2

    def test_get_metrics_returns_prometheus_metrics(self):
        """Test get_metrics returns PrometheusMetrics."""
        m = get_metrics()

        assert isinstance(m, PrometheusMetrics)


class TestMetricsMiddleware:
    """Test metrics middleware."""

    @pytest.fixture
    def mock_app(self):
        """Create mock app."""
        from unittest.mock import MagicMock, AsyncMock
        from starlette.requests import Request
        from starlette.responses import Response

        async def app(scope, receive, send):
            response = Response("OK", status_code=200)
            await response(scope, receive, send)

        return app

    def test_normalize_path_numeric_id(self):
        """Test path normalization with numeric ID."""
        middleware = MetricsMiddleware(lambda: None)

        result = middleware._normalize_path("/api/v1/users/123")

        assert result == "/api/v1/users/:id"

    def test_normalize_path_uuid(self):
        """Test path normalization with UUID."""
        middleware = MetricsMiddleware(lambda: None)

        result = middleware._normalize_path(
            "/api/v1/items/550e8400-e29b-41d4-a716-446655440000"
        )

        assert result == "/api/v1/items/:id"

    def test_normalize_path_no_id(self):
        """Test path normalization without ID."""
        middleware = MetricsMiddleware(lambda: None)

        result = middleware._normalize_path("/api/v1/health")

        assert result == "/api/v1/health"
