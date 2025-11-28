"""Unit tests for Qdrant Repository."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from qdrant_client.models import Distance, VectorParams

from app.repositories.qdrant_repository import QdrantRepository
from app.models.qdrant_point import (
    QdrantPoint,
    SearchResult,
    BatchUploadResult,
    DeleteResult,
)


@pytest.fixture
def mock_qdrant_client():
    """Create mock Qdrant client."""
    client = MagicMock()
    client.get_collections = AsyncMock()
    client.create_collection = AsyncMock()
    client.delete_collection = AsyncMock()
    client.get_collection = AsyncMock()
    client.upsert = AsyncMock()
    client.retrieve = AsyncMock()
    client.search = AsyncMock()
    client.delete = AsyncMock()
    client.set_payload = AsyncMock()
    client.delete_payload = AsyncMock()
    client.scroll = AsyncMock()
    client.count = AsyncMock()
    return client


@pytest.fixture
def repository(mock_qdrant_client):
    """Create repository with mocked client."""
    return QdrantRepository(mock_qdrant_client)


@pytest.fixture
def sample_point():
    """Create sample QdrantPoint."""
    return QdrantPoint(
        id="test-id-123",
        vector=[0.1, 0.2, 0.3] * 128,  # 384 dimensions
        payload={
            "query_hash": "hash123",
            "original_query": "test query",
            "response": "test response",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
        },
    )


class TestQdrantRepositoryCollection:
    """Tests for collection operations."""

    @pytest.mark.asyncio
    async def test_collection_exists_true(self, repository, mock_qdrant_client):
        """Test collection_exists returns True when collection exists."""
        mock_collection = MagicMock()
        mock_collection.name = "ragcache"
        mock_qdrant_client.get_collections.return_value = MagicMock(
            collections=[mock_collection]
        )

        with patch.object(repository, "_collection_name", "ragcache"):
            result = await repository.collection_exists()

        assert result is True

    @pytest.mark.asyncio
    async def test_collection_exists_false(self, repository, mock_qdrant_client):
        """Test collection_exists returns False when collection doesn't exist."""
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])

        result = await repository.collection_exists()

        assert result is False

    @pytest.mark.asyncio
    async def test_collection_exists_error(self, repository, mock_qdrant_client):
        """Test collection_exists handles errors gracefully."""
        mock_qdrant_client.get_collections.side_effect = Exception("Connection error")

        result = await repository.collection_exists()

        assert result is False

    @pytest.mark.asyncio
    async def test_create_collection_success(self, repository, mock_qdrant_client):
        """Test create_collection creates new collection."""
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.create_collection.return_value = None

        result = await repository.create_collection()

        assert result is True
        mock_qdrant_client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_collection_already_exists(
        self, repository, mock_qdrant_client
    ):
        """Test create_collection returns True if collection exists."""
        mock_collection = MagicMock()
        mock_collection.name = repository._collection_name
        mock_qdrant_client.get_collections.return_value = MagicMock(
            collections=[mock_collection]
        )

        result = await repository.create_collection()

        assert result is True
        mock_qdrant_client.create_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_collection_success(self, repository, mock_qdrant_client):
        """Test delete_collection deletes collection."""
        mock_qdrant_client.delete_collection.return_value = None

        result = await repository.delete_collection()

        assert result is True
        mock_qdrant_client.delete_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_collection_error(self, repository, mock_qdrant_client):
        """Test delete_collection handles errors."""
        mock_qdrant_client.delete_collection.side_effect = Exception("Delete error")

        result = await repository.delete_collection()

        assert result is False


class TestQdrantRepositoryPing:
    """Tests for ping operation."""

    @pytest.mark.asyncio
    async def test_ping_success(self, repository, mock_qdrant_client):
        """Test ping returns True when connected."""
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])

        result = await repository.ping()

        assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self, repository, mock_qdrant_client):
        """Test ping returns False when connection fails."""
        mock_qdrant_client.get_collections.side_effect = Exception("Connection refused")

        result = await repository.ping()

        assert result is False


class TestQdrantRepositoryStorePoint:
    """Tests for store_point operation."""

    @pytest.mark.asyncio
    async def test_store_point_success(
        self, repository, mock_qdrant_client, sample_point
    ):
        """Test store_point stores point successfully."""
        mock_qdrant_client.upsert.return_value = None

        result = await repository.store_point(sample_point)

        assert result is True
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_point_failure(
        self, repository, mock_qdrant_client, sample_point
    ):
        """Test store_point handles errors."""
        mock_qdrant_client.upsert.side_effect = Exception("Upsert failed")

        result = await repository.store_point(sample_point)

        assert result is False

    @pytest.mark.asyncio
    async def test_store_points_batch(
        self, repository, mock_qdrant_client, sample_point
    ):
        """Test store_points stores multiple points."""
        mock_qdrant_client.upsert.return_value = None
        points = [sample_point, sample_point]

        result = await repository.store_points(points)

        assert result == 2
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_points_empty(self, repository):
        """Test store_points handles empty list."""
        result = await repository.store_points([])

        assert result == 0


