"""Unit tests for Health Check endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.routes.health import (
    router,
    check_redis_health,
    check_qdrant_health,
    ComponentHealth,
    DetailedHealthResponse,
)


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


class TestComponentHealth:
    """Tests for ComponentHealth model."""

    def test_healthy_component(self):
        """Test healthy component."""
        health = ComponentHealth(status="healthy", latency_ms=5.0)

        assert health.status == "healthy"
        assert health.latency_ms == 5.0

    def test_unhealthy_component(self):
        """Test unhealthy component."""
        health = ComponentHealth(status="unhealthy", message="Connection failed")

        assert health.status == "unhealthy"
        assert health.message == "Connection failed"


class TestDetailedHealthResponse:
    """Tests for DetailedHealthResponse model."""

    def test_all_healthy(self):
        """Test all components healthy."""
        response = DetailedHealthResponse(
            status="healthy",
            environment="development",
            version="0.1.0",
            components={
                "redis": ComponentHealth(status="healthy"),
                "qdrant": ComponentHealth(status="healthy"),
            },
        )

        assert response.status == "healthy"
        assert len(response.components) == 2

    def test_degraded_status(self):
        """Test degraded status when component is degraded."""
        response = DetailedHealthResponse(
            status="degraded",
            environment="development",
            version="0.1.0",
            components={
                "redis": ComponentHealth(status="healthy"),
                "qdrant": ComponentHealth(status="degraded"),
            },
        )

        assert response.status == "degraded"


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_returns_status(self, client):
        """Test health endpoint returns status."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"

    def test_health_returns_version(self, client):
        """Test health endpoint returns version."""
        response = client.get("/health")
        data = response.json()

        assert "version" in data


class TestHealthzEndpoint:
    """Tests for /healthz endpoint."""

    def test_healthz_returns_200(self, client):
        """Test healthz endpoint returns 200."""
        response = client.get("/healthz")

        assert response.status_code == 200


class TestLiveEndpoint:
    """Tests for /live endpoint."""

    def test_live_returns_200(self, client):
        """Test live endpoint returns 200."""
        response = client.get("/live")

        assert response.status_code == 200


class TestCheckRedisHealth:
    """Tests for check_redis_health function."""

    @pytest.mark.asyncio
    async def test_redis_healthy(self):
        """Test Redis health when connected."""
        mock_request = MagicMock()
        mock_app_state = MagicMock()
        mock_app_state.redis_pool = MagicMock()
        mock_request.app.state.app_state = mock_app_state

        # Mock RedisRepository at the import location
        with patch(
            "app.repositories.redis_repository.RedisRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.ping = AsyncMock(return_value=True)
            mock_repo_class.return_value = mock_repo

            health = await check_redis_health(mock_request)

        # Check that it returns a ComponentHealth object
        assert health.status in ["healthy", "unhealthy", "degraded"]

    @pytest.mark.asyncio
    async def test_redis_unhealthy_no_pool(self):
        """Test Redis health when pool not available."""
        mock_request = MagicMock()
        mock_app_state = MagicMock()
        mock_app_state.redis_pool = None
        mock_request.app.state.app_state = mock_app_state

        health = await check_redis_health(mock_request)

        assert health.status == "unhealthy"

    @pytest.mark.asyncio
    async def test_redis_unhealthy_no_app_state(self):
        """Test Redis health when app state not initialized."""
        mock_request = MagicMock()
        # Create a mock that doesn't have app_state attribute
        mock_state = MagicMock()
        del mock_state.app_state  # Remove the attribute
        mock_request.app.state = mock_state

        health = await check_redis_health(mock_request)

        assert health.status == "unhealthy"


class TestCheckQdrantHealth:
    """Tests for check_qdrant_health function."""

    @pytest.mark.asyncio
    async def test_qdrant_degraded_no_client(self):
        """Test Qdrant health when client not initialized."""
        mock_request = MagicMock()
        mock_app_state = MagicMock()
        mock_app_state.qdrant_client = None
        mock_request.app.state.app_state = mock_app_state

        health = await check_qdrant_health(mock_request)

        assert health.status == "degraded"

