"""
Semantic Matcher Service.

Finds semantically similar cached queries using embeddings and Qdrant.

Sandi Metz Principles:
- Single Responsibility: Semantic matching
- Dependency Injection: Embedding and Qdrant injected
- Small methods: Each operation isolated
"""

from dataclasses import dataclass
from typing import List, Optional

from app.config import config
from app.embeddings.embedding_generator import EmbeddingGenerator
from app.exceptions import SemanticMatchError
from app.models.qdrant_point import SearchResult
from app.repositories.qdrant_repository import QdrantRepository
from app.similarity.score_calculator import SimilarityLevel, SimilarityScoreCalculator
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SemanticMatch:
    """Result of semantic matching."""

    query_hash: str
    original_query: str
    cached_response: str
    similarity_score: float
    similarity_level: SimilarityLevel
    provider: str
    model: str
    point_id: str

    @property
    def is_high_quality(self) -> bool:
        """Check if match is high quality."""
        return self.similarity_level in (
            SimilarityLevel.EXACT,
            SimilarityLevel.VERY_HIGH,
            SimilarityLevel.HIGH,
        )

    @property
    def confidence(self) -> str:
        """Get confidence description."""
        return SimilarityScoreCalculator.get_confidence_level(self.similarity_score)


class SemanticMatcher:
    """
    Matches queries semantically using vector similarity.

    Uses embeddings and Qdrant for semantic search.
    """

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        qdrant_repository: QdrantRepository,
        similarity_threshold: Optional[float] = None,
    ):
        """
        Initialize matcher with dependencies.

        Args:
            embedding_generator: Embedding generator service
            qdrant_repository: Qdrant repository
            similarity_threshold: Minimum similarity for match
        """
        self._embeddings = embedding_generator
        self._qdrant = qdrant_repository
        self._threshold = similarity_threshold or config.semantic_similarity_threshold

    async def find_match(self, query: str) -> Optional[SemanticMatch]:
        """
        Find best semantic match for a query.

        Args:
            query: Query string to match

        Returns:
            SemanticMatch if found above threshold, None otherwise
        """
        try:
            # Generate embedding for query
            embedding = await self._embeddings.generate(query)

            # Search for similar vectors
            results = await self._qdrant.search_similar(
                query_vector=embedding,
                limit=1,
                score_threshold=self._threshold,
            )

            if not results:
                logger.info("No semantic match found", query=query[:50])
                return None

            # Convert top result to match
            top_result = results[0]
            match = self._result_to_match(top_result)

            logger.info(
                "Semantic match found",
                query=query[:50],
                score=match.similarity_score,
                level=match.similarity_level.value,
            )

            return match

        except Exception as e:
            logger.error("Semantic matching failed", error=str(e))
            raise SemanticMatchError(f"Failed to find semantic match: {str(e)}")

    async def find_matches(self, query: str, limit: int = 5) -> List[SemanticMatch]:
        """
        Find multiple semantic matches for a query.

        Args:
            query: Query string to match
            limit: Maximum matches to return

        Returns:
            List of SemanticMatch objects
        """
        try:
            # Generate embedding
            embedding = await self._embeddings.generate(query)

            # Search for similar vectors
            results = await self._qdrant.search_similar(
                query_vector=embedding,
                limit=limit,
                score_threshold=self._threshold,
            )

            # Convert to matches
            matches = [self._result_to_match(r) for r in results]

            logger.info(
                "Semantic matches found",
                query=query[:50],
                count=len(matches),
            )

            return matches

        except Exception as e:
            logger.error("Semantic matching failed", error=str(e))
            raise SemanticMatchError(f"Failed to find semantic matches: {str(e)}")

    async def store_for_matching(
        self,
        query: str,
        query_hash: str,
        response: str,
        provider: str,
        model: str,
    ) -> bool:
        """
        Store a query-response pair for future matching.

        Args:
            query: Original query
            query_hash: Query hash for identification
            response: LLM response
            provider: LLM provider name
            model: Model name

        Returns:
            True if stored successfully
        """
        try:
            # Generate embedding
            embedding = await self._embeddings.generate(query)

            # Create point with payload
            from app.models.qdrant_point import QdrantPoint

            point = QdrantPoint(
                vector=embedding,
                payload={
                    "query_hash": query_hash,
                    "original_query": query,
                    "response": response,
                    "provider": provider,
                    "model": model,
                },
            )

            # Store in Qdrant
            success = await self._qdrant.store_point(point)

            if success:
                logger.info(
                    "Query stored for semantic matching",
                    query_hash=query_hash,
                )

            return success

        except Exception as e:
            logger.error("Failed to store for matching", error=str(e))
            return False

    def _result_to_match(self, result: SearchResult) -> SemanticMatch:
        """
        Convert search result to semantic match.

        Args:
            result: Qdrant search result

        Returns:
            SemanticMatch object
        """
        payload = result.payload
        score = result.score

        return SemanticMatch(
            query_hash=payload.get("query_hash", ""),
            original_query=payload.get("original_query", ""),
            cached_response=payload.get("response", ""),
            similarity_score=score,
            similarity_level=SimilarityScoreCalculator.interpret_score(score),
            provider=payload.get("provider", "unknown"),
            model=payload.get("model", "unknown"),
            point_id=result.point_id,
        )

    async def is_healthy(self) -> bool:
        """
        Check if semantic matching is operational.

        Returns:
            True if healthy
        """
        try:
            return await self._qdrant.ping()
        except Exception:
            return False

    @property
    def threshold(self) -> float:
        """Get similarity threshold."""
        return self._threshold

    def set_threshold(self, threshold: float) -> None:
        """
        Update similarity threshold.

        Args:
            threshold: New threshold (0.0 to 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self._threshold = threshold
            logger.info("Similarity threshold updated", threshold=threshold)
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")