class TestQdrantRepositoryPointExists:
    """Tests for point_exists operation."""

    @pytest.mark.asyncio
    async def test_point_exists_true(self, repository, mock_qdrant_client):
        """Test point_exists returns True when point exists."""
        mock_point = MagicMock()
        mock_qdrant_client.retrieve.return_value = [mock_point]

        result = await repository.point_exists("test-id")

        assert result is True

    @pytest.mark.asyncio
    async def test_point_exists_false(self, repository, mock_qdrant_client):
        """Test point_exists returns False when point doesn't exist."""
        mock_qdrant_client.retrieve.return_value = []

        result = await repository.point_exists("test-id")

        assert result is False

    @pytest.mark.asyncio
    async def test_point_exists_error(self, repository, mock_qdrant_client):
        """Test point_exists handles errors."""
        mock_qdrant_client.retrieve.side_effect = Exception("Retrieve error")

        result = await repository.point_exists("test-id")

        assert result is False


class TestQdrantRepositoryGetPoint:
    """Tests for get_point operation."""

    @pytest.mark.asyncio
    async def test_get_point_success(self, repository, mock_qdrant_client):
        """Test get_point retrieves point."""
        mock_point = MagicMock()
        mock_point.id = "test-id"
        mock_point.vector = [0.1, 0.2, 0.3]
        mock_point.payload = {"key": "value"}
        mock_qdrant_client.retrieve.return_value = [mock_point]

        result = await repository.get_point("test-id")

        assert result is not None
        assert result.id == "test-id"
        assert result.payload["key"] == "value"

    @pytest.mark.asyncio
    async def test_get_point_not_found(self, repository, mock_qdrant_client):
        """Test get_point returns None when not found."""
        mock_qdrant_client.retrieve.return_value = []

        result = await repository.get_point("nonexistent")

        assert result is None


class TestQdrantRepositorySearch:
    """Tests for search operations."""

    @pytest.mark.asyncio
    async def test_search_similar_success(self, repository, mock_qdrant_client):
        """Test search_similar finds similar vectors."""
        mock_result = MagicMock()
        mock_result.id = "result-id"
        mock_result.score = 0.95
        mock_result.vector = None
        mock_result.payload = {"query_hash": "hash123"}
        mock_qdrant_client.search.return_value = [mock_result]

        results = await repository.search_similar([0.1, 0.2, 0.3], limit=5)

        assert len(results) == 1
        assert results[0].point_id == "result-id"
        assert results[0].score == 0.95

    @pytest.mark.asyncio
    async def test_search_similar_with_threshold(self, repository, mock_qdrant_client):
        """Test search_similar with score threshold."""
        mock_qdrant_client.search.return_value = []

        results = await repository.search_similar(
            [0.1, 0.2, 0.3], limit=5, score_threshold=0.8
        )

        assert len(results) == 0
        mock_qdrant_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_similar_error(self, repository, mock_qdrant_client):
        """Test search_similar handles errors."""
        mock_qdrant_client.search.side_effect = Exception("Search error")

        results = await repository.search_similar([0.1, 0.2, 0.3])

        assert len(results) == 0


class TestQdrantRepositoryDelete:
    """Tests for delete operations."""

    @pytest.mark.asyncio
    async def test_delete_point_success(self, repository, mock_qdrant_client):
        """Test delete_point deletes point."""
        mock_qdrant_client.delete.return_value = None

        result = await repository.delete_point("test-id")

        assert result.success is True
        assert result.deleted_count == 1

    @pytest.mark.asyncio
    async def test_delete_point_error(self, repository, mock_qdrant_client):
        """Test delete_point handles errors."""
        mock_qdrant_client.delete.side_effect = Exception("Delete error")

        result = await repository.delete_point("test-id")

        assert result.success is False
        assert result.deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_points_batch(self, repository, mock_qdrant_client):
        """Test delete_points deletes multiple points."""
        mock_qdrant_client.delete.return_value = None

        result = await repository.delete_points(["id1", "id2", "id3"])

        assert result.success is True
        assert result.deleted_count == 3

    @pytest.mark.asyncio
    async def test_delete_points_empty(self, repository, mock_qdrant_client):
        """Test delete_points handles empty list."""
        result = await repository.delete_points([])

        assert result.success is True
        assert result.deleted_count == 0


