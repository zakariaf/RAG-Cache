"""
Qdrant repository for vector storage and search.

Sandi Metz Principles:
- Single Responsibility: Qdrant data access
- Small methods: Each operation isolated
- Dependency Injection: Client injected
"""

from typing import List, Optional
from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import config
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
