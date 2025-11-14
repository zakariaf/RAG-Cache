"""
Similarity score calculation and interpretation.

Sandi Metz Principles:
- Single Responsibility: Score calculation
- Small methods: Each calculation isolated
- Clear naming: Descriptive method names
"""

import math
from enum import Enum
from typing import List

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SimilarityLevel(str, Enum):
    """
    Semantic similarity quality levels.

    Helps interpret similarity scores.
    """

    EXACT = "exact"  # 0.95 - 1.0
    VERY_HIGH = "very_high"  # 0.85 - 0.95
    HIGH = "high"  # 0.75 - 0.85
    MODERATE = "moderate"  # 0.60 - 0.75
    LOW = "low"  # 0.40 - 0.60
    VERY_LOW = "very_low"  # < 0.40


class SimilarityScoreCalculator:
    """
    Calculator for similarity scores.

    Provides score calculation and interpretation.
    """

    # Threshold definitions
    EXACT_THRESHOLD = 0.95
    VERY_HIGH_THRESHOLD = 0.85
    HIGH_THRESHOLD = 0.75
    MODERATE_THRESHOLD = 0.60
    LOW_THRESHOLD = 0.40

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (-1.0 to 1.0)

        Raises:
            ValueError: If vectors have different dimensions
        """
        if len(vec1) != len(vec2):
            raise ValueError(
                f"Vectors must have same dimensions: {len(vec1)} != {len(vec2)}"
            )

        if len(vec1) == 0:
            raise ValueError("Vectors must have same dimensions: 0 != 0")

        try:
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(b * b for b in vec2))

            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0

            similarity = dot_product / (magnitude1 * magnitude2)
            return similarity

        except Exception as e:
            logger.error("Cosine similarity calculation failed", error=str(e))
            return 0.0

    @staticmethod
    def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate Euclidean distance between vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Euclidean distance

        Raises:
            ValueError: If vectors have different dimensions
        """
        if len(vec1) != len(vec2):
            raise ValueError(
                f"Vectors must have same dimensions: {len(vec1)} != {len(vec2)}"
            )

        try:
            return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))
        except Exception as e:
            logger.error("Euclidean distance calculation failed", error=str(e))
            return float("inf")

    @staticmethod
    def euclidean_to_similarity(distance: float, max_distance: float = 2.0) -> float:
        """
        Convert Euclidean distance to similarity score.

        Args:
            distance: Euclidean distance
            max_distance: Maximum expected distance

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if distance >= max_distance:
            return 0.0

        return 1.0 - (distance / max_distance)

    @staticmethod
    def dot_product(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate dot product of vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Dot product value
        """
        if len(vec1) != len(vec2):
            logger.error("Vector size mismatch", v1=len(vec1), v2=len(vec2))
            return 0.0

        try:
            return sum(a * b for a, b in zip(vec1, vec2))
        except Exception as e:
            logger.error("Dot product calculation failed", error=str(e))
            return 0.0

    @classmethod
    def interpret_score(cls, score: float) -> SimilarityLevel:
        """
        Interpret similarity score quality.

        Args:
            score: Similarity score (0.0 to 1.0)

        Returns:
            SimilarityLevel enum
        """
        if score >= cls.EXACT_THRESHOLD:
            return SimilarityLevel.EXACT
        elif score >= cls.VERY_HIGH_THRESHOLD:
            return SimilarityLevel.VERY_HIGH
        elif score >= cls.HIGH_THRESHOLD:
            return SimilarityLevel.HIGH
        elif score >= cls.MODERATE_THRESHOLD:
            return SimilarityLevel.MODERATE
        elif score >= cls.LOW_THRESHOLD:
            return SimilarityLevel.LOW
        else:
            return SimilarityLevel.VERY_LOW

    @classmethod
    def should_cache_hit(cls, score: float, threshold: float = 0.85) -> bool:
        """
        Determine if score qualifies as cache hit.

        Args:
            score: Similarity score
            threshold: Minimum acceptable score

        Returns:
            True if score meets threshold
        """
        return score >= threshold

    @classmethod
    def get_confidence_level(cls, score: float) -> str:
        """
        Get human-readable confidence level.

        Args:
            score: Similarity score

        Returns:
            Confidence description
        """
        level = cls.interpret_score(score)

        descriptions = {
            SimilarityLevel.EXACT: "Exact match - virtually identical",
            SimilarityLevel.VERY_HIGH: "Very high confidence - strong match",
            SimilarityLevel.HIGH: "High confidence - good match",
            SimilarityLevel.MODERATE: "Moderate confidence - acceptable match",
            SimilarityLevel.LOW: "Low confidence - weak match",
            SimilarityLevel.VERY_LOW: "Very low confidence - poor match",
        }

        return descriptions.get(level, "Unknown confidence")

    @classmethod
    def calculate(
        cls, vec1: List[float], vec2: List[float], metric: str = "cosine"
    ) -> float:
        """
        Calculate similarity using specified metric.

        Args:
            vec1: First vector
            vec2: Second vector
            metric: Similarity metric (cosine, euclidean)

        Returns:
            Similarity score

        Raises:
            ValueError: If unknown metric specified
        """
        if metric == "cosine":
            return cls.cosine_similarity(vec1, vec2)
        elif metric == "euclidean":
            return cls.euclidean_distance(vec1, vec2)
        else:
            raise ValueError(f"Unknown metric: {metric}")

    @staticmethod
    def is_match(score: float, threshold: float = 0.85) -> bool:
        """
        Check if score meets threshold for cache hit.

        Args:
            score: Similarity score
            threshold: Minimum threshold

        Returns:
            True if score meets or exceeds threshold
        """
        return score >= threshold

    @staticmethod
    def normalize_score(score: float, metric: str = "cosine") -> float:
        """
        Normalize score to 0-1 range.

        Args:
            score: Raw score
            metric: Metric type (cosine, euclidean)

        Returns:
            Normalized score (0-1)
        """
        if metric == "cosine":
            # Cosine already in [0, 1] for our use case (non-negative similarity)
            return score
        elif metric == "euclidean":
            # Convert distance to similarity (0 distance = 1.0 similarity)
            # Using inverse relationship
            max_distance = 10.0  # Configurable max
            if score == 0.0:
                return 1.0
            if score >= max_distance:
                return 0.0
            return 1.0 - (score / max_distance)
        return score

    @classmethod
    def get_interpretation(cls, score: float) -> SimilarityLevel:
        """
        Get score interpretation.

        Args:
            score: Similarity score

        Returns:
            SimilarityLevel enum
        """
        return cls.interpret_score(score)

    @staticmethod
    def calculate_match_quality(score: float) -> dict:
        """
        Calculate detailed match quality metrics.

        Args:
            score: Similarity score

        Returns:
            Dict with quality metrics
        """
        calculator = SimilarityScoreCalculator

        return {
            "score": round(score, 4),
            "percentage": round(score * 100, 2),
            "level": calculator.interpret_score(score).value,
            "confidence": calculator.get_confidence_level(score),
            "is_cache_hit": calculator.should_cache_hit(score),
        }


# Convenience aliases for easier imports
ScoreCalculator = SimilarityScoreCalculator
ScoreInterpretation = SimilarityLevel


# Standalone functions for convenience
def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between vectors."""
    return SimilarityScoreCalculator.cosine_similarity(vec1, vec2)


def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
    """Calculate Euclidean distance between vectors."""
    return SimilarityScoreCalculator.euclidean_distance(vec1, vec2)


def interpret_cosine_score(score: float) -> SimilarityLevel:
    """Interpret cosine similarity score."""
    return SimilarityScoreCalculator.interpret_score(score)
