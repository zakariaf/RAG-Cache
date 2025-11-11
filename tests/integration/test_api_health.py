"""Integration tests for health endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_application


@pytest.fixture
def client():
    """Create test client."""
    app = create_application()
    return TestClient(app)


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_should_return_healthy_status(self, client: TestClient):
        """Test health endpoint returns 200."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "environment" in data
        assert "version" in data

    def test_should_return_healthz_status(self, client: TestClient):
        """Test healthz endpoint returns 200."""
        response = client.get("/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_should_return_ready_status(self, client: TestClient):
        """Test readiness endpoint returns 200."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
