"""Unit tests for vector normalizer."""

import math

import pytest

from app.similarity.vector_normalizer import (
    NormalizationType,
    VectorNormalizer,
    clip_vector,
    l1_normalize,
    l2_normalize,
    max_normalize,
    standardize_vector,
)


class TestL2Normalize:
    """Tests for L2 normalization."""

    def test_l2_normalize_unit_vector(self):
        """Test L2 normalization of unit vector."""
        vector = [1.0, 0.0, 0.0]
        normalized = l2_normalize(vector)

        assert abs(normalized[0] - 1.0) < 1e-6
        assert abs(normalized[1] - 0.0) < 1e-6
        assert abs(normalized[2] - 0.0) < 1e-6

    def test_l2_normalize_regular_vector(self):
        """Test L2 normalization produces unit magnitude."""
        vector = [3.0, 4.0, 0.0]
        normalized = l2_normalize(vector)

        # Should be [0.6, 0.8, 0.0] (3-4-5 triangle)
        assert abs(normalized[0] - 0.6) < 1e-6
        assert abs(normalized[1] - 0.8) < 1e-6

        # Check magnitude is 1.0
        magnitude = math.sqrt(sum(x**2 for x in normalized))
        assert abs(magnitude - 1.0) < 1e-6

    def test_l2_normalize_zero_vector(self):
        """Test L2 normalization of zero vector returns zero vector."""
        vector = [0.0, 0.0, 0.0]
        normalized = l2_normalize(vector)

        assert all(x == 0.0 for x in normalized)

    def test_l2_normalize_preserves_direction(self):
        """Test L2 normalization preserves vector direction."""
        vector = [2.0, 2.0, 2.0]
        normalized = l2_normalize(vector)

        # All components should be equal (same direction)
        assert abs(normalized[0] - normalized[1]) < 1e-6
        assert abs(normalized[1] - normalized[2]) < 1e-6


class TestL1Normalize:
    """Tests for L1 normalization."""

    def test_l1_normalize_unit_vector(self):
        """Test L1 normalization of unit vector."""
        vector = [1.0, 0.0, 0.0]
        normalized = l1_normalize(vector)

        assert abs(normalized[0] - 1.0) < 1e-6
        assert abs(sum(abs(x) for x in normalized) - 1.0) < 1e-6

    def test_l1_normalize_regular_vector(self):
        """Test L1 normalization produces unit L1 norm."""
        vector = [1.0, 2.0, 3.0]
        normalized = l1_normalize(vector)

        # L1 norm should be 1.0
        l1_norm = sum(abs(x) for x in normalized)
        assert abs(l1_norm - 1.0) < 1e-6

    def test_l1_normalize_zero_vector(self):
        """Test L1 normalization of zero vector returns zero vector."""
        vector = [0.0, 0.0, 0.0]
        normalized = l1_normalize(vector)

        assert all(x == 0.0 for x in normalized)


class TestMaxNormalize:
    """Tests for max normalization."""

    def test_max_normalize_regular_vector(self):
        """Test max normalization scales by max absolute value."""
        vector = [1.0, 2.0, 4.0]
        normalized = max_normalize(vector)

        # Should be scaled by 1/4
        assert abs(normalized[0] - 0.25) < 1e-6
        assert abs(normalized[1] - 0.5) < 1e-6
        assert abs(normalized[2] - 1.0) < 1e-6

    def test_max_normalize_negative_values(self):
        """Test max normalization with negative values."""
        vector = [-4.0, 2.0, 1.0]
        normalized = max_normalize(vector)

        # Should be scaled by 1/4 (abs max is 4)
        assert abs(normalized[0] - (-1.0)) < 1e-6
        assert abs(normalized[1] - 0.5) < 1e-6

    def test_max_normalize_zero_vector(self):
        """Test max normalization of zero vector returns zero vector."""
        vector = [0.0, 0.0, 0.0]
        normalized = max_normalize(vector)

        assert all(x == 0.0 for x in normalized)


class TestStandardize:
    """Tests for vector standardization."""

    def test_standardize_regular_vector(self):
        """Test standardization produces zero mean and unit variance."""
        vector = [1.0, 2.0, 3.0, 4.0, 5.0]
        standardized = standardize_vector(vector)

        # Mean should be close to 0
        mean = sum(standardized) / len(standardized)
        assert abs(mean) < 1e-6

        # Variance should be close to 1
        variance = sum((x - mean) ** 2 for x in standardized) / len(standardized)
        assert abs(variance - 1.0) < 1e-6

    def test_standardize_constant_vector(self):
        """Test standardization of constant vector returns zero vector."""
        vector = [5.0, 5.0, 5.0]
        standardized = standardize_vector(vector)

        assert all(x == 0.0 for x in standardized)


