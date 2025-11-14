"""
Vector normalization utilities.

Sandi Metz Principles:
- Single Responsibility: Vector normalization
- Small methods: Each operation isolated
- Clear naming: Descriptive method names
"""

import math
from enum import Enum
from typing import List

from app.utils.logger import get_logger

logger = get_logger(__name__)


class NormalizationType(str, Enum):
    """Normalization type options."""

    L1 = "l1"
    L2 = "l2"
    MAX = "max"


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

    @classmethod
    def normalize(
        cls, vector: List[float], norm_type: NormalizationType = NormalizationType.L2
    ) -> List[float]:
        """
        Normalize vector using specified normalization type.

        Args:
            vector: Input vector
            norm_type: Type of normalization to apply

        Returns:
            Normalized vector
        """
        if norm_type == NormalizationType.L1:
            return cls.l1_normalize(vector)
        elif norm_type == NormalizationType.L2:
            return cls.l2_normalize(vector)
        elif norm_type == NormalizationType.MAX:
            return cls.max_normalize(vector)
        else:
            raise ValueError(f"Unknown normalization type: {norm_type}")

    @classmethod
    def batch_normalize(
        cls,
        vectors: List[List[float]],
        norm_type: NormalizationType = NormalizationType.L2,
    ) -> List[List[float]]:
        """
        Normalize multiple vectors.

        Args:
            vectors: List of input vectors
            norm_type: Type of normalization to apply

        Returns:
            List of normalized vectors
        """
        return [cls.normalize(vec, norm_type) for vec in vectors]

    @classmethod
    def is_normalized(
        cls,
        vector: List[float],
        norm_type: NormalizationType = NormalizationType.L2,
        tolerance: float = 1e-6,
    ) -> bool:
        """
        Check if vector is normalized according to the given norm type.

        Args:
            vector: Vector to check
            norm_type: Type of normalization to check
            tolerance: Tolerance for check

        Returns:
            True if vector is normalized
        """
        if norm_type == NormalizationType.L2:
            magnitude = cls.magnitude(vector)
            return abs(magnitude - 1.0) < tolerance
        elif norm_type == NormalizationType.L1:
            l1_norm = sum(abs(x) for x in vector)
            return abs(l1_norm - 1.0) < tolerance
        elif norm_type == NormalizationType.MAX:
            max_val = max(abs(x) for x in vector) if vector else 0.0
            return abs(max_val - 1.0) < tolerance
        return False

    @classmethod
    def safe_normalize(
        cls, vector: List[float], norm_type: NormalizationType = NormalizationType.L2
    ) -> List[float]:
        """
        Safely normalize vector, returning original if normalization fails.

        Args:
            vector: Input vector
            norm_type: Type of normalization to apply

        Returns:
            Normalized vector or original if normalization fails
        """
        try:
            return cls.normalize(vector, norm_type)
        except Exception as e:
            logger.error("Safe normalization failed", error=str(e))
            return vector


# Convenience standalone functions
def l1_normalize(vector: List[float]) -> List[float]:
    """Normalize vector using L1 norm."""
    return VectorNormalizer.l1_normalize(vector)


def l2_normalize(vector: List[float]) -> List[float]:
    """Normalize vector using L2 norm."""
    return VectorNormalizer.l2_normalize(vector)


def max_normalize(vector: List[float]) -> List[float]:
    """Normalize vector by max value."""
    return VectorNormalizer.max_normalize(vector)


def standardize_vector(vector: List[float]) -> List[float]:
    """Standardize vector (zero mean, unit variance)."""
    return VectorNormalizer.standardize(vector)


def clip_vector(
    vector: List[float], min_val: float = -1.0, max_val: float = 1.0
) -> List[float]:
    """Clip vector values to range."""
    return VectorNormalizer.clip(vector, min_val, max_val)
