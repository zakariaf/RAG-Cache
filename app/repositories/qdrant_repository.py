"""
Qdrant repository for vector storage and search.

Sandi Metz Principles:
- Single Responsibility: Qdrant data access
- Small methods: Each operation isolated
- Dependency Injection: Client injected
"""

from typing import Dict, List, Optional
from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import config
from app.models.qdrant_point import QdrantPoint
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QdrantRepository:
    """
    Repository for Qdrant vector operations.

    Handles low-level Qdrant interactions.
    """

    def __init__(self, client: AsyncQdrantClient):
        """
        Initialize repository.

        Args:
            client: Qdrant async client
        """
        self._client = client
        self._collection_name = config.qdrant_collection_name
        self._vector_size = config.qdrant_vector_size

    async def collection_exists(self) -> bool:
        """
        Check if collection exists.

        Returns:
            True if exists, False otherwise
        """
        try:
            collections = await self._client.get_collections()
            return any(
                col.name == self._collection_name for col in collections.collections
            )
        except Exception as e:
            logger.error("Collection check failed", error=str(e))
            return False

    async def create_collection(
        self, distance: Distance = Distance.COSINE
    ) -> bool:
        """
        Create collection if not exists.

        Args:
            distance: Distance metric (COSINE, EUCLID, DOT)

        Returns:
            True if created or exists, False on error
        """
        try:
            exists = await self.collection_exists()
            if exists:
                logger.info("Collection already exists", name=self._collection_name)
                return True

            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=self._vector_size, distance=distance
                ),
            )

            logger.info(
                "Collection created",
                name=self._collection_name,
                vector_size=self._vector_size,
                distance=distance,
            )
            return True

        except Exception as e:
            logger.error("Collection creation failed", error=str(e))
            return False

    async def delete_collection(self) -> bool:
        """
        Delete collection.

        Returns:
            True if deleted successfully
        """
        try:
            await self._client.delete_collection(
                collection_name=self._collection_name
            )
            logger.info("Collection deleted", name=self._collection_name)
            return True
        except Exception as e:
            logger.error("Collection deletion failed", error=str(e))
            return False

    async def ping(self) -> bool:
        """
        Ping Qdrant server.

        Returns:
            True if connected, False otherwise
        """
        try:
            await self._client.get_collections()
            return True
        except Exception as e:
            logger.error("Qdrant ping failed", error=str(e))
            return False

    async def get_collection_info(self) -> Optional[dict]:
        """
        Get collection information.

        Returns:
            Collection info dict if successful
        """
        try:
            info = await self._client.get_collection(
                collection_name=self._collection_name
            )
            return {
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "config": {
                    "vector_size": self._vector_size,
                    "distance": info.config.params.vectors.distance,
                },
            }
        except Exception as e:
            logger.error("Get collection info failed", error=str(e))
            return None

    async def store_point(self, point: QdrantPoint) -> bool:
        """
        Store a single vector point.

        Args:
            point: QdrantPoint to store

        Returns:
            True if stored successfully
        """
        try:
            await self._client.upsert(
                collection_name=self._collection_name,
                points=[point.to_qdrant_point()],
            )

            logger.info(
                "Point stored",
                point_id=point.id,
                query_hash=point.payload.get("query_hash"),
            )
            return True

        except Exception as e:
            logger.error("Point store failed", point_id=point.id, error=str(e))
            return False

    async def store_points(self, points: List[QdrantPoint]) -> int:
        """
        Store multiple vector points.

        Args:
            points: List of QdrantPoints to store

        Returns:
            Number of points stored successfully
        """
        if not points:
            return 0

        try:
            qdrant_points = [p.to_qdrant_point() for p in points]
            await self._client.upsert(
                collection_name=self._collection_name, points=qdrant_points
            )

            logger.info("Points stored", count=len(points))
            return len(points)

        except Exception as e:
            logger.error("Batch store failed", count=len(points), error=str(e))
            return 0

    async def point_exists(self, point_id: str) -> bool:
        """
        Check if point exists by ID.

        Args:
            point_id: Point ID to check

        Returns:
            True if exists, False otherwise
        """
        try:
            points = await self._client.retrieve(
                collection_name=self._collection_name, ids=[point_id]
            )
            return len(points) > 0

        except Exception as e:
            logger.error("Point exists check failed", point_id=point_id, error=str(e))
            return False

    async def get_point(self, point_id: str) -> Optional[QdrantPoint]:
        """
        Retrieve point by ID.

        Args:
            point_id: Point ID to retrieve

        Returns:
            QdrantPoint if found, None otherwise
        """
        try:
            points = await self._client.retrieve(
                collection_name=self._collection_name,
                ids=[point_id],
                with_vectors=True,
                with_payload=True,
            )

            if not points:
                return None

            point = points[0]
            return QdrantPoint.from_qdrant_point(
                point_id=str(point.id), vector=point.vector, payload=point.payload
            )

        except Exception as e:
            logger.error("Get point failed", point_id=point_id, error=str(e))
            return None
