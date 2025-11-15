"""
Qdrant collection initialization and management.

Sandi Metz Principles:
- Single Responsibility: Collection setup and validation
- Small methods: Each operation isolated
- Dependency Injection: Repository injected
"""

from typing import Optional

from qdrant_client.models import Distance

from app.repositories.qdrant_repository import QdrantRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QdrantCollectionManager:
    """
    Manages Qdrant collection initialization.

    Ensures collection exists and is properly configured.
    """

    def __init__(self, repository: QdrantRepository):
        """
        Initialize collection manager.

        Args:
            repository: Qdrant repository
        """
        self._repository = repository

    async def initialize(
        self, distance: Distance = Distance.COSINE, recreate: bool = False
    ) -> bool:
        """
        Initialize collection for vector storage.

        Args:
            distance: Distance metric for similarity
            recreate: Whether to recreate existing collection

        Returns:
            True if initialized successfully
        """
        try:
            if recreate:
                await self._recreate_collection(distance)
                return True

            return await self._ensure_collection_exists(distance)

        except Exception as e:
            logger.error("Collection initialization failed", error=str(e))
            return False

    async def _ensure_collection_exists(self, distance: Distance) -> bool:
        """
        Ensure collection exists.

        Args:
            distance: Distance metric

        Returns:
            True if exists or created
        """
        exists = await self._repository.collection_exists()

        if exists:
            logger.info("Collection verified")
            return True

        return await self._repository.create_collection(distance)

    async def _recreate_collection(self, distance: Distance) -> bool:
        """
        Recreate collection (delete and create).

        Args:
            distance: Distance metric

        Returns:
            True if recreated successfully
        """
        logger.warning("Recreating collection - all data will be lost")

        # Delete if exists
        exists = await self._repository.collection_exists()
        if exists:
            await self._repository.delete_collection()

        # Create new collection
        return await self._repository.create_collection(distance)

    async def validate_collection(self) -> dict[str, bool]:
        """
        Validate collection configuration.

        Returns:
            Validation results dict
        """
        results = {
            "exists": False,
            "accessible": False,
            "configured": False,
        }

        try:
            # Check existence
            results["exists"] = await self._repository.collection_exists()
            if not results["exists"]:
                return results

            # Check accessibility
            results["accessible"] = await self._repository.ping()
            if not results["accessible"]:
                return results

            # Check configuration
            info = await self._repository.get_collection_info()
            results["configured"] = info is not None

            return results

        except Exception as e:
            logger.error("Collection validation failed", error=str(e))
            return results

    async def get_status(self) -> Optional[dict]:
        """
        Get collection status and statistics.

        Returns:
            Status dict if successful
        """
        try:
            validation = await self.validate_collection()
            if not validation["exists"]:
                return {
                    "status": "not_initialized",
                    "message": "Collection does not exist",
                }

            info = await self._repository.get_collection_info()
            if not info:
                return {
                    "status": "error",
                    "message": "Failed to get collection info",
                }

            return {
                "status": "ready",
                "vectors_count": info["vectors_count"],
                "points_count": info["points_count"],
                "collection_status": info["status"],
                "config": info["config"],
            }

        except Exception as e:
            logger.error("Get status failed", error=str(e))
            return {
                "status": "error",
                "message": str(e),
            }
