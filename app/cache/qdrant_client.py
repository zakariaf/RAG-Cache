"""
Qdrant client connection manager.

Sandi Metz Principles:
- Single Responsibility: Qdrant connection management
- Small methods: Each operation isolated
- Dependency Injection: Configuration injected
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from qdrant_client import AsyncQdrantClient

from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_qdrant_client() -> AsyncQdrantClient:
    """
    Create Qdrant async client connection.

    Returns:
        Qdrant async client

    Raises:
        ConnectionError: If connection fails
    """
    try:
        client = AsyncQdrantClient(
            host=config.qdrant_host,
            port=config.qdrant_port,
            timeout=30,
        )

        # Test connection
        await client.get_collections()

        logger.info(
            "Qdrant client connected",
            host=config.qdrant_host,
            port=config.qdrant_port,
        )

        return client

    except Exception as e:
        logger.error("Qdrant connection failed", error=str(e))
        raise ConnectionError(f"Failed to connect to Qdrant: {e}")


class QdrantConnectionManager:
    """
    Manages Qdrant client connection lifecycle.

    Handles connection pooling and health checks.
    """

    def __init__(self):
        """Initialize connection manager."""
        self._client: Optional[AsyncQdrantClient] = None

    async def get_client(self) -> AsyncQdrantClient:
        """
        Get or create Qdrant client.

        Returns:
            Qdrant async client

        Raises:
            ConnectionError: If connection fails
        """
        if self._client is None:
            self._client = await create_qdrant_client()
        return self._client

    async def close(self) -> None:
        """Close Qdrant client connection."""
        if self._client is not None:
            try:
                await self._client.close()
                logger.info("Qdrant client closed")
            except Exception as e:
                logger.error("Failed to close Qdrant client", error=str(e))
            finally:
                self._client = None

    async def health_check(self) -> bool:
        """
        Check Qdrant server health.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self.get_client()
            await client.get_collections()
            return True
        except Exception as e:
            logger.error("Qdrant health check failed", error=str(e))
            return False

    async def reconnect(self) -> bool:
        """
        Reconnect to Qdrant server.

        Returns:
            True if reconnected successfully
        """
        try:
            await self.close()
            self._client = await create_qdrant_client()
            return True
        except Exception as e:
            logger.error("Qdrant reconnection failed", error=str(e))
            return False


@asynccontextmanager
async def get_pooled_client() -> AsyncIterator[AsyncQdrantClient]:
    """
    Context manager for acquiring pooled connection.

    Yields:
        Qdrant client from pool

    Example:
        async with get_pooled_client() as client:
            await client.upsert(...)
    """
    from app.cache.qdrant_pool import get_pool

    pool = await get_pool()
    client = await pool.acquire()
    try:
        yield client
    finally:
        await pool.release(client)
