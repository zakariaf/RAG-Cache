"""Unit tests for Qdrant client connection manager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cache.qdrant_client import (
    QdrantConnectionManager,
    create_qdrant_client,
    get_pooled_client,
)


class TestCreateQdrantClient:
    """Tests for create_qdrant_client function."""

    @pytest.mark.asyncio
    async def test_create_qdrant_client_success(self):
        """Test successful Qdrant client creation."""
        with patch("app.cache.qdrant_client.AsyncQdrantClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_collections.return_value = MagicMock(collections=[])
            mock_client_class.return_value = mock_client

            with patch("app.cache.qdrant_client.config") as mock_config:
                mock_config.qdrant_host = "localhost"
                mock_config.qdrant_port = 6333

                client = await create_qdrant_client()

                assert client is mock_client
                mock_client.get_collections.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_qdrant_client_connection_failure(self):
        """Test Qdrant client creation handles connection failure."""
        with patch("app.cache.qdrant_client.AsyncQdrantClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_collections.side_effect = Exception("Connection refused")
            mock_client_class.return_value = mock_client

            with patch("app.cache.qdrant_client.config") as mock_config:
                mock_config.qdrant_host = "localhost"
                mock_config.qdrant_port = 6333

                with pytest.raises(ConnectionError, match="Failed to connect"):
                    await create_qdrant_client()

    @pytest.mark.asyncio
    async def test_create_qdrant_client_uses_config(self):
        """Test client creation uses config values."""
        with patch("app.cache.qdrant_client.AsyncQdrantClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_collections.return_value = MagicMock(collections=[])
            mock_client_class.return_value = mock_client

            with patch("app.cache.qdrant_client.config") as mock_config:
                mock_config.qdrant_host = "qdrant.example.com"
                mock_config.qdrant_port = 9999

                await create_qdrant_client()

                mock_client_class.assert_called_once_with(
                    host="qdrant.example.com", port=9999, timeout=30
                )


class TestQdrantConnectionManager:
    """Tests for QdrantConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create connection manager."""
        return QdrantConnectionManager()

    @pytest.mark.asyncio
    async def test_manager_init(self, manager):
        """Test manager initialization."""
        assert manager._client is None

    @pytest.mark.asyncio
    async def test_get_client_creates_new(self, manager):
        """Test get_client creates new client when none exists."""
        with patch(
            "app.cache.qdrant_client.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_create_client.return_value = mock_client

            client = await manager.get_client()

            assert client is mock_client
            mock_create_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self, manager):
        """Test get_client reuses existing client."""
        with patch(
            "app.cache.qdrant_client.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_create_client.return_value = mock_client

            client1 = await manager.get_client()
            client2 = await manager.get_client()

            assert client1 is client2
            mock_create_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_raises_on_error(self, manager):
        """Test get_client raises error on connection failure."""
        with patch(
            "app.cache.qdrant_client.create_qdrant_client"
        ) as mock_create_client:
            mock_create_client.side_effect = ConnectionError("Connection failed")

            with pytest.raises(ConnectionError, match="Connection failed"):
                await manager.get_client()

    @pytest.mark.asyncio
    async def test_close_client(self, manager):
        """Test closing client connection."""
        with patch(
            "app.cache.qdrant_client.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_create_client.return_value = mock_client

            await manager.get_client()
            await manager.close()

            assert manager._client is None
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_when_no_client(self, manager):
        """Test closing when no client exists."""
        await manager.close()  # Should not raise error

    @pytest.mark.asyncio
    async def test_close_handles_error(self, manager):
        """Test close handles errors gracefully."""
        with patch(
            "app.cache.qdrant_client.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_client.close.side_effect = Exception("Close failed")
            mock_create_client.return_value = mock_client

            await manager.get_client()
            await manager.close()

            # Client should be set to None even if close fails
            assert manager._client is None

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, manager):
        """Test health check when server is healthy."""
        with patch(
            "app.cache.qdrant_client.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_client.get_collections.return_value = MagicMock(collections=[])
            mock_create_client.return_value = mock_client

            is_healthy = await manager.health_check()

            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, manager):
        """Test health check when server is unhealthy."""
        with patch(
            "app.cache.qdrant_client.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_client.get_collections.side_effect = Exception("Connection failed")
            mock_create_client.return_value = mock_client

            is_healthy = await manager.health_check()

            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_reconnect_success(self, manager):
        """Test successful reconnection."""
        with patch(
            "app.cache.qdrant_client.create_qdrant_client"
        ) as mock_create_client:
            mock_client1 = AsyncMock()
            mock_client2 = AsyncMock()
            mock_create_client.side_effect = [mock_client1, mock_client2]

            # Initial connection
            client1 = await manager.get_client()
            assert client1 is mock_client1

            # Reconnect
            success = await manager.reconnect()

            assert success is True
            assert manager._client is mock_client2
            mock_client1.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_failure(self, manager):
        """Test reconnection failure."""
        with patch(
            "app.cache.qdrant_client.create_qdrant_client"
        ) as mock_create_client:
            mock_client = AsyncMock()
            mock_create_client.side_effect = [
                mock_client,
                ConnectionError("Connection failed"),
            ]

            # Initial connection
            await manager.get_client()

            # Reconnect fails
            success = await manager.reconnect()

            assert success is False
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_close_error(self, manager):
        """Test reconnection when close fails."""
        with patch(
            "app.cache.qdrant_client.create_qdrant_client"
        ) as mock_create_client:
            mock_client1 = AsyncMock()
            mock_client1.close.side_effect = Exception("Close failed")
            mock_client2 = AsyncMock()
            mock_create_client.side_effect = [mock_client1, mock_client2]

            # Initial connection
            await manager.get_client()

            # Reconnect (should handle close error)
            success = await manager.reconnect()

            assert success is True
            assert manager._client is mock_client2


class TestGetPooledClient:
    """Tests for get_pooled_client context manager."""

    @pytest.mark.asyncio
    async def test_get_pooled_client_success(self):
        """Test successful pooled client acquisition."""
        mock_client = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value = mock_client

        with patch("app.cache.qdrant_client.get_pool") as mock_get_pool:
            mock_get_pool.return_value = mock_pool

            async with get_pooled_client() as client:
                assert client is mock_client

            mock_pool.acquire.assert_called_once()
            mock_pool.release.assert_called_once_with(mock_client)

    @pytest.mark.asyncio
    async def test_get_pooled_client_releases_on_error(self):
        """Test pooled client is released even on error."""
        mock_client = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value = mock_client

        with patch("app.cache.qdrant_client.get_pool") as mock_get_pool:
            mock_get_pool.return_value = mock_pool

            with pytest.raises(ValueError, match="Test error"):
                async with get_pooled_client() as client:
                    raise ValueError("Test error")

            mock_pool.release.assert_called_once_with(mock_client)

    @pytest.mark.asyncio
    async def test_get_pooled_client_multiple_contexts(self):
        """Test multiple pooled client contexts."""
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.side_effect = [mock_client1, mock_client2]

        with patch("app.cache.qdrant_client.get_pool") as mock_get_pool:
            mock_get_pool.return_value = mock_pool

            async with get_pooled_client() as client1:
                assert client1 is mock_client1

            async with get_pooled_client() as client2:
                assert client2 is mock_client2

            assert mock_pool.acquire.call_count == 2
            assert mock_pool.release.call_count == 2
