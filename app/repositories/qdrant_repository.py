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
from qdrant_client.models import Distance, PointStruct, VectorParams, Filter

from app.config import config
from app.models.qdrant_point import (
    BatchUploadResult,
    DeleteResult,
    QdrantPoint,
    SearchResult,
)
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

    async def create_collection(self, distance: Distance = Distance.COSINE) -> bool:
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
                vectors_config=VectorParams(size=self._vector_size, distance=distance),
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
            await self._client.delete_collection(collection_name=self._collection_name)
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

    async def search_similar(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_condition: Optional[Filter] = None,
    ) -> List[SearchResult]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_condition: Optional filter for search

        Returns:
            List of SearchResult objects
        """
        try:
            results = await self._client.search(
                collection_name=self._collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_condition,
                with_payload=True,
                with_vectors=False,
            )

            search_results = [
                SearchResult(
                    point_id=str(result.id),
                    score=result.score,
                    vector=result.vector if result.vector else None,
                    payload=result.payload if result.payload else {},
                )
                for result in results
            ]

            logger.info(
                "Similarity search completed",
                results_count=len(search_results),
                threshold=score_threshold,
            )

            return search_results

        except Exception as e:
            logger.error("Similarity search failed", error=str(e))
            return []

    async def search_similar_with_vectors(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        Search for similar vectors including vector data.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of SearchResult objects with vectors
        """
        try:
            results = await self._client.search(
                collection_name=self._collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=True,
            )

            search_results = [
                SearchResult(
                    point_id=str(result.id),
                    score=result.score,
                    vector=result.vector if result.vector else None,
                    payload=result.payload if result.payload else {},
                )
                for result in results
            ]

            logger.info(
                "Similarity search with vectors completed",
                results_count=len(search_results),
            )

            return search_results

        except Exception as e:
            logger.error("Similarity search with vectors failed", error=str(e))
            return []

    async def batch_upload(
        self, points: List[QdrantPoint], batch_size: int = 100
    ) -> BatchUploadResult:
        """
        Upload points in batches with progress tracking.

        Args:
            points: List of QdrantPoints to upload
            batch_size: Number of points per batch

        Returns:
            BatchUploadResult with statistics
        """
        if not points:
            return BatchUploadResult(
                total=0, successful=0, failed=0, point_ids=[], errors=[]
            )

        total = len(points)
        successful = 0
        failed = 0
        uploaded_ids = []
        errors = []

        try:
            # Process in batches
            for i in range(0, total, batch_size):
                batch = points[i : i + batch_size]

                try:
                    qdrant_points = [p.to_qdrant_point() for p in batch]
                    await self._client.upsert(
                        collection_name=self._collection_name, points=qdrant_points
                    )

                    # Track success
                    successful += len(batch)
                    uploaded_ids.extend([p.id for p in batch])

                    logger.info(
                        "Batch uploaded",
                        batch_num=i // batch_size + 1,
                        batch_size=len(batch),
                        progress=f"{successful}/{total}",
                    )

                except Exception as batch_error:
                    # Track failure
                    failed += len(batch)
                    error_msg = (
                        f"Batch {i // batch_size + 1} failed: {str(batch_error)}"
                    )
                    errors.append(error_msg)
                    logger.error("Batch upload failed", error=error_msg)

            result = BatchUploadResult(
                total=total,
                successful=successful,
                failed=failed,
                point_ids=uploaded_ids,
                errors=errors,
            )

            logger.info(
                "Batch upload completed",
                total=total,
                successful=successful,
                failed=failed,
                success_rate=result.success_rate,
            )

            return result

        except Exception as e:
            logger.error("Batch upload fatal error", error=str(e))
            return BatchUploadResult(
                total=total,
                successful=successful,
                failed=total - successful,
                point_ids=uploaded_ids,
                errors=errors + [f"Fatal error: {str(e)}"],
            )

    async def batch_upload_with_retry(
        self,
        points: List[QdrantPoint],
        batch_size: int = 100,
        max_retries: int = 3,
    ) -> BatchUploadResult:
        """
        Upload points with automatic retry on failure.

        Args:
            points: List of QdrantPoints to upload
            batch_size: Number of points per batch
            max_retries: Maximum retry attempts

        Returns:
            BatchUploadResult with statistics
        """
        retry_count = 0
        last_result = None

        while retry_count <= max_retries:
            result = await self.batch_upload(points, batch_size)

            if not result.has_failures:
                return result

            # Retry failed batches
            if retry_count < max_retries:
                logger.warning(
                    "Retrying failed uploads",
                    retry=retry_count + 1,
                    max_retries=max_retries,
                    failed=result.failed,
                )
                retry_count += 1
                last_result = result
            else:
                logger.error("Max retries exceeded", failed=result.failed)
                return result

        return last_result or BatchUploadResult(
            total=len(points), successful=0, failed=len(points), errors=[]
        )

    async def delete_point(self, point_id: str) -> DeleteResult:
        """
        Delete a single point by ID.

        Args:
            point_id: Point ID to delete

        Returns:
            DeleteResult with operation status
        """
        try:
            await self._client.delete(
                collection_name=self._collection_name, points_selector=[point_id]
            )

            logger.info("Point deleted", point_id=point_id)
            return DeleteResult(
                deleted_count=1, success=True, message=f"Point {point_id} deleted"
            )

        except Exception as e:
            logger.error("Point deletion failed", point_id=point_id, error=str(e))
            return DeleteResult(
                deleted_count=0, success=False, message=f"Deletion failed: {str(e)}"
            )

    async def delete_points(self, point_ids: List[str]) -> DeleteResult:
        """
        Delete multiple points by IDs.

        Args:
            point_ids: List of point IDs to delete

        Returns:
            DeleteResult with operation status
        """
        if not point_ids:
            return DeleteResult(
                deleted_count=0, success=True, message="No points to delete"
            )

        try:
            await self._client.delete(
                collection_name=self._collection_name, points_selector=point_ids
            )

            logger.info("Points deleted", count=len(point_ids))
            return DeleteResult(
                deleted_count=len(point_ids),
                success=True,
                message=f"Deleted {len(point_ids)} points",
            )

        except Exception as e:
            logger.error("Batch deletion failed", count=len(point_ids), error=str(e))
            return DeleteResult(
                deleted_count=0, success=False, message=f"Deletion failed: {str(e)}"
            )

    async def delete_by_filter(self, filter_condition: Filter) -> DeleteResult:
        """
        Delete points matching filter condition.

        Args:
            filter_condition: Filter to match points

        Returns:
            DeleteResult with operation status
        """
        try:
            # Note: Qdrant doesn't return count for filter-based deletion
            await self._client.delete(
                collection_name=self._collection_name,
                points_selector=filter_condition,
            )

            logger.info("Points deleted by filter")
            return DeleteResult(
                deleted_count=-1,  # Unknown count
                success=True,
                message="Points deleted by filter",
            )

        except Exception as e:
            logger.error("Filter deletion failed", error=str(e))
            return DeleteResult(
                deleted_count=0, success=False, message=f"Deletion failed: {str(e)}"
            )

    async def delete_by_query_hash(self, query_hash: str) -> DeleteResult:
        """
        Delete points by query hash.

        Args:
            query_hash: Query hash to match

        Returns:
            DeleteResult with operation status
        """
        from app.cache.qdrant_filter import create_filter

        filter_obj = create_filter().with_query_hash(query_hash).build()

        if not filter_obj:
            return DeleteResult(
                deleted_count=0, success=False, message="Failed to create filter"
            )

        return await self.delete_by_filter(filter_obj)

    async def update_point_payload(
        self, point_id: str, payload: Dict[str, any]
    ) -> bool:
        """
        Update point payload metadata.

        Args:
            point_id: Point ID to update
            payload: New payload data

        Returns:
            True if updated successfully
        """
        try:
            await self._client.set_payload(
                collection_name=self._collection_name,
                payload=payload,
                points=[point_id],
            )

            logger.info("Point payload updated", point_id=point_id)
            return True

        except Exception as e:
            logger.error("Payload update failed", point_id=point_id, error=str(e))
            return False

    async def update_point_vector(self, point_id: str, vector: List[float]) -> bool:
        """
        Update point vector.

        Args:
            point_id: Point ID to update
            vector: New vector data

        Returns:
            True if updated successfully
        """
        try:
            await self._client.update_vectors(
                collection_name=self._collection_name,
                points=[PointStruct(id=point_id, vector=vector, payload={})],
            )

            logger.info("Point vector updated", point_id=point_id)
            return True

        except Exception as e:
            logger.error("Vector update failed", point_id=point_id, error=str(e))
            return False

    async def update_point(self, point: QdrantPoint) -> bool:
        """
        Update complete point (vector + payload).

        Args:
            point: QdrantPoint with updated data

        Returns:
            True if updated successfully
        """
        try:
            # Upsert replaces the point completely
            await self._client.upsert(
                collection_name=self._collection_name,
                points=[point.to_qdrant_point()],
            )

            logger.info("Point updated", point_id=point.id)
            return True

        except Exception as e:
            logger.error("Point update failed", point_id=point.id, error=str(e))
            return False

    async def partial_update_payload(
        self, point_id: str, updates: Dict[str, any]
    ) -> bool:
        """
        Partially update payload fields.

        Args:
            point_id: Point ID to update
            updates: Fields to update

        Returns:
            True if updated successfully
        """
        try:
            await self._client.set_payload(
                collection_name=self._collection_name,
                payload=updates,
                points=[point_id],
            )

            logger.info(
                "Partial payload update", point_id=point_id, fields=list(updates.keys())
            )
            return True

        except Exception as e:
            logger.error("Partial update failed", point_id=point_id, error=str(e))
            return False

    async def delete_payload_fields(
        self, point_id: str, field_names: List[str]
    ) -> bool:
        """
        Delete specific payload fields.

        Args:
            point_id: Point ID
            field_names: Fields to delete

        Returns:
            True if deleted successfully
        """
        try:
            await self._client.delete_payload(
                collection_name=self._collection_name,
                keys=field_names,
                points=[point_id],
            )

            logger.info("Payload fields deleted", point_id=point_id, fields=field_names)
            return True

        except Exception as e:
            logger.error("Field deletion failed", point_id=point_id, error=str(e))
            return False

    async def scroll_points(
        self,
        limit: int = 100,
        offset: Optional[str] = None,
        filter_condition: Optional[Filter] = None,
        with_vectors: bool = False,
    ) -> tuple[List[QdrantPoint], Optional[str]]:
        """
        Scroll through points with pagination.

        Args:
            limit: Number of points per page
            offset: Offset ID for pagination
            filter_condition: Optional filter
            with_vectors: Include vectors in results

        Returns:
            Tuple of (points, next_offset)
        """
        try:
            result = await self._client.scroll(
                collection_name=self._collection_name,
                limit=limit,
                offset=offset,
                scroll_filter=filter_condition,
                with_payload=True,
                with_vectors=with_vectors,
            )

            points = [
                QdrantPoint.from_qdrant_point(
                    point_id=str(point.id),
                    vector=point.vector if point.vector else [],
                    payload=point.payload if point.payload else {},
                )
                for point in result[0]
            ]

            next_offset = result[1]  # Next offset for pagination

            logger.info(
                "Scroll completed",
                returned=len(points),
                has_next=next_offset is not None,
            )

            return points, next_offset

        except Exception as e:
            logger.error("Scroll failed", error=str(e))
            return [], None

    async def count_points(self, filter_condition: Optional[Filter] = None) -> int:
        """
        Count points in collection.

        Args:
            filter_condition: Optional filter

        Returns:
            Number of points
        """
        try:
            result = await self._client.count(
                collection_name=self._collection_name,
                count_filter=filter_condition,
                exact=True,
            )

            count = result.count
            logger.info("Point count", count=count)
            return count

        except Exception as e:
            logger.error("Count failed", error=str(e))
            return 0

    async def get_all_points(
        self, batch_size: int = 100, filter_condition: Optional[Filter] = None
    ) -> List[QdrantPoint]:
        """
        Get all points using scroll pagination.

        Args:
            batch_size: Points per batch
            filter_condition: Optional filter

        Returns:
            List of all points
        """
        all_points = []
        offset = None

        try:
            while True:
                points, next_offset = await self.scroll_points(
                    limit=batch_size,
                    offset=offset,
                    filter_condition=filter_condition,
                    with_vectors=False,
                )

                all_points.extend(points)

                if next_offset is None:
                    break

                offset = next_offset

            logger.info("Retrieved all points", total=len(all_points))
            return all_points

        except Exception as e:
            logger.error("Get all points failed", error=str(e))
            return all_points  # Return what we got so far
