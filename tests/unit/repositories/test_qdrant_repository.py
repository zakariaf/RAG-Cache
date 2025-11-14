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
    async def test_collection_exists_true(self, repository, mock_client):
        """Test collection_exists returns True when collection exists."""
        mock_collection = MagicMock()
        mock_collection.name = "test_cache"
        mock_client.get_collections.return_value = MagicMock(
            collections=[mock_collection]
        )

        with patch("app.repositories.qdrant_repository.config") as mock_config:
            mock_config.qdrant_collection_name = "test_cache"
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
    async def test_create_collection_already_exists(self, repository, mock_client):
        """Test collection creation when already exists."""
        mock_collection = MagicMock()
        mock_collection.name = "test_cache"
        mock_client.get_collections.return_value = MagicMock(
            collections=[mock_collection]
        )

        with patch("app.repositories.qdrant_repository.config") as mock_config:
            mock_config.qdrant_collection_name = "test_cache"
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
    async def test_get_point_by_id_success(self, repository, mock_client):
        """Test successful point retrieval by ID."""
        mock_point = PointStruct(
            id="test-123",
            vector=[0.1, 0.2, 0.3],
            payload={"query_hash": "abc123"},
        )
        mock_client.retrieve.return_value = [mock_point]

        point = await repository.get_point_by_id("test-123")

        assert point is not None
        assert point.id == "test-123"
        mock_client.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_point_by_id_not_found(self, repository, mock_client):
        """Test point retrieval when not found."""
        mock_client.retrieve.return_value = []

        point = await repository.get_point_by_id("nonexistent")

        assert point is None

    @pytest.mark.asyncio
    async def test_delete_point_success(self, repository, mock_client):
        """Test successful point deletion."""
        result = await repository.delete_point("test-123")

        assert result is True
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_points_success(self, repository, mock_client):
        """Test successful multiple points deletion."""
        point_ids = ["test-1", "test-2", "test-3"]

        result = await repository.delete_points(point_ids)

        assert result == 3
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
