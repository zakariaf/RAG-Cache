"""
Qdrant connection pool manager.

Sandi Metz Principles:
- Single Responsibility: Connection pooling
- Small methods: Each operation focused
- Clear naming: Descriptive method names
"""

import asyncio
from typing import Dict, List, Optional

from qdrant_client import AsyncQdrantClient

from app.cache.qdrant_client import create_qdrant_client
from app.cache.qdrant_errors import QdrantConnectionError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PoolConfig:
    """
    Configuration for connection pool.

    Defines pool behavior and limits.
    """

    def __init__(
        self,
        min_size: int = 1,
        max_size: int = 10,
        idle_timeout: float = 300.0,
        max_lifetime: float = 3600.0,
        acquire_timeout: float = 30.0,
    ):
        """
        Initialize pool configuration.

        Args:
            min_size: Minimum pool connections
            max_size: Maximum pool connections
            idle_timeout: Max idle time before closing (seconds)
            max_lifetime: Max connection lifetime (seconds)
            acquire_timeout: Timeout for acquiring connection (seconds)
        """
        self.min_size = max(1, min_size)
        self.max_size = max(self.min_size, max_size)
        self.idle_timeout = idle_timeout
        self.max_lifetime = max_lifetime
        self.acquire_timeout = acquire_timeout


class PooledConnection:
    """
    Wrapper for pooled connection.

    Tracks connection metadata for pool management.
    """

    def __init__(self, client: AsyncQdrantClient):
        """
        Initialize pooled connection.

        Args:
            client: Qdrant client instance
        """
        self.client = client
        self.created_at = asyncio.get_event_loop().time()
        self.last_used = self.created_at
        self.in_use = False
        self.use_count = 0

    def mark_used(self) -> None:
        """Mark connection as in use."""
        self.in_use = True
        self.use_count += 1
        self.last_used = asyncio.get_event_loop().time()

    def mark_released(self) -> None:
        """Mark connection as released."""
        self.in_use = False
        self.last_used = asyncio.get_event_loop().time()

    def is_expired(self, max_lifetime: float) -> bool:
        """
        Check if connection has exceeded max lifetime.

        Args:
            max_lifetime: Maximum lifetime in seconds

        Returns:
            True if expired
        """
        age = asyncio.get_event_loop().time() - self.created_at
        return age > max_lifetime

    def is_idle_expired(self, idle_timeout: float) -> bool:
        """
        Check if connection has been idle too long.

        Args:
            idle_timeout: Idle timeout in seconds

        Returns:
            True if idle too long
        """
        idle_time = asyncio.get_event_loop().time() - self.last_used
        return not self.in_use and idle_time > idle_timeout


