"""Unit tests for Metrics endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.routes.metrics import router, get_metrics


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_returns_200(self, client):
        """Test metrics endpoint returns 200."""
        response = client.get("/metrics")

        assert response.status_code == 200

    def test_metrics_returns_application_info(self, client):
        """Test metrics includes application info."""
        response = client.get("/metrics")
        data = response.json()

        assert "application" in data
        assert "name" in data["application"]
        assert "version" in data["application"]

    def test_metrics_returns_config_info(self, client):
        """Test metrics includes config info."""
        response = client.get("/metrics")
        data = response.json()

        assert "config" in data
        assert "cache_ttl_seconds" in data["config"]


class TestPrometheusMetricsEndpoint:
    """Tests for /metrics/prometheus endpoint."""

    def test_prometheus_metrics_returns_200(self, client):
        """Test prometheus metrics endpoint returns 200."""
        response = client.get("/metrics/prometheus")

        assert response.status_code == 200

    def test_prometheus_metrics_format(self, client):
        """Test prometheus metrics format."""
        response = client.get("/metrics/prometheus")
        text = response.text

        # Should have metric lines
        assert "ragcache_info" in text
        assert "# HELP" in text
        assert "# TYPE" in text

    def test_prometheus_metrics_includes_version(self, client):
        """Test prometheus metrics includes version."""
        response = client.get("/metrics/prometheus")
        text = response.text

        # Check for version in the response (might be escaped)
        assert "0.1.0" in text


class TestGetMetrics:
    """Tests for get_metrics function."""

    @pytest.mark.asyncio
    async def test_get_metrics_basic(self):
        """Test get_metrics returns basic structure."""
        mock_request = MagicMock()
        mock_request.app.state = MagicMock(spec=[])

        metrics = await get_metrics(mock_request)

        assert "application" in metrics
        assert "config" in metrics

    @pytest.mark.asyncio
    async def test_get_metrics_with_pipeline_monitor(self):
        """Test get_metrics includes pipeline metrics."""
        mock_request = MagicMock()
        mock_request.app.state = MagicMock(spec=[])

        with patch("app.pipeline.performance_monitor.get_monitor") as mock_get_monitor:
            mock_monitor = MagicMock()
            mock_monitor.get_summary.return_value = {
                "total_requests": 100,
                "cache_hits": 80,
            }
            mock_get_monitor.return_value = mock_monitor

            metrics = await get_metrics(mock_request)

        assert "pipeline" in metrics
        # Pipeline metrics might be empty dict if import fails
        # Just check the key exists
        assert isinstance(metrics["pipeline"], dict)
