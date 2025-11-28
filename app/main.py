"""
Main FastAPI application.

Following Sandi Metz:
- Single Responsibility: Application setup and configuration
- Small methods: Each lifecycle stage isolated
- Clear naming: Descriptive function names
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.api.middleware import (
    RequestLoggingMiddleware,
    default_logging_config,
)
from app.api.routes import health, metrics, query
from app.api.routes.docs import API_DESCRIPTION, TAGS_METADATA
from app.config import config
from app.repositories.redis_repository import create_redis_pool
from app.utils.logger import get_logger, setup_logging

setup_logging(config.log_level)
logger = get_logger(__name__)


class ApplicationState:
    """
    Manages application-wide state.

    Single Responsibility: Lifecycle management of shared resources.
    """

    def __init__(self) -> None:
        self.redis_pool: Optional[object] = None
        self.qdrant_client: Optional[object] = None
        self.embedding_model: Optional[object] = None

    async def startup(self) -> None:
        """Initialize application resources."""
        logger.info("Starting RAGCache", env=config.app_env)
        try:
            # Initialize Redis connection pool
            self.redis_pool = await create_redis_pool()
            logger.info("Redis pool initialized")
            # TODO: Initialize Qdrant and embedding model
            logger.info("RAGCache started successfully")
        except Exception as e:
            logger.error("Failed to initialize RAGCache", error=str(e))
            raise

    async def shutdown(self) -> None:
        """Cleanup application resources."""
        logger.info("Shutting down RAGCache")
        try:
            if self.redis_pool:
                await self.redis_pool.disconnect()  # type: ignore
                logger.info("Redis pool closed")
            # TODO: Cleanup Qdrant and embedding model
            logger.info("RAGCache shut down successfully")
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    state = ApplicationState()
    await state.startup()
    app.state.app_state = state

    yield

    await state.shutdown()


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title=config.app_name,
        description=API_DESCRIPTION,
        version="0.1.0",
        docs_url="/docs" if config.is_development else None,
        redoc_url="/redoc" if config.is_development else None,
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )

    # Add middleware (order matters - first added is last executed)

    # GZip compression for responses
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # Request logging
    app.add_middleware(
        RequestLoggingMiddleware,
        config=default_logging_config,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
    )

    # Note: Rate limiting and auth middleware can be enabled via:
    # from app.api.middleware import RateLimitMiddleware, AuthMiddleware
    # app.add_middleware(RateLimitMiddleware)
    # app.add_middleware(AuthMiddleware, config=auth_config)

    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(query.router, prefix="/api/v1", tags=["query"])
    app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.is_development,
    )