class QdrantConnectionPool:
    """
    Connection pool for Qdrant clients.

    Manages a pool of reusable connections with lifecycle management.
    """

    def __init__(self, config: Optional[PoolConfig] = None):
        """
        Initialize connection pool.

        Args:
            config: Pool configuration
        """
        self._config = config or PoolConfig()
        self._pool: List[PooledConnection] = []
        self._lock = asyncio.Lock()
        self._closed = False
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize pool with minimum connections."""
        async with self._lock:
            if self._closed:
                raise QdrantConnectionError("Pool is closed")

            # Create minimum connections
            for _ in range(self._config.min_size):
                await self._create_connection()

            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

            logger.info(
                "Connection pool initialized",
                min_size=self._config.min_size,
                max_size=self._config.max_size,
            )

    async def acquire(self) -> AsyncQdrantClient:
        """
        Acquire a connection from the pool.

        Returns:
            Qdrant client

        Raises:
            QdrantConnectionError: If unable to acquire connection
        """
        try:
            return await asyncio.wait_for(
                self._acquire_internal(),
                timeout=self._config.acquire_timeout,
            )
        except asyncio.TimeoutError:
            raise QdrantConnectionError(
                f"Timeout acquiring connection after {self._config.acquire_timeout}s"
            )

    async def _acquire_internal(self) -> AsyncQdrantClient:
        """
        Internal acquire logic.

        Returns:
            Qdrant client
        """
        while True:
            async with self._lock:
                if self._closed:
                    raise QdrantConnectionError("Pool is closed")

                # Find available connection
                for conn in self._pool:
                    if not conn.in_use:
                        # Check if expired
                        if conn.is_expired(self._config.max_lifetime):
                            await self._remove_connection(conn)
                            continue

                        conn.mark_used()
                        logger.debug(
                            "Connection acquired from pool",
                            pool_size=len(self._pool),
                            use_count=conn.use_count,
                        )
                        return conn.client

                # Create new connection if below max
                if len(self._pool) < self._config.max_size:
                    conn = await self._create_connection()
                    conn.mark_used()
                    logger.debug(
                        "New connection created and acquired",
                        pool_size=len(self._pool),
                    )
                    return conn.client

            # Wait briefly before retrying
            await asyncio.sleep(0.1)

    async def release(self, client: AsyncQdrantClient) -> None:
        """
        Release a connection back to the pool.

        Args:
            client: Qdrant client to release
        """
        async with self._lock:
            for conn in self._pool:
                if conn.client is client:
                    conn.mark_released()
                    logger.debug(
                        "Connection released to pool",
                        pool_size=len(self._pool),
                        in_use_count=sum(1 for c in self._pool if c.in_use),
                    )
                    return

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self._lock:
            if self._closed:
                return

            self._closed = True

            # Cancel cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Close all connections
            for conn in self._pool[:]:
                await self._remove_connection(conn)

            logger.info("Connection pool closed")

    async def _create_connection(self) -> PooledConnection:
        """
        Create a new pooled connection.

        Returns:
            Pooled connection
        """
        client = await create_qdrant_client()
        conn = PooledConnection(client)
        self._pool.append(conn)
        return conn

    async def _remove_connection(self, conn: PooledConnection) -> None:
        """
        Remove and close a connection.

        Args:
            conn: Connection to remove
        """
        try:
            await conn.client.close()
        except Exception as e:
            logger.error("Error closing connection", error=str(e))
        finally:
            if conn in self._pool:
                self._pool.remove(conn)

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup expired connections."""
        while not self._closed:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup loop error", error=str(e))

    async def _cleanup_expired(self) -> None:
        """Remove expired and idle connections."""
        async with self._lock:
            expired = []

            for conn in self._pool:
                # Skip connections in use
                if conn.in_use:
                    continue

                # Check lifetime
                if conn.is_expired(self._config.max_lifetime):
                    expired.append(conn)
                    continue

                # Check idle timeout (keep minimum connections)
                if len(self._pool) > self._config.min_size:
                    if conn.is_idle_expired(self._config.idle_timeout):
                        expired.append(conn)

            # Remove expired connections
            for conn in expired:
                await self._remove_connection(conn)

            if expired:
                logger.info(
                    "Cleaned up expired connections",
                    removed=len(expired),
                    remaining=len(self._pool),
                )

    def get_stats(self) -> Dict[str, int]:
        """
        Get pool statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total": len(self._pool),
            "in_use": sum(1 for conn in self._pool if conn.in_use),
            "available": sum(1 for conn in self._pool if not conn.in_use),
            "min_size": self._config.min_size,
            "max_size": self._config.max_size,
        }


# Global pool instance
_global_pool: Optional[QdrantConnectionPool] = None


async def get_pool() -> QdrantConnectionPool:
    """
    Get or create global connection pool.

    Returns:
        Connection pool instance
    """
    global _global_pool

    if _global_pool is None:
        _global_pool = QdrantConnectionPool()
        await _global_pool.initialize()

    return _global_pool


async def close_pool() -> None:
    """Close global connection pool."""
    global _global_pool

    if _global_pool is not None:
        await _global_pool.close()
        _global_pool = None
