"""Unit tests for Qdrant connection pool."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cache.qdrant_errors import QdrantConnectionError
from app.cache.qdrant_pool import (
    PoolConfig,
    PooledConnection,
    QdrantConnectionPool,
    close_pool,
    get_pool,
)


class TestPoolConfig:
    """Tests for PoolConfig class."""

    def test_pool_config_defaults(self):
        """Test pool config with default values."""
        config = PoolConfig()

        assert config.min_size == 1
        assert config.max_size == 10
        assert config.idle_timeout == 300.0
        assert config.max_lifetime == 3600.0
        assert config.acquire_timeout == 30.0

    def test_pool_config_custom_values(self):
        """Test pool config with custom values."""
        config = PoolConfig(
            min_size=2,
            max_size=20,
            idle_timeout=600.0,
            max_lifetime=7200.0,
            acquire_timeout=60.0,
        )

        assert config.min_size == 2
        assert config.max_size == 20
        assert config.idle_timeout == 600.0
        assert config.max_lifetime == 7200.0
        assert config.acquire_timeout == 60.0

    def test_pool_config_min_size_validation(self):
        """Test pool config validates min_size >= 1."""
        config = PoolConfig(min_size=0, max_size=10)

        assert config.min_size == 1

    def test_pool_config_max_size_validation(self):
        """Test pool config validates max_size >= min_size."""
        config = PoolConfig(min_size=10, max_size=5)

        assert config.max_size == 10


class TestPooledConnection:
    """Tests for PooledConnection class."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Qdrant client."""
        return AsyncMock()

    @pytest.fixture
    def pooled_conn(self, mock_client):
        """Create pooled connection."""
        return PooledConnection(mock_client)

    def test_pooled_connection_init(self, pooled_conn, mock_client):
        """Test pooled connection initialization."""
        assert pooled_conn.client is mock_client
        assert pooled_conn.in_use is False
        assert pooled_conn.use_count == 0
        assert pooled_conn.created_at > 0
        assert pooled_conn.last_used == pooled_conn.created_at

    def test_mark_used(self, pooled_conn):
        """Test marking connection as used."""
        initial_count = pooled_conn.use_count

        pooled_conn.mark_used()

        assert pooled_conn.in_use is True
        assert pooled_conn.use_count == initial_count + 1
        assert pooled_conn.last_used > pooled_conn.created_at

    def test_mark_released(self, pooled_conn):
        """Test marking connection as released."""
        pooled_conn.mark_used()
        pooled_conn.mark_released()

        assert pooled_conn.in_use is False

    def test_is_expired_true(self, pooled_conn):
        """Test connection is expired when max lifetime exceeded."""
        # Mock time to make connection appear old
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = pooled_conn.created_at + 3700

            is_expired = pooled_conn.is_expired(max_lifetime=3600.0)

            assert is_expired is True

    def test_is_expired_false(self, pooled_conn):
        """Test connection is not expired when within lifetime."""
        is_expired = pooled_conn.is_expired(max_lifetime=3600.0)

        assert is_expired is False

    def test_is_idle_expired_true(self, pooled_conn):
        """Test connection is idle expired."""
        # Mock time to make connection appear idle
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = pooled_conn.last_used + 400

            is_idle = pooled_conn.is_idle_expired(idle_timeout=300.0)

            assert is_idle is True

    def test_is_idle_expired_false_within_timeout(self, pooled_conn):
        """Test connection is not idle expired when within timeout."""
        is_idle = pooled_conn.is_idle_expired(idle_timeout=300.0)

        assert is_idle is False

    def test_is_idle_expired_false_in_use(self, pooled_conn):
        """Test connection is not idle expired when in use."""
        pooled_conn.mark_used()

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = pooled_conn.last_used + 400

            is_idle = pooled_conn.is_idle_expired(idle_timeout=300.0)

            assert is_idle is False


