"""Test API routes."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_query_service
from app.api.routes.health import router as health_router
from app.api.routes.query import router as query_router
from app.exceptions import LLMProviderError
from app.models.response import CacheInfo, QueryResponse, UsageMetrics


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(query_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app, mock_query_service):
    """Create test client with dependency override."""
    app.dependency_overrides[get_query_service] = lambda: mock_query_service
    return TestClient(app)


@pytest.fixture
def mock_query_service():
    """Create mock query service."""
    return AsyncMock()


@pytest.fixture
def sample_response():
    """Create sample query response."""
    return QueryResponse(
        response="Python is a programming language",
        provider="openai",
        model="gpt-3.5-turbo",
        usage=UsageMetrics.create(10, 20),
        cache_info=CacheInfo.miss(),
        latency_ms=150.5,
    )


class TestHealthRoutes:
    """Test health check routes."""

    def test_should_return_health_status(self, client):
        """Test basic health check."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_should_return_kubernetes_health(self, client):
        """Test Kubernetes health check."""
        response = client.get("/api/v1/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_should_return_readiness_status(self, client):
        """Test readiness check."""
        response = client.get("/api/v1/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestQueryRoutes:
    """Test query routes."""

    def test_should_process_query(self, client, mock_query_service, sample_response):
        """Test processing query."""
        mock_query_service.process.return_value = sample_response

        response = client.post(
            "/api/v1/query",
            json={"query": "What is Python?", "use_cache": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Python is a programming language"
        assert data["provider"] == "openai"
        assert data["cache_info"]["cache_hit"] is False

    def test_should_validate_request(self, client):
        """Test request validation."""
        response = client.post("/api/v1/query", json={})

        assert response.status_code == 422  # Validation error

    def test_should_handle_llm_provider_error(self, client, mock_query_service):
        """Test handling LLM provider errors."""
        mock_query_service.process.side_effect = LLMProviderError("API error")

        response = client.post(
            "/api/v1/query",
            json={"query": "What is Python?"},
        )

        assert response.status_code == 502
        assert "API error" in response.json()["detail"]

    def test_should_handle_unexpected_error(self, client, mock_query_service):
        """Test handling unexpected errors."""
        mock_query_service.process.side_effect = RuntimeError("Unexpected error")

        response = client.post(
            "/api/v1/query",
            json={"query": "What is Python?"},
        )

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_should_accept_custom_parameters(
        self, client, mock_query_service, sample_response
    ):
        """Test accepting custom parameters."""
        mock_query_service.process.return_value = sample_response

        response = client.post(
            "/api/v1/query",
            json={
                "query": "What is Python?",
                "model": "gpt-4",
                "max_tokens": 500,
                "temperature": 0.7,
                "use_cache": False,
            },
        )

        assert response.status_code == 200
        # Verify service was called with the request
        mock_query_service.process.assert_called_once()
