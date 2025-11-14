"""
Qdrant health check service.

Sandi Metz Principles:
- Single Responsibility: Health monitoring
- Small methods: Each check isolated
- Clear naming: Descriptive method names
"""

from enum import Enum
from typing import Dict, Optional

from app.cache.qdrant_collection import QdrantCollectionManager
from app.repositories.qdrant_repository import QdrantRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class QdrantHealthCheck:
    """
    Qdrant health check service.

    Monitors Qdrant service health and collection status.
    """

    def __init__(
        self, repository: QdrantRepository, collection_manager: QdrantCollectionManager
    ):
        """
        Initialize health check service.

        Args:
            repository: Qdrant repository
            collection_manager: Collection manager
        """
        self._repository = repository
        self._collection_manager = collection_manager

    async def check_health(self) -> Dict[str, any]:
        """
        Perform comprehensive health check.

        Returns:
            Health check results dictionary
        """
        results = {
            "status": HealthStatus.HEALTHY.value,
            "checks": {},
            "details": {},
        }

        # Check connection
        connection_ok = await self._check_connection()
        results["checks"]["connection"] = connection_ok

        if not connection_ok:
            results["status"] = HealthStatus.UNHEALTHY.value
            results["details"]["error"] = "Cannot connect to Qdrant"
            return results

        # Check collection
        collection_ok = await self._check_collection()
        results["checks"]["collection"] = collection_ok

        if not collection_ok:
            results["status"] = HealthStatus.DEGRADED.value
            results["details"]["warning"] = "Collection not properly configured"

        # Get collection stats
        stats = await self._get_collection_stats()
        results["details"]["statistics"] = stats

        # Determine final status
        if all(results["checks"].values()):
            results["status"] = HealthStatus.HEALTHY.value
        elif any(results["checks"].values()):
            results["status"] = HealthStatus.DEGRADED.value
        else:
            results["status"] = HealthStatus.UNHEALTHY.value

        logger.info("Health check completed", status=results["status"])
        return results

    async def _check_connection(self) -> bool:
        """
        Check Qdrant server connection.

        Returns:
            True if connected
        """
        try:
            return await self._repository.ping()
        except Exception as e:
            logger.error("Connection check failed", error=str(e))
            return False

    async def _check_collection(self) -> bool:
        """
        Check collection existence and configuration.

        Returns:
            True if collection is properly configured
        """
        try:
            validation = await self._collection_manager.validate_collection()
            return all(validation.values())
        except Exception as e:
            logger.error("Collection check failed", error=str(e))
            return False

    async def _get_collection_stats(self) -> Optional[Dict]:
        """
        Get collection statistics.

        Returns:
            Statistics dictionary
        """
        try:
            info = await self._repository.get_collection_info()
            if info:
                return {
                    "vectors_count": info.get("vectors_count", 0),
                    "points_count": info.get("points_count", 0),
                    "status": info.get("status", "unknown"),
                }
            return None
        except Exception as e:
            logger.error("Stats retrieval failed", error=str(e))
            return None

    async def is_healthy(self) -> bool:
        """
        Quick health check.

        Returns:
            True if healthy
        """
        results = await self.check_health()
        return results["status"] == HealthStatus.HEALTHY.value

    async def is_ready(self) -> bool:
        """
        Check if service is ready to handle requests.

        Returns:
            True if ready
        """
        connection_ok = await self._check_connection()
        collection_ok = await self._check_collection()
        return connection_ok and collection_ok

    async def get_status_summary(self) -> str:
        """
        Get human-readable status summary.

        Returns:
            Status summary string
        """
        results = await self.check_health()
        status = results["status"]

        if status == HealthStatus.HEALTHY.value:
            return "All systems operational"
        elif status == HealthStatus.DEGRADED.value:
            return "Service degraded - some features may be limited"
        else:
            return "Service unavailable - critical issues detected"
