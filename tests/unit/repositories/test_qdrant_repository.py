"""Unit tests for Qdrant repository."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.models import Distance, PointStruct, ScoredPoint

from app.models.qdrant_point import QdrantPoint, SearchResult
from app.repositories.qdrant_repository import QdrantRepository


@pytest.fixture
def mock_client():
    """Create mock Qdrant client."""
    client = AsyncMock()
    client.get_collections.return_value = MagicMock(collections=[])
    return client


@pytest.fixture
def repository(mock_client):
    """Create repository instance."""
    return QdrantRepository(mock_client)


class TestQdrantRepository:
    """Tests for QdrantRepository class."""

    @pytest.mark.asyncio
    async def test_collection_exists_true(self, mock_client):
        """Test collection_exists returns True when collection exists."""
        mock_collection = MagicMock()
        mock_collection.name = "test_cache"
        mock_client.get_collections.return_value = MagicMock(
            collections=[mock_collection]
        )

        with patch("app.repositories.qdrant_repository.config") as mock_config:
            mock_config.qdrant_collection_name = "test_cache"
            mock_config.qdrant_vector_size = 384
            repository = QdrantRepository(mock_client)
            result = await repository.collection_exists()

        assert result is True
        mock_client.get_collections.assert_called_once()

    @pytest.mark.asyncio
    async def test_collection_exists_false(self, repository, mock_client):
        """Test collection_exists returns False when collection doesn't exist."""
        mock_client.get_collections.return_value = MagicMock(collections=[])

        result = await repository.collection_exists()

        assert result is False

    @pytest.mark.asyncio
    async def test_collection_exists_error(self, repository, mock_client):
        """Test collection_exists handles errors gracefully."""
        mock_client.get_collections.side_effect = Exception("Connection failed")

        result = await repository.collection_exists()

        assert result is False

    @pytest.mark.asyncio
    async def test_create_collection_success(self, repository, mock_client):
        """Test successful collection creation."""
        mock_client.get_collections.return_value = MagicMock(collections=[])

        result = await repository.create_collection(distance=Distance.COSINE)

        assert result is True
        mock_client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_collection_already_exists(self, mock_client):
        """Test collection creation when already exists."""
        mock_collection = MagicMock()
        mock_collection.name = "test_cache"
        mock_client.get_collections.return_value = MagicMock(
            collections=[mock_collection]
        )

        with patch("app.repositories.qdrant_repository.config") as mock_config:
            mock_config.qdrant_collection_name = "test_cache"
            mock_config.qdrant_vector_size = 384
            repository = QdrantRepository(mock_client)
            result = await repository.create_collection()

        assert result is True
        mock_client.create_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_collection_success(self, repository, mock_client):
        """Test successful collection deletion."""
        result = await repository.delete_collection()

        assert result is True
        mock_client.delete_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_success(self, repository, mock_client):
        """Test successful ping."""
        with (
            patch("app.repositories.qdrant_repository.RetryPolicy"),
            patch("app.repositories.qdrant_repository.ErrorContext"),
        ):
            result = await repository.ping()

        assert result is True
        mock_client.get_collections.assert_called()

    @pytest.mark.asyncio
    async def test_store_point_success(self, repository, mock_client):
        """Test successful point storage."""
        point = QdrantPoint(
            id="test-123",
            vector=[0.1, 0.2, 0.3],
            payload={"query_hash": "abc123", "response": "test response"},
        )

        with (
            patch("app.repositories.qdrant_repository.RetryPolicy"),
            patch("app.repositories.qdrant_repository.ErrorContext"),
        ):
            result = await repository.store_point(point)

        assert result is True
        mock_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_points_success(self, repository, mock_client):
        """Test successful multiple points storage."""
        points = [
            QdrantPoint(
                id=f"test-{i}",
                vector=[0.1 * i, 0.2 * i, 0.3 * i],
                payload={"query_hash": f"hash{i}"},
            )
            for i in range(3)
        ]

        result = await repository.store_points(points)

        assert result == 3
        mock_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_points_empty(self, repository, mock_client):
        """Test storing empty points list."""
        result = await repository.store_points([])

        assert result == 0
        mock_client.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_similar_success(self, repository, mock_client):
        """Test successful similarity search."""
        query_vector = [0.1, 0.2, 0.3]
        mock_scored = ScoredPoint(
            id="test-123",
            version=1,
            score=0.95,
            payload={"query_hash": "abc123", "response": "test"},
            vector=[0.1, 0.2, 0.3],
        )
        mock_client.search.return_value = [mock_scored]

        results = await repository.search_similar(query_vector, limit=5)

        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].score == 0.95
        mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_similar_no_results(self, repository, mock_client):
        """Test similarity search with no results."""
        query_vector = [0.1, 0.2, 0.3]
        mock_client.search.return_value = []

        results = await repository.search_similar(query_vector)

        assert results == []

    @pytest.mark.asyncio
    async def test_get_point_success(self, repository, mock_client):
        """Test successful point retrieval by ID."""
        mock_point = PointStruct(
            id="test-123",
            vector=[0.1, 0.2, 0.3],
            payload={"query_hash": "abc123"},
        )
        mock_client.retrieve.return_value = [mock_point]

        point = await repository.get_point("test-123")

        assert point is not None
        assert point.id == "test-123"
        mock_client.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_point_not_found(self, repository, mock_client):
        """Test point retrieval when not found."""
        mock_client.retrieve.return_value = []

        point = await repository.get_point("nonexistent")

        assert point is None

    @pytest.mark.asyncio
    async def test_delete_point_success(self, repository, mock_client):
        """Test successful point deletion."""
        result = await repository.delete_point("test-123")

        assert result.success is True
        assert result.deleted_count == 1
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_points_success(self, repository, mock_client):
        """Test successful multiple points deletion."""
        point_ids = ["test-1", "test-2", "test-3"]

        result = await repository.delete_points(point_ids)

        assert result.success is True
        assert result.deleted_count == 3
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_points_success(self, repository, mock_client):
        """Test successful points counting."""
        mock_client.count.return_value = MagicMock(count=42)

        count = await repository.count_points()

        assert count == 42
        mock_client.count.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_points_error(self, repository, mock_client):
        """Test points counting handles errors."""
        mock_client.count.side_effect = Exception("Count failed")

        count = await repository.count_points()

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_collection_info_success(self, repository, mock_client):
        """Test successful collection info retrieval."""
        mock_info = MagicMock()
        mock_info.vectors_count = 100
        mock_info.points_count = 100
        mock_info.status = "green"
        mock_info.config.params.vectors = MagicMock()
        mock_info.config.params.vectors.distance = Distance.COSINE
        mock_client.get_collection.return_value = mock_info

        info = await repository.get_collection_info()

        assert info is not None
        assert info["vectors_count"] == 100
        assert info["points_count"] == 100
        assert info["status"] == "green"

    @pytest.mark.asyncio
    async def test_get_collection_info_error(self, repository, mock_client):
        """Test collection info retrieval handles errors."""
        mock_client.get_collection.side_effect = Exception("Get failed")

        info = await repository.get_collection_info()

        assert info is None

    @pytest.mark.asyncio
    async def test_point_exists_true(self, repository, mock_client):
        """Test point_exists returns True when point exists."""
        mock_point = PointStruct(id="test-123", vector=[0.1], payload={})
        mock_client.retrieve.return_value = [mock_point]

        exists = await repository.point_exists("test-123")

        assert exists is True

    @pytest.mark.asyncio
    async def test_point_exists_false(self, repository, mock_client):
        """Test point_exists returns False when point doesn't exist."""
        mock_client.retrieve.return_value = []

        exists = await repository.point_exists("nonexistent")

        assert exists is False

    @pytest.mark.asyncio
    async def test_point_exists_error(self, repository, mock_client):
        """Test point_exists handles errors."""
        mock_client.retrieve.side_effect = Exception("Retrieve failed")

        exists = await repository.point_exists("test-123")

        assert exists is False

    @pytest.mark.asyncio
    async def test_search_similar_with_vectors(self, repository, mock_client):
        """Test similarity search with vectors included."""
        query_vector = [0.1, 0.2, 0.3]
        mock_scored = ScoredPoint(
            id="test-123",
            version=1,
            score=0.95,
            payload={"query_hash": "abc123"},
            vector=[0.1, 0.2, 0.3],
        )
        mock_client.search.return_value = [mock_scored]

        results = await repository.search_similar_with_vectors(query_vector, limit=5)

        assert len(results) == 1
        assert results[0].vector is not None
        assert results[0].vector == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_search_similar_with_threshold(self, repository, mock_client):
        """Test similarity search with score threshold."""
        query_vector = [0.1, 0.2, 0.3]
        mock_client.search.return_value = []

        results = await repository.search_similar(
            query_vector, limit=5, score_threshold=0.9
        )

        assert results == []
        mock_client.search.assert_called_once_with(
            collection_name=repository._collection_name,
            query_vector=query_vector,
            limit=5,
            score_threshold=0.9,
            query_filter=None,
            with_payload=True,
            with_vectors=False,
        )

    @pytest.mark.asyncio
    async def test_batch_upload_success(self, repository, mock_client):
        """Test successful batch upload."""
        points = [
            QdrantPoint(
                id=f"test-{i}",
                vector=[0.1 * i, 0.2 * i, 0.3 * i],
                payload={"query_hash": f"hash{i}"},
            )
            for i in range(10)
        ]

        result = await repository.batch_upload(points, batch_size=5)

        assert result.total == 10
        assert result.successful == 10
        assert result.failed == 0
        assert len(result.point_ids) == 10
        assert result.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_batch_upload_empty(self, repository, mock_client):
        """Test batch upload with empty list."""
        result = await repository.batch_upload([])

        assert result.total == 0
        assert result.successful == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_batch_upload_partial_failure(self, repository, mock_client):
        """Test batch upload with partial failures."""
        points = [
            QdrantPoint(
                id=f"test-{i}",
                vector=[0.1 * i, 0.2 * i, 0.3 * i],
                payload={"query_hash": f"hash{i}"},
            )
            for i in range(10)
        ]

        # First batch succeeds, second fails
        mock_client.upsert.side_effect = [None, Exception("Upload failed")]

        result = await repository.batch_upload(points, batch_size=5)

        assert result.total == 10
        assert result.successful == 5
        assert result.failed == 5
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_batch_upload_with_retry_success(self, repository, mock_client):
        """Test batch upload with retry succeeds."""
        points = [
            QdrantPoint(
                id=f"test-{i}", vector=[0.1 * i], payload={"query_hash": f"hash{i}"}
            )
            for i in range(5)
        ]

        result = await repository.batch_upload_with_retry(points, batch_size=5)

        assert result.successful == 5
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_delete_points_empty(self, repository, mock_client):
        """Test deleting empty list of points."""
        result = await repository.delete_points([])

        assert result.success is True
        assert result.deleted_count == 0
        mock_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_by_filter_success(self, repository, mock_client):
        """Test successful deletion by filter."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        filter_obj = Filter(
            must=[FieldCondition(key="query_hash", match=MatchValue(value="abc123"))]
        )

        result = await repository.delete_by_filter(filter_obj)

        assert result.success is True
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_query_hash_success(self, repository, mock_client):
        """Test successful deletion by query hash."""
        result = await repository.delete_by_query_hash("abc123")

        assert result.success is True
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_point_payload_success(self, repository, mock_client):
        """Test successful payload update."""
        payload = {"new_field": "new_value"}

        result = await repository.update_point_payload("test-123", payload)

        assert result is True
        mock_client.set_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_point_payload_error(self, repository, mock_client):
        """Test payload update handles errors."""
        mock_client.set_payload.side_effect = Exception("Update failed")

        result = await repository.update_point_payload("test-123", {})

        assert result is False

    @pytest.mark.asyncio
    async def test_update_point_vector_success(self, repository, mock_client):
        """Test successful vector update."""
        new_vector = [0.5, 0.6, 0.7]

        result = await repository.update_point_vector("test-123", new_vector)

        assert result is True
        mock_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_point_vector_error(self, repository, mock_client):
        """Test vector update handles errors."""
        mock_client.upsert.side_effect = Exception("Update failed")

        result = await repository.update_point_vector("test-123", [0.1, 0.2])

        assert result is False

    @pytest.mark.asyncio
    async def test_update_point_success(self, repository, mock_client):
        """Test successful complete point update."""
        point = QdrantPoint(
            id="test-123", vector=[0.1, 0.2, 0.3], payload={"updated": True}
        )

        result = await repository.update_point(point)

        assert result is True
        mock_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_point_error(self, repository, mock_client):
        """Test point update handles errors."""
        point = QdrantPoint(id="test-123", vector=[0.1, 0.2], payload={})
        mock_client.upsert.side_effect = Exception("Update failed")

        result = await repository.update_point(point)

        assert result is False

    @pytest.mark.asyncio
    async def test_partial_update_payload_success(self, repository, mock_client):
        """Test successful partial payload update."""
        updates = {"field1": "value1", "field2": "value2"}

        result = await repository.partial_update_payload("test-123", updates)

        assert result is True
        mock_client.set_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_update_payload_error(self, repository, mock_client):
        """Test partial payload update handles errors."""
        mock_client.set_payload.side_effect = Exception("Update failed")

        result = await repository.partial_update_payload("test-123", {"field": "value"})

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_payload_fields_success(self, repository, mock_client):
        """Test successful payload fields deletion."""
        fields = ["field1", "field2"]

        result = await repository.delete_payload_fields("test-123", fields)

        assert result is True
        mock_client.delete_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_payload_fields_error(self, repository, mock_client):
        """Test payload fields deletion handles errors."""
        mock_client.delete_payload.side_effect = Exception("Delete failed")

        result = await repository.delete_payload_fields("test-123", ["field1"])

        assert result is False

    @pytest.mark.asyncio
    async def test_scroll_points_success(self, repository, mock_client):
        """Test successful scroll pagination."""
        mock_point = PointStruct(
            id="test-123", vector=[0.1, 0.2], payload={"data": "test"}
        )
        mock_client.scroll.return_value = ([mock_point], "next_offset")

        points, next_offset = await repository.scroll_points(limit=10)

        assert len(points) == 1
        assert next_offset == "next_offset"
        assert points[0].id == "test-123"

    @pytest.mark.asyncio
    async def test_scroll_points_no_vectors(self, repository, mock_client):
        """Test scroll without vectors."""
        mock_point = PointStruct(id="test-123", vector=None, payload={"data": "test"})
        mock_client.scroll.return_value = ([mock_point], None)

        points, next_offset = await repository.scroll_points(
            limit=10, with_vectors=False
        )

        assert len(points) == 1
        assert next_offset is None

    @pytest.mark.asyncio
    async def test_scroll_points_error(self, repository, mock_client):
        """Test scroll handles errors."""
        mock_client.scroll.side_effect = Exception("Scroll failed")

        points, next_offset = await repository.scroll_points()

        assert points == []
        assert next_offset is None

    @pytest.mark.asyncio
    async def test_get_all_points_success(self, repository, mock_client):
        """Test getting all points with pagination."""
        # Simulate two pages of results
        mock_point1 = PointStruct(id="test-1", vector=[0.1], payload={})
        mock_point2 = PointStruct(id="test-2", vector=[0.2], payload={})

        mock_client.scroll.side_effect = [
            ([mock_point1], "offset1"),
            ([mock_point2], None),
        ]

        all_points = await repository.get_all_points(batch_size=1)

        assert len(all_points) == 2
        assert all_points[0].id == "test-1"
        assert all_points[1].id == "test-2"

    @pytest.mark.asyncio
    async def test_get_all_points_error(self, repository, mock_client):
        """Test get all points handles errors gracefully."""
        mock_client.scroll.side_effect = Exception("Scroll failed")

        all_points = await repository.get_all_points()

        assert all_points == []

    @pytest.mark.asyncio
    async def test_count_points_with_filter(self, repository, mock_client):
        """Test counting points with filter."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        filter_obj = Filter(
            must=[FieldCondition(key="query_hash", match=MatchValue(value="abc123"))]
        )
        mock_client.count.return_value = MagicMock(count=5)

        count = await repository.count_points(filter_condition=filter_obj)

        assert count == 5
        mock_client.count.assert_called_once_with(
            collection_name=repository._collection_name,
            count_filter=filter_obj,
            exact=True,
        )

    @pytest.mark.asyncio
    async def test_delete_point_error(self, repository, mock_client):
        """Test delete point handles errors."""
        mock_client.delete.side_effect = Exception("Delete failed")

        result = await repository.delete_point("test-123")

        assert result.success is False
        assert result.deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_points_error(self, repository, mock_client):
        """Test delete points handles errors."""
        mock_client.delete.side_effect = Exception("Delete failed")

        result = await repository.delete_points(["test-1", "test-2"])

        assert result.success is False
        assert result.deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_by_filter_error(self, repository, mock_client):
        """Test delete by filter handles errors."""
        from qdrant_client.models import Filter

        mock_client.delete.side_effect = Exception("Delete failed")

        result = await repository.delete_by_filter(Filter())

        assert result.success is False

    @pytest.mark.asyncio
    async def test_create_collection_error(self, repository, mock_client):
        """Test create collection handles errors."""
        mock_client.get_collections.side_effect = Exception("Check failed")

        result = await repository.create_collection()

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_collection_error(self, repository, mock_client):
        """Test delete collection handles errors."""
        mock_client.delete_collection.side_effect = Exception("Delete failed")

        result = await repository.delete_collection()

        assert result is False