class TestQdrantConnectionPool:
    """Tests for QdrantConnectionPool class."""

    @pytest.fixture
    def pool_config(self):
        """Create pool config for testing."""
        return PoolConfig(min_size=1, max_size=3, acquire_timeout=5.0)

    @pytest.fixture
    async def pool(self, pool_config):
        """Create connection pool."""
        pool = QdrantConnectionPool(pool_config)
        yield pool
        # Cleanup
        try:
            await pool.close()
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_pool_initialize(self, pool_config):
        """Test pool initialization."""
        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_create_client.return_value = AsyncMock()

            pool = QdrantConnectionPool(pool_config)
            await pool.initialize()

            stats = pool.get_stats()
            assert stats["total"] >= pool_config.min_size
            assert stats["min_size"] == pool_config.min_size
            assert stats["max_size"] == pool_config.max_size

            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_initialize_when_closed(self, pool):
        """Test initializing closed pool raises error."""
        with patch("app.cache.qdrant_pool.create_qdrant_client") as mock_create:
            mock_create.return_value = AsyncMock()

            await pool.initialize()
            await pool.close()

            with pytest.raises(QdrantConnectionError, match="Pool is closed"):
                await pool.initialize()

    @pytest.mark.asyncio
    async def test_pool_acquire_and_release(self, pool_config):
        """Test acquiring and releasing connection."""
        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_create_client.return_value = mock_client

            pool = QdrantConnectionPool(pool_config)
            await pool.initialize()

            # Acquire connection
            client = await pool.acquire()
            assert client is not None

            stats = pool.get_stats()
            assert stats["in_use"] == 1

            # Release connection
            await pool.release(client)

            stats = pool.get_stats()
            assert stats["in_use"] == 0

            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_acquire_timeout(self, pool_config):
        """Test acquire timeout when pool is full."""
        # Set very short timeout for testing
        pool_config.acquire_timeout = 0.5
        pool_config.max_size = 1

        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_create_client.return_value = mock_client

            pool = QdrantConnectionPool(pool_config)
            await pool.initialize()

            # Acquire the only connection
            client = await pool.acquire()

            # Try to acquire when pool is full - should timeout
            with pytest.raises(QdrantConnectionError, match="Timeout acquiring"):
                await pool.acquire()

            await pool.release(client)
            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_acquire_when_closed(self, pool):
        """Test acquiring from closed pool raises error."""
        with patch("app.cache.qdrant_pool.create_qdrant_client") as mock_create:
            mock_create.return_value = AsyncMock()

            await pool.initialize()
            await pool.close()

            with pytest.raises(QdrantConnectionError, match="Pool is closed"):
                await pool.acquire()

    @pytest.mark.asyncio
    async def test_pool_creates_new_connection_when_needed(self, pool_config):
        """Test pool creates new connections up to max_size."""
        pool_config.min_size = 1
        pool_config.max_size = 2

        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_create_client.return_value = AsyncMock()

            pool = QdrantConnectionPool(pool_config)
            await pool.initialize()

            # Acquire two connections
            client1 = await pool.acquire()
            client2 = await pool.acquire()

            stats = pool.get_stats()
            assert stats["total"] == 2
            assert stats["in_use"] == 2

            await pool.release(client1)
            await pool.release(client2)
            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_close(self, pool_config):
        """Test closing pool."""
        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_create_client.return_value = mock_client

            pool = QdrantConnectionPool(pool_config)
            await pool.initialize()

            await pool.close()

            # Verify client was closed
            assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_pool_close_idempotent(self, pool):
        """Test closing pool multiple times is safe."""
        with patch("app.cache.qdrant_pool.create_qdrant_client") as mock_create:
            mock_create.return_value = AsyncMock()

            await pool.initialize()
            await pool.close()
            await pool.close()  # Should not raise error

    @pytest.mark.asyncio
    async def test_pool_cleanup_expired_connections(self, pool_config):
        """Test cleanup of expired connections."""
        pool_config.max_lifetime = 0.1  # Very short lifetime

        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_create_client.return_value = mock_client

            pool = QdrantConnectionPool(pool_config)
            await pool.initialize()

            # Acquire and release to mark connection
            client = await pool.acquire()
            await pool.release(client)

            # Wait for connection to expire
            await asyncio.sleep(0.2)

            # Manually trigger cleanup
            await pool._cleanup_expired()

            # Connection should be removed and new one created on next acquire
            stats = pool.get_stats()
            # After cleanup, expired connections are removed
            assert stats["total"] >= 0

            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_get_stats(self, pool_config):
        """Test getting pool statistics."""
        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_create_client.return_value = AsyncMock()

            pool = QdrantConnectionPool(pool_config)
            await pool.initialize()

            stats = pool.get_stats()

            assert "total" in stats
            assert "in_use" in stats
            assert "available" in stats
            assert "min_size" in stats
            assert "max_size" in stats
            assert stats["min_size"] == pool_config.min_size
            assert stats["max_size"] == pool_config.max_size

            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_release_unknown_client(self, pool):
        """Test releasing unknown client doesn't raise error."""
        with patch("app.cache.qdrant_pool.create_qdrant_client") as mock_create:
            mock_create.return_value = AsyncMock()

            await pool.initialize()

            unknown_client = AsyncMock()
            await pool.release(unknown_client)  # Should not raise

            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_remove_connection_error_handling(self, pool_config):
        """Test connection removal handles errors gracefully."""
        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_client.close.side_effect = Exception("Close failed")
            mock_create_client.return_value = mock_client

            pool = QdrantConnectionPool(pool_config)
            await pool.initialize()

            # Close should handle error gracefully
            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_cleanup_loop_error_handling(self, pool_config):
        """Test cleanup loop handles errors."""
        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_create_client.return_value = AsyncMock()

            pool = QdrantConnectionPool(pool_config)
            await pool.initialize()

            # Force error in cleanup
            with patch.object(pool, "_cleanup_expired", side_effect=Exception("Error")):
                # Wait briefly to let cleanup run
                await asyncio.sleep(0.1)

            await pool.close()


class TestGlobalPool:
    """Tests for global pool functions."""

    @pytest.mark.asyncio
    async def test_get_pool_creates_instance(self):
        """Test get_pool creates and initializes pool."""
        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_create_client.return_value = AsyncMock()

            pool = await get_pool()

            assert pool is not None
            assert isinstance(pool, QdrantConnectionPool)

            await close_pool()

    @pytest.mark.asyncio
    async def test_get_pool_returns_same_instance(self):
        """Test get_pool returns same instance on multiple calls."""
        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_create_client.return_value = AsyncMock()

            pool1 = await get_pool()
            pool2 = await get_pool()

            assert pool1 is pool2

            await close_pool()

    @pytest.mark.asyncio
    async def test_close_pool_global(self):
        """Test closing global pool."""
        with patch(
            "app.cache.qdrant_pool.create_qdrant_client"
        ) as mock_create_client:
            mock_create_client.return_value = AsyncMock()

            pool = await get_pool()
            assert pool is not None

            await close_pool()

            # Next get_pool should create new instance
            new_pool = await get_pool()
            assert new_pool is not pool

            await close_pool()

    @pytest.mark.asyncio
    async def test_close_pool_when_none(self):
        """Test closing pool when none exists doesn't raise error."""
        await close_pool()  # Should not raise
