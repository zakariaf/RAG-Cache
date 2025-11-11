"""
Health check endpoints.

Sandi Metz Principles:
- Single Responsibility: Health check logic only
- Small functions: Each check isolated
- Clear naming: Descriptive endpoint names
"""

from fastapi import APIRouter

from app.config import config
from app.models.response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        Health status response
    """
    return HealthResponse(
        status="healthy",
        environment=config.app_env,
        version="0.1.0",
    )


@router.get("/healthz", response_model=HealthResponse)
async def kubernetes_health_check() -> HealthResponse:
    """
    Kubernetes-style health check endpoint.

    Returns:
        Health status response
    """
    return await health_check()


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """
    Kubernetes-style readiness check endpoint.

    Returns:
        Health status response
    """
    # TODO: Add checks for Redis, Qdrant, etc.
    return await health_check()