class TestQdrantRepositoryUpdate:
    """Tests for update operations."""

    @pytest.mark.asyncio
    async def test_update_point_payload(self, repository, mock_qdrant_client):
        """Test update_point_payload updates payload."""
        mock_qdrant_client.set_payload.return_value = None

        result = await repository.update_point_payload("test-id", {"key": "new_value"})

        assert result is True
        mock_qdrant_client.set_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_point_payload_error(self, repository, mock_qdrant_client):
        """Test update_point_payload handles errors."""
        mock_qdrant_client.set_payload.side_effect = Exception("Update error")

        result = await repository.update_point_payload("test-id", {"key": "value"})

        assert result is False

    @pytest.mark.asyncio
    async def test_update_point_complete(
        self, repository, mock_qdrant_client, sample_point
    ):
        """Test update_point updates complete point."""
        mock_qdrant_client.upsert.return_value = None

        result = await repository.update_point(sample_point)

        assert result is True
        mock_qdrant_client.upsert.assert_called_once()


class TestQdrantRepositoryBatchUpload:
    """Tests for batch upload operations."""

    @pytest.mark.asyncio
    async def test_batch_upload_success(
        self, repository, mock_qdrant_client, sample_point
    ):
        """Test batch_upload uploads points in batches."""
        mock_qdrant_client.upsert.return_value = None
        points = [sample_point] * 5

        result = await repository.batch_upload(points, batch_size=2)

        assert result.total == 5
        assert result.successful == 5
        assert result.failed == 0
        assert result.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_batch_upload_empty(self, repository):
        """Test batch_upload handles empty list."""
        result = await repository.batch_upload([])

        assert result.total == 0
        assert result.successful == 0

    @pytest.mark.asyncio
    async def test_batch_upload_partial_failure(
        self, repository, mock_qdrant_client, sample_point
    ):
        """Test batch_upload handles partial failures."""
        # First batch succeeds, second fails
        mock_qdrant_client.upsert.side_effect = [None, Exception("Batch failed")]
        points = [sample_point] * 4

        result = await repository.batch_upload(points, batch_size=2)

        assert result.total == 4
        assert result.successful == 2
        assert result.failed == 2
        assert result.has_failures is True


class TestQdrantRepositoryScroll:
    """Tests for scroll/pagination operations."""

    @pytest.mark.asyncio
    async def test_scroll_points(self, repository, mock_qdrant_client):
        """Test scroll_points returns paginated results."""
        mock_point = MagicMock()
        mock_point.id = "point-1"
        mock_point.vector = [0.1, 0.2]
        mock_point.payload = {"key": "value"}
        mock_qdrant_client.scroll.return_value = ([mock_point], "next-offset")

        points, next_offset = await repository.scroll_points(limit=10)

        assert len(points) == 1
        assert next_offset == "next-offset"

    @pytest.mark.asyncio
    async def test_scroll_points_no_more(self, repository, mock_qdrant_client):
        """Test scroll_points returns None offset when done."""
        mock_qdrant_client.scroll.return_value = ([], None)

        points, next_offset = await repository.scroll_points()

        assert len(points) == 0
        assert next_offset is None

    @pytest.mark.asyncio
    async def test_count_points(self, repository, mock_qdrant_client):
        """Test count_points returns count."""
        mock_qdrant_client.count.return_value = MagicMock(count=42)

        count = await repository.count_points()

        assert count == 42

    @pytest.mark.asyncio
    async def test_count_points_error(self, repository, mock_qdrant_client):
        """Test count_points handles errors."""
        mock_qdrant_client.count.side_effect = Exception("Count error")

        count = await repository.count_points()

        assert count == 0


class TestQdrantRepositoryGetCollectionInfo:
    """Tests for get_collection_info."""

    @pytest.mark.asyncio
    async def test_get_collection_info_success(self, repository, mock_qdrant_client):
        """Test get_collection_info returns info dict."""
        mock_info = MagicMock()
        mock_info.vectors_count = 100
        mock_info.points_count = 100
        mock_info.status = "green"
        mock_info.config.params.vectors = VectorParams(
            size=384, distance=Distance.COSINE
        )
        mock_qdrant_client.get_collection.return_value = mock_info

        info = await repository.get_collection_info()

        assert info is not None
        assert info["vectors_count"] == 100
        assert info["points_count"] == 100
        assert info["status"] == "green"

    @pytest.mark.asyncio
    async def test_get_collection_info_error(self, repository, mock_qdrant_client):
        """Test get_collection_info handles errors."""
        mock_qdrant_client.get_collection.side_effect = Exception("Get info error")

        info = await repository.get_collection_info()

        assert info is None
