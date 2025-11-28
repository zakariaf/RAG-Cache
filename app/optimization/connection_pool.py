"""
Connection pool optimization.

Sandi Metz Principles:
- Single Responsibility: Connection pooling
- Small methods: Each operation isolated
- Configurable: Flexible pool settings
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class PoolConfig:
    """Connection pool configuration."""

    # Pool size
    min_size: int = 5
    max_size: int = 20

    # Timeouts
    acquire_timeout_seconds: float = 5.0
    idle_timeout_seconds: float = 300.0  # 5 minutes
    max_lifetime_seconds: float = 3600.0  # 1 hour

    # Health checking
    health_check_interval_seconds: float = 30.0
    enable_health_check: bool = True

    # Behavior
    overflow_allowed: bool = True
    max_overflow: int = 10


@dataclass
class PooledConnection(Generic[T]):
    """A connection managed by the pool."""

    connection: T
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0
    in_use: bool = False

    def mark_used(self) -> None:
        """Mark connection as used."""
        self.last_used_at = time.time()
        self.use_count += 1
        self.in_use = True

    def mark_released(self) -> None:
        """Mark connection as released."""
        self.in_use = False

    def is_expired(self, max_lifetime: float) -> bool:
        """Check if connection has exceeded max lifetime."""
        return (time.time() - self.created_at) > max_lifetime

    def is_idle(self, idle_timeout: float) -> bool:
        """Check if connection has been idle too long."""
        return not self.in_use and (time.time() - self.last_used_at) > idle_timeout


@dataclass
class PoolStats:
    """Pool statistics."""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    overflow_connections: int = 0
    total_acquires: int = 0
    total_releases: int = 0
    failed_acquires: int = 0
    connections_recycled: int = 0


class ConnectionPoolManager(Generic[T]):
    """
    Manages a pool of connections for efficient resource usage.

    Handles connection lifecycle, health checking, and overflow.
    """

    def __init__(
        self,
        factory: Callable[[], T],
        close_fn: Optional[Callable[[T], None]] = None,
        health_check_fn: Optional[Callable[[T], bool]] = None,
        config: Optional[PoolConfig] = None,
    ):
        """
        Initialize pool manager.

        Args:
            factory: Function to create new connections
            close_fn: Function to close a connection
            health_check_fn: Function to check connection health
            config: Pool configuration
        """
        self._factory = factory
        self._close_fn = close_fn or (lambda c: None)
        self._health_check_fn = health_check_fn or (lambda c: True)
        self._config = config or PoolConfig()

        self._pool: list[PooledConnection[T]] = []
        self._overflow_pool: list[PooledConnection[T]] = []
        self._lock = asyncio.Lock()
        self._available = asyncio.Condition()
        self._stats = PoolStats()
        self._initialized = False
        self._closed = False

    async def initialize(self) -> None:
        """Initialize the pool with minimum connections."""
        if self._initialized:
            return

        async with self._lock:
            for _ in range(self._config.min_size):
                conn = await self._create_connection()
                self._pool.append(conn)

            self._initialized = True
            logger.info("Connection pool initialized", min_size=self._config.min_size)

    async def _create_connection(self) -> PooledConnection[T]:
        """Create a new pooled connection."""
        try:
            conn = await asyncio.to_thread(self._factory)
            pooled = PooledConnection(connection=conn)
            self._stats.total_connections += 1
            return pooled
        except Exception as e:
            logger.error("Failed to create connection", error=str(e))
            raise

    async def acquire(self) -> T:
        """
        Acquire a connection from the pool.

        Returns:
            A connection

        Raises:
            TimeoutError: If no connection available within timeout
        """
        if not self._initialized:
            await self.initialize()

        async with self._available:
            start_time = time.time()
            timeout = self._config.acquire_timeout_seconds

            while True:
                # Try to get an idle connection
                conn = self._find_idle_connection()
                if conn:
                    conn.mark_used()
                    self._stats.total_acquires += 1
                    self._update_stats()
                    return conn.connection

                # Try to create new connection if under max
                if self._can_create_connection():
                    try:
                        pooled = await self._create_connection()
                        pooled.mark_used()

                        if len(self._pool) < self._config.max_size:
                            self._pool.append(pooled)
                        else:
                            self._overflow_pool.append(pooled)
                            self._stats.overflow_connections += 1

                        self._stats.total_acquires += 1
                        self._update_stats()
                        return pooled.connection
                    except Exception as e:
                        self._stats.failed_acquires += 1
                        raise

                # Wait for a connection to be released
                elapsed = time.time() - start_time
                remaining = timeout - elapsed

                if remaining <= 0:
                    self._stats.failed_acquires += 1
                    raise TimeoutError(
                        f"Could not acquire connection within {timeout}s"
                    )

                try:
                    await asyncio.wait_for(self._available.wait(), timeout=remaining)
                except asyncio.TimeoutError:
                    self._stats.failed_acquires += 1
                    raise TimeoutError(
                        f"Could not acquire connection within {timeout}s"
                    )

    def _find_idle_connection(self) -> Optional[PooledConnection[T]]:
        """Find an idle, healthy connection."""
        # Check main pool first
        for pooled in self._pool:
            if not pooled.in_use:
                if pooled.is_expired(self._config.max_lifetime_seconds):
                    self._recycle_connection(pooled)
                    continue
                if self._config.enable_health_check:
                    if not self._health_check_fn(pooled.connection):
                        self._recycle_connection(pooled)
                        continue
                return pooled

        return None

    def _can_create_connection(self) -> bool:
        """Check if we can create a new connection."""
        total = len(self._pool) + len(self._overflow_pool)
        max_allowed = self._config.max_size

        if self._config.overflow_allowed:
            max_allowed += self._config.max_overflow

        return total < max_allowed

    def _recycle_connection(self, pooled: PooledConnection[T]) -> None:
        """Close and remove a connection."""
        try:
            self._close_fn(pooled.connection)
        except Exception as e:
            logger.warning("Error closing connection", error=str(e))

        if pooled in self._pool:
            self._pool.remove(pooled)
        elif pooled in self._overflow_pool:
            self._overflow_pool.remove(pooled)

        self._stats.connections_recycled += 1

    async def release(self, conn: T) -> None:
        """
        Release a connection back to the pool.

        Args:
            conn: The connection to release
        """
        async with self._available:
            # Find the pooled connection
            pooled = self._find_pooled_connection(conn)

            if pooled:
                pooled.mark_released()

                # Remove from overflow if idle connection
                if pooled in self._overflow_pool:
                    self._recycle_connection(pooled)

                self._stats.total_releases += 1
                self._update_stats()

            # Notify waiting acquires
            self._available.notify()

    def _find_pooled_connection(self, conn: T) -> Optional[PooledConnection[T]]:
        """Find pooled connection by connection object."""
        for pooled in self._pool + self._overflow_pool:
            if pooled.connection is conn:
                return pooled
        return None

    def _update_stats(self) -> None:
        """Update pool statistics."""
        active = sum(1 for p in self._pool if p.in_use)
        active += sum(1 for p in self._overflow_pool if p.in_use)

        self._stats.active_connections = active
        self._stats.idle_connections = len(self._pool) - active

    async def close(self) -> None:
        """Close all connections and shutdown the pool."""
        if self._closed:
            return

        async with self._lock:
            for pooled in self._pool + self._overflow_pool:
                try:
                    self._close_fn(pooled.connection)
                except Exception as e:
                    logger.warning("Error closing connection", error=str(e))

            self._pool.clear()
            self._overflow_pool.clear()
            self._closed = True

            logger.info("Connection pool closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        self._update_stats()
        return {
            "total_connections": len(self._pool) + len(self._overflow_pool),
            "pool_size": len(self._pool),
            "overflow_size": len(self._overflow_pool),
            "active_connections": self._stats.active_connections,
            "idle_connections": self._stats.idle_connections,
            "total_acquires": self._stats.total_acquires,
            "total_releases": self._stats.total_releases,
            "failed_acquires": self._stats.failed_acquires,
            "connections_recycled": self._stats.connections_recycled,
        }


class PoolContextManager(Generic[T]):
    """
    Context manager for automatic connection acquisition and release.

    Usage:
        async with pool.connection() as conn:
            await conn.execute(...)
    """

    def __init__(self, pool: ConnectionPoolManager[T]):
        """Initialize context manager."""
        self._pool = pool
        self._conn: Optional[T] = None

    async def __aenter__(self) -> T:
        """Acquire connection."""
        self._conn = await self._pool.acquire()
        return self._conn

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release connection."""
        if self._conn:
            await self._pool.release(self._conn)
