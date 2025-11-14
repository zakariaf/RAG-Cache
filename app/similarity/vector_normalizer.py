"""
Vector normalization utilities.

Sandi Metz Principles:
- Single Responsibility: Vector normalization
- Small methods: Each operation isolated
- Clear naming: Descriptive method names
"""

import math
from typing import List

from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorNormalizer:
    """
    Utilities for vector normalization.

    Ensures vectors are properly normalized for distance calculations.
    """

    @staticmethod
    def l2_normalize(vector: List[float]) -> List[float]:
        """
        Normalize vector using L2 (Euclidean) norm.

        Args:
            vector: Input vector

        Returns:
            Normalized vector with unit length
        """
        try:
            magnitude = math.sqrt(sum(x * x for x in vector))

            if magnitude == 0:
                logger.warning("Cannot normalize zero vector")
                return vector

            return [x / magnitude for x in vector]

        except Exception as e:
            logger.error("L2 normalization failed", error=str(e))
            return vector

    @staticmethod
    def l1_normalize(vector: List[float]) -> List[float]:
        """
        Normalize vector using L1 (Manhattan) norm.

        Args:
            vector: Input vector

        Returns:
            L1 normalized vector
        """
        try:
            total = sum(abs(x) for x in vector)

            if total == 0:
                logger.warning("Cannot normalize zero vector")
                return vector

            return [x / total for x in vector]

        except Exception as e:
            logger.error("L1 normalization failed", error=str(e))
            return vector

    @staticmethod
    def max_normalize(vector: List[float]) -> List[float]:
        """
        Normalize vector by dividing by maximum absolute value.

        Args:
            vector: Input vector

        Returns:
            Max normalized vector
        """
        try:
            max_val = max(abs(x) for x in vector)

            if max_val == 0:
                logger.warning("Cannot normalize zero vector")
                return vector

            return [x / max_val for x in vector]

        except Exception as e:
            logger.error("Max normalization failed", error=str(e))
            return vector

    @staticmethod
    def is_normalized(vector: List[float], tolerance: float = 1e-6) -> bool:
        """
        Check if vector is normalized (unit length).

        Args:
            vector: Vector to check
            tolerance: Tolerance for magnitude check

        Returns:
            True if vector has unit length
        """
        try:
            magnitude = math.sqrt(sum(x * x for x in vector))
            return abs(magnitude - 1.0) < tolerance
        except Exception as e:
            logger.error("Normalization check failed", error=str(e))
            return False

    @staticmethod
    def magnitude(vector: List[float]) -> float:
        """
        Calculate vector magnitude (L2 norm).

        Args:
            vector: Input vector

        Returns:
            Vector magnitude
        """
        try:
            return math.sqrt(sum(x * x for x in vector))
        except Exception as e:
            logger.error("Magnitude calculation failed", error=str(e))
            return 0.0

    @staticmethod
    def zero_center(vector: List[float]) -> List[float]:
        """
        Center vector around zero by subtracting mean.

        Args:
            vector: Input vector

        Returns:
            Zero-centered vector
        """
        try:
            mean = sum(vector) / len(vector) if vector else 0.0
            return [x - mean for x in vector]
        except Exception as e:
            logger.error("Zero centering failed", error=str(e))
            return vector

    @staticmethod
    def standardize(vector: List[float]) -> List[float]:
        """
        Standardize vector (zero mean, unit variance).

        Args:
            vector: Input vector

        Returns:
            Standardized vector
        """
        try:
            if not vector:
                return vector

            mean = sum(vector) / len(vector)
            variance = sum((x - mean) ** 2 for x in vector) / len(vector)

            if variance == 0:
                logger.warning("Cannot standardize constant vector")
                return vector

            std_dev = math.sqrt(variance)
            return [(x - mean) / std_dev for x in vector]

        except Exception as e:
            logger.error("Standardization failed", error=str(e))
            return vector

    @staticmethod
    def clip(
        vector: List[float], min_val: float = -1.0, max_val: float = 1.0
    ) -> List[float]:
        """
        Clip vector values to range.

        Args:
            vector: Input vector
            min_val: Minimum value
            max_val: Maximum value

        Returns:
            Clipped vector
        """
        try:
            return [max(min_val, min(max_val, x)) for x in vector]
        except Exception as e:
            logger.error("Vector clipping failed", error=str(e))
            return vector