class TestClipVector:
    """Tests for vector clipping."""

    def test_clip_vector_within_range(self):
        """Test clipping vector already within range."""
        vector = [0.5, 0.3, -0.2]
        clipped = clip_vector(vector, min_val=-1.0, max_val=1.0)

        assert clipped == vector

    def test_clip_vector_exceeds_max(self):
        """Test clipping vector exceeding max value."""
        vector = [0.5, 1.5, -0.2]
        clipped = clip_vector(vector, min_val=-1.0, max_val=1.0)

        assert clipped[0] == 0.5
        assert clipped[1] == 1.0  # Clipped to max
        assert clipped[2] == -0.2

    def test_clip_vector_below_min(self):
        """Test clipping vector below min value."""
        vector = [0.5, -1.5, -0.2]
        clipped = clip_vector(vector, min_val=-1.0, max_val=1.0)

        assert clipped[0] == 0.5
        assert clipped[1] == -1.0  # Clipped to min
        assert clipped[2] == -0.2


class TestVectorNormalizer:
    """Tests for VectorNormalizer class."""

    def test_normalize_l2(self):
        """Test normalize with L2 normalization."""
        vector = [3.0, 4.0, 0.0]
        normalized = VectorNormalizer.normalize(vector, norm_type=NormalizationType.L2)

        magnitude = math.sqrt(sum(x**2 for x in normalized))
        assert abs(magnitude - 1.0) < 1e-6

    def test_normalize_l1(self):
        """Test normalize with L1 normalization."""
        vector = [1.0, 2.0, 3.0]
        normalized = VectorNormalizer.normalize(vector, norm_type=NormalizationType.L1)

        l1_norm = sum(abs(x) for x in normalized)
        assert abs(l1_norm - 1.0) < 1e-6

    def test_normalize_max(self):
        """Test normalize with max normalization."""
        vector = [1.0, 2.0, 4.0]
        normalized = VectorNormalizer.normalize(vector, norm_type=NormalizationType.MAX)

        assert abs(max(abs(x) for x in normalized) - 1.0) < 1e-6

    def test_normalize_invalid_type(self):
        """Test normalize with invalid type raises error."""
        vector = [1.0, 2.0, 3.0]

        with pytest.raises(ValueError, match="Unknown normalization type"):
            VectorNormalizer.normalize(vector, norm_type="invalid")  # type: ignore

    def test_batch_normalize(self):
        """Test batch normalization."""
        vectors = [
            [3.0, 4.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 5.0, 12.0],
        ]

        normalized = VectorNormalizer.batch_normalize(
            vectors, norm_type=NormalizationType.L2
        )

        assert len(normalized) == 3
        for vec in normalized:
            magnitude = math.sqrt(sum(x**2 for x in vec))
            assert abs(magnitude - 1.0) < 1e-6 or all(x == 0.0 for x in vec)

    def test_is_normalized_true(self):
        """Test is_normalized returns True for normalized vector."""
        vector = [0.6, 0.8, 0.0]  # Already L2 normalized

        assert VectorNormalizer.is_normalized(vector, norm_type=NormalizationType.L2)

    def test_is_normalized_false(self):
        """Test is_normalized returns False for non-normalized vector."""
        vector = [3.0, 4.0, 0.0]  # Not normalized

        assert not VectorNormalizer.is_normalized(
            vector, norm_type=NormalizationType.L2
        )

    def test_safe_normalize(self):
        """Test safe_normalize handles zero vectors."""
        zero_vector = [0.0, 0.0, 0.0]
        normalized = VectorNormalizer.safe_normalize(
            zero_vector, norm_type=NormalizationType.L2
        )

        assert all(x == 0.0 for x in normalized)

        regular_vector = [3.0, 4.0, 0.0]
        normalized = VectorNormalizer.safe_normalize(
            regular_vector, norm_type=NormalizationType.L2
        )

        magnitude = math.sqrt(sum(x**2 for x in normalized))
        assert abs(magnitude - 1.0) < 1e-6
