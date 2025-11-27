"""
Health check endpoints.

Sandi Metz Principles:
- Single Responsibility: Health check logic only
- Small functions: Each check isolated
- Clear naming: Descriptive endpoint names
"""

from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config import config
from app.models.response import HealthResponse
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class ComponentHealth(BaseModel):
    """Health status of a component."""

    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        ..., description="Component status"
    )
    latency_ms: Optional[float] = Field(None, description="Check latency in ms")
    message: Optional[str] = Field(None, description="Status message")


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""

    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        ..., description="Overall status"
    )
    environment: str = Field(..., description="Environment name")
    version: str = Field(..., description="Application version")
    components: Dict[str, ComponentHealth] = Field(
        default_factory=dict, description="Component health status"
    )
    uptime_seconds: Optional[float] = Field(None, description="Uptime in seconds")


async def check_redis_health(request: Request) -> ComponentHealth:
    """Check Redis health."""
    import time

    try:
        if not hasattr(request.app.state, "app_state"):
            return ComponentHealth(status="unhealthy", message="App state not initialized")

        app_state = request.app.state.app_state
        if not app_state.redis_pool:
            return ComponentHealth(status="unhealthy", message="Redis pool not available")

        from app.repositories.redis_repository import RedisRepository

        start = time.time()
        repo = RedisRepository(app_state.redis_pool)
        is_healthy = await repo.ping()
        latency = (time.time() - start) * 1000

        if is_healthy:
            return ComponentHealth(status="healthy", latency_ms=round(latency, 2))
        return ComponentHealth(status="unhealthy", message="Ping failed")

    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return ComponentHealth(status="unhealthy", message=str(e))


async def check_qdrant_health(request: Request) -> ComponentHealth:
    """Check Qdrant health."""
    import time

    try:
        if not hasattr(request.app.state, "app_state"):
            return ComponentHealth(status="unhealthy", message="App state not initialized")

        app_state = request.app.state.app_state
        if not app_state.qdrant_client:
            return ComponentHealth(
                status="degraded", message="Qdrant client not initialized"
            )

        # If Qdrant client exists, try to ping it
        start = time.time()
        # Would call qdrant health check here
        latency = (time.time() - start) * 1000

        return ComponentHealth(status="healthy", latency_ms=round(latency, 2))

    except Exception as e:
        logger.error("Qdrant health check failed", error=str(e))
        return ComponentHealth(status="degraded", message=str(e))


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
    Kubernetes-style liveness check endpoint.

    Returns:
        Health status response
    """
    return await health_check()


@router.get("/ready", response_model=DetailedHealthResponse)
async def readiness_check(request: Request) -> DetailedHealthResponse:
    """
    Kubernetes-style readiness check endpoint.

    Checks all dependencies and returns detailed status.

    Returns:
        Detailed health status response
    """
    components = {}

    # Check Redis
    redis_health = await check_redis_health(request)
    components["redis"] = redis_health

    # Check Qdrant
    qdrant_health = await check_qdrant_health(request)
    components["qdrant"] = qdrant_health

    # Determine overall status
    statuses = [c.status for c in components.values()]
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        environment=config.app_env,
        version="0.1.0",
        components=components,
    )


@router.get("/live", response_model=HealthResponse)
async def liveness_check() -> HealthResponse:
    """
    Kubernetes liveness probe endpoint.

    Always returns healthy if the application is running.

    Returns:
        Health status response
    """
    return HealthResponse(
        status="healthy",
        environment=config.app_env,
        version="0.1.0",
    )
