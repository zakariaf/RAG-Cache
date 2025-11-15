"""Unit tests for Qdrant collection manager."""

from unittest.mock import AsyncMock

import pytest
from qdrant_client.models import Distance

from app.cache.qdrant_collection import QdrantCollectionManager


class TestQdrantCollectionManager:
    """Tests for QdrantCollectionManager class."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        return AsyncMock()

    @pytest.fixture
    def manager(self, mock_repository):
        """Create collection manager."""
        return QdrantCollectionManager(mock_repository)

    @pytest.mark.asyncio
    async def test_manager_init(self, manager, mock_repository):
        """Test manager initialization."""
        assert manager._repository is mock_repository

    @pytest.mark.asyncio
    async def test_initialize_creates_new_collection(self, manager, mock_repository):
        """Test initialize creates collection when it doesn't exist."""
        mock_repository.collection_exists.return_value = False
        mock_repository.create_collection.return_value = True

        result = await manager.initialize()

        assert result is True
        mock_repository.collection_exists.assert_called_once()
        mock_repository.create_collection.assert_called_once_with(Distance.COSINE)

    @pytest.mark.asyncio
    async def test_initialize_with_existing_collection(self, manager, mock_repository):
        """Test initialize with existing collection."""
        mock_repository.collection_exists.return_value = True

        result = await manager.initialize()

        assert result is True
        mock_repository.collection_exists.assert_called_once()
        mock_repository.create_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_with_recreate(self, manager, mock_repository):
        """Test initialize with recreate flag."""
        mock_repository.collection_exists.return_value = True
        mock_repository.delete_collection.return_value = True
        mock_repository.create_collection.return_value = True

        result = await manager.initialize(recreate=True)

        assert result is True
        mock_repository.delete_collection.assert_called_once()
        mock_repository.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_with_custom_distance(self, manager, mock_repository):
        """Test initialize with custom distance metric."""
        mock_repository.collection_exists.return_value = False
        mock_repository.create_collection.return_value = True

        result = await manager.initialize(distance=Distance.EUCLID)

        assert result is True
        mock_repository.create_collection.assert_called_once_with(Distance.EUCLID)

    @pytest.mark.asyncio
    async def test_initialize_handles_error(self, manager, mock_repository):
        """Test initialize handles errors gracefully."""
        mock_repository.collection_exists.side_effect = Exception("Connection failed")

        result = await manager.initialize()

        assert result is False

    @pytest.mark.asyncio
    async def test_recreate_deletes_existing_collection(self, manager, mock_repository):
        """Test recreate deletes existing collection."""
        mock_repository.collection_exists.return_value = True
        mock_repository.delete_collection.return_value = True
        mock_repository.create_collection.return_value = True

        result = await manager._recreate_collection(Distance.COSINE)

        assert result is True
        mock_repository.delete_collection.assert_called_once()
        mock_repository.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_recreate_skips_delete_when_not_exists(
        self, manager, mock_repository
    ):
        """Test recreate skips delete when collection doesn't exist."""
        mock_repository.collection_exists.return_value = False
        mock_repository.create_collection.return_value = True

        result = await manager._recreate_collection(Distance.COSINE)

        assert result is True
        mock_repository.delete_collection.assert_not_called()
        mock_repository.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_collection_exists_creates_when_missing(
        self, manager, mock_repository
    ):
        """Test ensure collection creates when missing."""
        mock_repository.collection_exists.return_value = False
        mock_repository.create_collection.return_value = True

        result = await manager._ensure_collection_exists(Distance.COSINE)

        assert result is True
        mock_repository.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_collection_exists_verifies_when_present(
        self, manager, mock_repository
    ):
        """Test ensure collection verifies when present."""
        mock_repository.collection_exists.return_value = True

        result = await manager._ensure_collection_exists(Distance.COSINE)

        assert result is True
        mock_repository.create_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_collection_all_checks_pass(self, manager, mock_repository):
        """Test validate collection when all checks pass."""
        mock_repository.collection_exists.return_value = True
        mock_repository.ping.return_value = True
        mock_repository.get_collection_info.return_value = {"status": "green"}

        result = await manager.validate_collection()

        assert result["exists"] is True
        assert result["accessible"] is True
        assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_validate_collection_not_exists(self, manager, mock_repository):
        """Test validate collection when collection doesn't exist."""
        mock_repository.collection_exists.return_value = False

        result = await manager.validate_collection()

        assert result["exists"] is False
        assert result["accessible"] is False
        assert result["configured"] is False

    @pytest.mark.asyncio
    async def test_validate_collection_not_accessible(self, manager, mock_repository):
        """Test validate collection when not accessible."""
        mock_repository.collection_exists.return_value = True
        mock_repository.ping.return_value = False

        result = await manager.validate_collection()

        assert result["exists"] is True
        assert result["accessible"] is False
        assert result["configured"] is False

    @pytest.mark.asyncio
    async def test_validate_collection_not_configured(self, manager, mock_repository):
        """Test validate collection when not properly configured."""
        mock_repository.collection_exists.return_value = True
        mock_repository.ping.return_value = True
        mock_repository.get_collection_info.return_value = None

        result = await manager.validate_collection()

        assert result["exists"] is True
        assert result["accessible"] is True
        assert result["configured"] is False

    @pytest.mark.asyncio
    async def test_validate_collection_handles_error(self, manager, mock_repository):
        """Test validate collection handles errors."""
        mock_repository.collection_exists.side_effect = Exception("Error")

        result = await manager.validate_collection()

        assert result["exists"] is False
        assert result["accessible"] is False
        assert result["configured"] is False

    @pytest.mark.asyncio
    async def test_get_status_not_initialized(self, manager, mock_repository):
        """Test get status when collection not initialized."""
        mock_repository.collection_exists.return_value = False

        status = await manager.get_status()

        assert status is not None
        assert status["status"] == "not_initialized"
        assert "message" in status

    @pytest.mark.asyncio
    async def test_get_status_error_getting_info(self, manager, mock_repository):
        """Test get status when error getting collection info."""
        mock_repository.collection_exists.return_value = True
        mock_repository.ping.return_value = True
        mock_repository.get_collection_info.return_value = None

        status = await manager.get_status()

        assert status is not None
        assert status["status"] == "error"
        assert "message" in status

    @pytest.mark.asyncio
    async def test_get_status_ready(self, manager, mock_repository):
        """Test get status when collection is ready."""
        mock_repository.collection_exists.return_value = True
        mock_repository.ping.return_value = True
        mock_repository.get_collection_info.return_value = {
            "vectors_count": 100,
            "points_count": 100,
            "status": "green",
            "config": {"vector_size": 384},
        }

        status = await manager.get_status()

        assert status is not None
        assert status["status"] == "ready"
        assert status["vectors_count"] == 100
        assert status["points_count"] == 100
        assert status["collection_status"] == "green"
        assert "config" in status

    @pytest.mark.asyncio
    async def test_get_status_handles_exception(self, manager, mock_repository):
        """Test get status handles exceptions."""
        mock_repository.collection_exists.side_effect = Exception("Connection error")

        status = await manager.get_status()

        assert status is not None
        assert status["status"] == "error"
        assert "message" in status
