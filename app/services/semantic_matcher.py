"""
Semantic matcher service.

Finds semantically similar queries using vector embeddings.

Sandi Metz Principles:
- Single Responsibility: Semantic matching
- Small methods: Each method < 15 lines
- Dependency Injection: Dependencies injected
"""

from typing import List, Optional

from app.config import config
from app.embeddings.generator import EmbeddingGenerator
from app.models.embedding import EmbeddingResult
from app.models.qdrant_point import SearchResult
from app.repositories.qdrant_repository import QdrantRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SemanticMatchError(Exception):
    """Semantic matching error."""

    pass


class SemanticMatch:
    """
    Result of semantic matching.

    Contains the matched query and similarity score.
    """

    def __init__(
        self,
        query: str,
        score: float,
        cached_response: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Initialize semantic match.

        Args:
            query: Matched query text
            score: Similarity score (0.0 to 1.0)
            cached_response: Cached response if available
            metadata: Additional match metadata
        """
        self.query = query
        self.score = score
        self.cached_response = cached_response
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        """Representation."""
        return (
            f"SemanticMatch(query='{self.query[:50]}...', "
            f"score={self.score:.4f})"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "score": self.score,
            "cached_response": self.cached_response,
            "metadata": self.metadata,
        }


class SemanticMatcher:
    """
    Semantic matcher for finding similar queries.

    Uses vector embeddings and Qdrant for semantic search.
    """

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        qdrant_repository: QdrantRepository,
        similarity_threshold: Optional[float] = None,
        max_results: int = 5,
    ):
        """
        Initialize semantic matcher.

        Args:
            embedding_generator: Embedding generator service
            qdrant_repository: Qdrant repository for vector search
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            max_results: Maximum number of matches to return
        """
        self._embedding_generator = embedding_generator
        self._qdrant = qdrant_repository
        self._similarity_threshold = (
            similarity_threshold or config.semantic_similarity_threshold
        )
        self._max_results = max_results

    async def find_matches(
        self,
        query: str,
        threshold: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[SemanticMatch]:
        """
        Find semantically similar queries.

        Args:
            query: Query text to match
            threshold: Custom similarity threshold (overrides default)
            limit: Maximum number of results (overrides default)

        Returns:
            List of semantic matches sorted by score (highest first)

        Raises:
            SemanticMatchError: If matching fails
        """
        try:
            threshold = threshold or self._similarity_threshold
            limit = limit or self._max_results

            # Generate embedding for query
            logger.debug(
                "Generating embedding for semantic match",
                query_length=len(query),
            )
            embedding = await self._embedding_generator.generate(query, normalize=True)

            # Search for similar vectors
            logger.debug(
                "Searching for semantic matches",
                threshold=threshold,
                limit=limit,
            )
            search_results = await self._qdrant.search_similar(
                query_vector=embedding.embedding.vector,
                limit=limit,
                score_threshold=threshold,
            )

            # Convert to semantic matches
            matches = self._convert_to_matches(search_results)

            logger.info(
                "Semantic matches found",
                query_length=len(query),
                matches_count=len(matches),
                threshold=threshold,
            )

            return matches

        except Exception as e:
            logger.error("Semantic matching failed", error=str(e), query=query[:100])
            raise SemanticMatchError(f"Failed to find semantic matches: {str(e)}") from e

    async def find_best_match(
        self,
        query: str,
        threshold: Optional[float] = None,
    ) -> Optional[SemanticMatch]:
        """
        Find single best semantic match.

        Args:
            query: Query text to match
            threshold: Custom similarity threshold

        Returns:
            Best match or None if no matches above threshold

        Raises:
            SemanticMatchError: If matching fails
        """
        matches = await self.find_matches(query, threshold=threshold, limit=1)

        if matches:
            logger.debug(
                "Best match found",
                query_length=len(query),
                score=matches[0].score,
            )
            return matches[0]

        logger.debug("No semantic match found", query_length=len(query))
        return None

    async def has_semantic_match(
        self,
        query: str,
        threshold: Optional[float] = None,
    ) -> bool:
        """
        Check if query has any semantic matches.

        Args:
            query: Query text to check
            threshold: Custom similarity threshold

        Returns:
            True if at least one match exists
        """
        try:
            match = await self.find_best_match(query, threshold=threshold)
            return match is not None
        except Exception as e:
            logger.error("Match check failed", error=str(e))
            return False

    def _convert_to_matches(
        self, search_results: List[SearchResult]
    ) -> List[SemanticMatch]:
        """
        Convert Qdrant search results to semantic matches.

        Args:
            search_results: List of Qdrant search results

        Returns:
            List of semantic matches
        """
        matches = []

        for result in search_results:
            # Extract query from payload
            query = result.payload.get("query", "")
            cached_response = result.payload.get("response")

            # Create match
            match = SemanticMatch(
                query=query,
                score=result.score,
                cached_response=cached_response,
                metadata={
                    "point_id": result.point_id,
                    "payload": result.payload,
                },
            )
            matches.append(match)

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)

        return matches

    async def store_query_embedding(
        self,
        query: str,
        response: str,
        point_id: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Store query embedding for future matching.

        Args:
            query: Query text
            response: Cached response
            point_id: Unique point identifier
            metadata: Additional metadata to store

        Returns:
            True if stored successfully

        Raises:
            SemanticMatchError: If storage fails
        """
        try:
            # Generate embedding
            embedding = await self._embedding_generator.generate(query, normalize=True)

            # Prepare payload
            payload = {
                "query": query,
                "response": response,
                **(metadata or {}),
            }

            # Import QdrantPoint here to avoid circular dependency
            from app.models.qdrant_point import QdrantPoint

            # Create point
            point = QdrantPoint(
                id=point_id,
                vector=embedding.embedding.vector,
                payload=payload,
            )

            # Store in Qdrant
            success = await self._qdrant.store_point(point)

            if success:
                logger.info(
                    "Query embedding stored",
                    point_id=point_id,
                    query_length=len(query),
                )
            else:
                logger.warning(
                    "Failed to store query embedding",
                    point_id=point_id,
                )

            return success

        except Exception as e:
            logger.error("Embedding storage failed", error=str(e), point_id=point_id)
            raise SemanticMatchError(
                f"Failed to store query embedding: {str(e)}"
            ) from e

    async def delete_query_embedding(self, point_id: str) -> bool:
        """
        Delete stored query embedding.

        Args:
            point_id: Point identifier to delete

        Returns:
            True if deleted successfully
        """
        try:
            success = await self._qdrant.delete_point(point_id)

            if success:
                logger.info("Query embedding deleted", point_id=point_id)
            else:
                logger.warning("Failed to delete query embedding", point_id=point_id)

            return success

        except Exception as e:
            logger.error("Embedding deletion failed", error=str(e), point_id=point_id)
            return False

    def set_threshold(self, threshold: float) -> None:
        """
        Set similarity threshold.

        Args:
            threshold: New threshold (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")

        self._similarity_threshold = threshold
        logger.info("Updated similarity threshold", threshold=threshold)

    def set_max_results(self, max_results: int) -> None:
        """
        Set maximum results.

        Args:
            max_results: New maximum (must be positive)
        """
        if max_results < 1:
            raise ValueError("Max results must be positive")

        self._max_results = max_results
        logger.info("Updated max results", max_results=max_results)

    def get_config(self) -> dict:
        """
        Get matcher configuration.

        Returns:
            Dictionary with configuration
        """
        return {
            "similarity_threshold": self._similarity_threshold,
            "max_results": self._max_results,
            "vector_dimensions": self._embedding_generator.get_embedding_dimensions(),
        }

    async def health_check(self) -> bool:
        """
        Check if semantic matcher is healthy.

        Returns:
            True if all components are functional
        """
        try:
            # Check embedding generator
            if not await self._embedding_generator.health_check():
                return False

            # Check Qdrant connection
            if not await self._qdrant.ping():
                return False

            return True

        except Exception as e:
            logger.error("Semantic matcher health check failed", error=str(e))
            return False
