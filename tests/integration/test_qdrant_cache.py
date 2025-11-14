"""
Integration tests for Qdrant cache.

These tests require a running Qdrant instance.
"""

import pytest
import pytest_asyncio
from qdrant_client.models import Distance

from app.cache.qdrant_client import create_qdrant_client
from app.models.qdrant_point import QdrantPoint
from app.repositories.qdrant_repository import QdrantRepository


@pytest_asyncio.fixture
async def qdrant_client():
    """Create Qdrant client for testing."""
    client = await create_qdrant_client()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def qdrant_repository(qdrant_client):
    """Create Qdrant repository for testing."""
    repository = QdrantRepository(qdrant_client)

    # Ensure collection exists
    await repository.create_collection(distance=Distance.COSINE)

    yield repository

    # Clean up: delete all points after tests
    try:
        await repository.delete_collection()
        await repository.create_collection(distance=Distance.COSINE)
    except Exception:
        pass


@pytest.fixture
def sample_point():
    """Create sample Qdrant point."""
    return QdrantPoint(
        id="test_integration_001",
        vector=[0.1, 0.2, 0.3, 0.4, 0.5] * 77,  # 385 dims (close to 384)
        payload={
            "query_hash": "test_integration_hash",
            "query": "What is integration testing?",
            "response": "Integration testing tests the complete flow",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
        },
    )


@pytest.mark.integration
class TestQdrantIntegration:
    """Integration tests for Qdrant operations."""

    @pytest.mark.asyncio
    async def test_collection_creation(self, qdrant_repository):
        """Test collection creation."""
        exists = await qdrant_repository.collection_exists()
        assert exists is True

    @pytest.mark.asyncio
    async def test_store_and_retrieve_point(self, qdrant_repository, sample_point):
        """Test storing and retrieving a point."""
        # Store point
        result = await qdrant_repository.store_point(sample_point)
        assert result is True

        # Retrieve point
        retrieved = await qdrant_repository.get_point(sample_point.id)
        assert retrieved is not None
        assert retrieved.id == sample_point.id
        assert retrieved.payload["query_hash"] == "test_integration_hash"

    @pytest.mark.asyncio
    async def test_batch_store_points(self, qdrant_repository):
        """Test batch storing multiple points."""
        points = [
            QdrantPoint(
                id=f"test_batch_{i}",
                vector=[0.1 * i, 0.2 * i, 0.3 * i, 0.4 * i, 0.5 * i] * 77,
                payload={
                    "query_hash": f"hash_{i}",
                    "index": i,
                },
            )
            for i in range(5)
        ]

        count = await qdrant_repository.store_points(points)
        assert count == 5

        # Verify all points were stored
        for point in points:
            retrieved = await qdrant_repository.get_point(point.id)
            assert retrieved is not None

    @pytest.mark.asyncio
    async def test_similarity_search(self, qdrant_repository):
        """Test similarity search."""
        # Store multiple points with similar vectors
        points = [
            QdrantPoint(
                id=f"test_search_{i}",
                vector=[0.1 + i * 0.01] * 385,
                payload={"index": i},
            )
            for i in range(3)
        ]
        await qdrant_repository.store_points(points)

        # Search for similar points
        query_vector = [0.1] * 385
        results = await qdrant_repository.search_similar(query_vector, limit=2)

        assert len(results) > 0
        assert results[0].score > 0.8  # High similarity expected

    @pytest.mark.asyncio
    async def test_delete_point(self, qdrant_repository, sample_point):
        """Test point deletion."""
        # Store point
        await qdrant_repository.store_point(sample_point)

        # Delete point
        result = await qdrant_repository.delete_point(sample_point.id)
        assert result.success is True
        assert result.deleted_count == 1

        # Verify point is deleted
        retrieved = await qdrant_repository.get_point(sample_point.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_count_points(self, qdrant_repository):
        """Test counting points in collection."""
        # Store some points
        points = [
            QdrantPoint(
                id=f"test_count_{i}",
                vector=[0.1] * 385,
                payload={"index": i},
            )
            for i in range(3)
        ]
        await qdrant_repository.store_points(points)

        # Count points
        count = await qdrant_repository.count_points()
        assert count >= 3

    @pytest.mark.asyncio
    async def test_pagination(self, qdrant_repository):
        """Test pagination of points."""
        # Store multiple points
        points = [
            QdrantPoint(
                id=f"test_page_{i}",
                vector=[0.1] * 385,
                payload={"index": i},
            )
            for i in range(10)
        ]
        await qdrant_repository.store_points(points)

        # Get first page
        page1, offset1 = await qdrant_repository.scroll_points(
            limit=5, with_vectors=False
        )
        assert len(page1) == 5

        # Get second page
        if offset1:
            page2, offset2 = await qdrant_repository.scroll_points(
                limit=5, offset=str(offset1), with_vectors=False
            )
            assert len(page2) <= 5

    @pytest.mark.asyncio
    async def test_update_point(self, qdrant_repository, sample_point):
        """Test updating point payload."""
        # Store original point
        await qdrant_repository.store_point(sample_point)

        # Update payload
        new_payload = {
            **sample_point.payload,
            "updated": True,
            "new_field": "new_value",
        }
        result = await qdrant_repository.update_point(sample_point.id, new_payload)
        assert result is True

        # Verify update
        retrieved = await qdrant_repository.get_point(sample_point.id)
        assert retrieved is not None
        assert retrieved.payload.get("updated") is True
        assert retrieved.payload.get("new_field") == "new_value"

    @pytest.mark.asyncio
    async def test_filter_search(self, qdrant_repository):
        """Test search with filters."""
        from app.cache.qdrant_filter import create_filter

        # Store points with different providers
        points = [
            QdrantPoint(
                id=f"test_filter_{i}",
                vector=[0.1] * 385,
                payload={
                    "provider": "openai" if i % 2 == 0 else "anthropic",
                    "index": i,
                },
            )
            for i in range(4)
        ]
        await qdrant_repository.store_points(points)

        # Search with filter
        query_vector = [0.1] * 385
        filter_builder = create_filter().with_provider("openai")

        results = await qdrant_repository.search_similar(
            query_vector,
            limit=10,
            filter_condition=filter_builder.build(),
        )

        # All results should be from openai
        assert len(results) > 0
        for result in results:
            assert result.payload.get("provider") == "openai"

    @pytest.mark.asyncio
    async def test_connection_health(self, qdrant_repository):
        """Test connection health check."""
        result = await qdrant_repository.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_collection_info(self, qdrant_repository):
        """Test getting collection information."""
        info = await qdrant_repository.get_collection_info()
        assert info is not None
        assert "vectors_count" in info
        assert "points_count" in info
        assert "status" in info
