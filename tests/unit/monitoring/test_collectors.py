"""Tests for metrics collectors."""

import pytest

from app.monitoring.collectors import (
    RequestMetrics,
    CacheMetrics,
    LLMMetrics,
    SystemMetrics,
)


class TestRequestMetrics:
    """Test request metrics collector."""

    @pytest.fixture
    def metrics(self):
        """Create request metrics."""
        return RequestMetrics()

    def test_record_request(self, metrics):
        """Test recording a request."""
        metrics.record_request("GET", "/api/v1/query", 200, 50.0)

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0

    def test_record_error_request(self, metrics):
        """Test recording error request."""
        metrics.record_request("POST", "/api/v1/query", 500, 100.0)

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 1

    def test_avg_latency(self, metrics):
        """Test average latency calculation."""
        metrics.record_request("GET", "/", 200, 100.0)
        metrics.record_request("GET", "/", 200, 200.0)

        assert metrics.avg_latency_ms == 150.0

    def test_success_rate(self, metrics):
        """Test success rate calculation."""
        metrics.record_request("GET", "/", 200, 50.0)
        metrics.record_request("GET", "/", 200, 50.0)
        metrics.record_request("GET", "/", 500, 50.0)

        assert metrics.success_rate == pytest.approx(0.666, rel=0.01)

    def test_error_rate(self, metrics):
        """Test error rate calculation."""
        metrics.record_request("GET", "/", 200, 50.0)
        metrics.record_request("GET", "/", 500, 50.0)

        assert metrics.error_rate == 0.5

    def test_percentile(self, metrics):
        """Test latency percentile."""
        for i in range(100):
            metrics.record_request("GET", "/", 200, float(i))

        p50 = metrics.get_percentile(50)
        assert p50 == pytest.approx(50.0, abs=1)

    def test_to_dict(self, metrics):
        """Test conversion to dict."""
        metrics.record_request("GET", "/", 200, 50.0)

        result = metrics.to_dict()

        assert "total_requests" in result
        assert "avg_latency_ms" in result
        assert "p50_latency_ms" in result
        assert "success_rate" in result


class TestCacheMetrics:
    """Test cache metrics collector."""

    @pytest.fixture
    def metrics(self):
        """Create cache metrics."""
        return CacheMetrics()

    def test_record_hit(self, metrics):
        """Test recording cache hit."""
        metrics.record_hit("exact", 5.0)
        metrics.record_hit("semantic", 10.0)

        assert metrics.exact_hits == 1
        assert metrics.semantic_hits == 1
        assert metrics.total_hits == 2

    def test_record_miss(self, metrics):
        """Test recording cache miss."""
        metrics.record_miss(100.0)

        assert metrics.misses == 1

    def test_hit_rate(self, metrics):
        """Test hit rate calculation."""
        metrics.record_hit("exact", 5.0)
        metrics.record_hit("exact", 5.0)
        metrics.record_miss(100.0)

        assert metrics.hit_rate == pytest.approx(0.666, rel=0.01)

    def test_exact_hit_rate(self, metrics):
        """Test exact hit rate."""
        metrics.record_hit("exact", 5.0)
        metrics.record_hit("semantic", 10.0)

        assert metrics.exact_hit_rate == 0.5

    def test_semantic_hit_rate(self, metrics):
        """Test semantic hit rate."""
        metrics.record_hit("exact", 5.0)
        metrics.record_hit("semantic", 10.0)
        metrics.record_hit("semantic", 10.0)

        assert metrics.semantic_hit_rate == pytest.approx(0.666, rel=0.01)

    def test_avg_latencies(self, metrics):
        """Test average latency calculations."""
        metrics.record_hit("exact", 10.0)
        metrics.record_hit("exact", 20.0)
        metrics.record_miss(100.0)
        metrics.record_miss(200.0)

        assert metrics.avg_hit_latency_ms == 15.0
        assert metrics.avg_miss_latency_ms == 150.0

    def test_to_dict(self, metrics):
        """Test conversion to dict."""
        metrics.record_hit("exact", 5.0)

        result = metrics.to_dict()

        assert "exact_hits" in result
        assert "hit_rate" in result


class TestLLMMetrics:
    """Test LLM metrics collector."""

    @pytest.fixture
    def metrics(self):
        """Create LLM metrics."""
        return LLMMetrics()

    def test_record_request(self, metrics):
        """Test recording LLM request."""
        metrics.record_request(
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.001,
            latency_ms=500.0,
        )

        assert metrics.total_requests == 1
        assert metrics.total_prompt_tokens == 100
        assert metrics.total_completion_tokens == 50
        assert metrics.total_cost == 0.001

    def test_record_failed_request(self, metrics):
        """Test recording failed request."""
        metrics.record_request(
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=0,
            completion_tokens=0,
            cost=0.0,
            latency_ms=100.0,
            success=False,
            error_type="RateLimitError",
        )

        assert metrics.failed_requests == 1
        assert metrics.errors_by_type["RateLimitError"] == 1

    def test_total_tokens(self, metrics):
        """Test total tokens calculation."""
        metrics.record_request(
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.001,
            latency_ms=500.0,
        )

        assert metrics.total_tokens == 150

    def test_avg_tokens_per_request(self, metrics):
        """Test average tokens per request."""
        metrics.record_request("openai", "gpt-3.5", 100, 50, 0.001, 500.0)
        metrics.record_request("openai", "gpt-3.5", 200, 100, 0.002, 600.0)

        assert metrics.avg_tokens_per_request == 225.0

    def test_provider_tracking(self, metrics):
        """Test provider usage tracking."""
        metrics.record_request("openai", "gpt-3.5", 100, 50, 0.001, 500.0)
        metrics.record_request("anthropic", "claude", 100, 50, 0.001, 500.0)
        metrics.record_request("openai", "gpt-4", 100, 50, 0.002, 500.0)

        assert metrics.providers["openai"] == 2
        assert metrics.providers["anthropic"] == 1

    def test_to_dict(self, metrics):
        """Test conversion to dict."""
        metrics.record_request("openai", "gpt-3.5", 100, 50, 0.001, 500.0)

        result = metrics.to_dict()

        assert "total_requests" in result
        assert "total_cost" in result
        assert "providers" in result


class TestSystemMetrics:
    """Test system metrics collector."""

    @pytest.fixture
    def metrics(self):
        """Create system metrics."""
        return SystemMetrics()

    def test_uptime(self, metrics):
        """Test uptime calculation."""
        import time
        time.sleep(0.1)

        uptime = metrics.uptime_seconds

        assert uptime >= 0.1

    def test_active_requests(self, metrics):
        """Test active request counting."""
        metrics.increment_active_requests()
        metrics.increment_active_requests()

        assert metrics.active_requests == 2
        assert metrics.peak_active_requests == 2

        metrics.decrement_active_requests()

        assert metrics.active_requests == 1
        assert metrics.peak_active_requests == 2

    def test_connection_tracking(self, metrics):
        """Test connection tracking."""
        metrics.set_redis_connections(5)
        metrics.set_qdrant_connections(3)

        assert metrics.redis_connections == 5
        assert metrics.qdrant_connections == 3

    def test_to_dict(self, metrics):
        """Test conversion to dict."""
        result = metrics.to_dict()

        assert "uptime_seconds" in result
        assert "active_requests" in result
        assert "redis_connections" in result

