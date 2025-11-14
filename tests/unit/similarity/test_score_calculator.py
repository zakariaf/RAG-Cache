"""Unit tests for similarity score calculator."""

import pytest
import math

from app.similarity.score_calculator import (
    ScoreCalculator,
    ScoreInterpretation,
    cosine_similarity,
    euclidean_distance,
    interpret_cosine_score,
)


class TestCosineSimilarity:
    """Tests for cosine_similarity function."""

    def test_identical_vectors(self):
        """Test cosine similarity of identical vectors is 1.0."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]

        score = cosine_similarity(vec1, vec2)

        assert abs(score - 1.0) < 1e-6

    def test_opposite_vectors(self):
        """Test cosine similarity of opposite vectors is -1.0."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]

        score = cosine_similarity(vec1, vec2)

        assert abs(score - (-1.0)) < 1e-6

    def test_orthogonal_vectors(self):
        """Test cosine similarity of orthogonal vectors is 0.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        score = cosine_similarity(vec1, vec2)

        assert abs(score - 0.0) < 1e-6

    def test_zero_vector(self):
        """Test cosine similarity with zero vector is 0.0."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [0.0, 0.0, 0.0]

        score = cosine_similarity(vec1, vec2)

        assert score == 0.0

    def test_mismatched_dimensions(self):
        """Test cosine similarity with mismatched dimensions raises error."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]

        with pytest.raises(ValueError, match="must have same dimensions"):
            cosine_similarity(vec1, vec2)

    def test_empty_vectors(self):
        """Test cosine similarity with empty vectors raises error."""
        vec1 = []
        vec2 = []

        with pytest.raises(ValueError, match="must have same dimensions"):
            cosine_similarity(vec1, vec2)


class TestEuclideanDistance:
    """Tests for euclidean_distance function."""

    def test_identical_vectors(self):
        """Test euclidean distance of identical vectors is 0.0."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]

        dist = euclidean_distance(vec1, vec2)

        assert abs(dist - 0.0) < 1e-6

    def test_known_distance(self):
        """Test euclidean distance with known values."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [3.0, 4.0, 0.0]

        dist = euclidean_distance(vec1, vec2)

        assert abs(dist - 5.0) < 1e-6  # 3-4-5 triangle

    def test_unit_distance(self):
        """Test euclidean distance with unit vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        dist = euclidean_distance(vec1, vec2)

        assert abs(dist - math.sqrt(2)) < 1e-6

    def test_mismatched_dimensions(self):
        """Test euclidean distance with mismatched dimensions raises error."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]

        with pytest.raises(ValueError, match="must have same dimensions"):
            euclidean_distance(vec1, vec2)


class TestScoreInterpretation:
    """Tests for interpret_cosine_score function."""

    def test_exact_match(self):
        """Test interpretation of exact match score."""
        result = interpret_cosine_score(1.0)

        assert result == ScoreInterpretation.EXACT

    def test_very_high_match(self):
        """Test interpretation of very high match score."""
        result = interpret_cosine_score(0.95)

        assert result == ScoreInterpretation.VERY_HIGH

    def test_high_match(self):
        """Test interpretation of high match score."""
        result = interpret_cosine_score(0.88)

        assert result == ScoreInterpretation.HIGH

    def test_moderate_match(self):
        """Test interpretation of moderate match score."""
        result = interpret_cosine_score(0.75)

        assert result == ScoreInterpretation.MODERATE

    def test_low_match(self):
        """Test interpretation of low match score."""
        result = interpret_cosine_score(0.55)

        assert result == ScoreInterpretation.LOW

    def test_very_low_match(self):
        """Test interpretation of very low match score."""
        result = interpret_cosine_score(0.25)

        assert result == ScoreInterpretation.VERY_LOW


class TestScoreCalculator:
    """Tests for ScoreCalculator class."""

    def test_calculate_cosine_similarity(self):
        """Test calculate method with cosine similarity."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        score = ScoreCalculator.calculate(vec1, vec2, metric="cosine")

        assert abs(score - 1.0) < 1e-6

    def test_calculate_euclidean_distance(self):
        """Test calculate method with euclidean distance."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        score = ScoreCalculator.calculate(vec1, vec2, metric="euclidean")

        assert abs(score - 1.0) < 1e-6

    def test_calculate_invalid_metric(self):
        """Test calculate method with invalid metric raises error."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]

        with pytest.raises(ValueError, match="Unknown metric"):
            ScoreCalculator.calculate(vec1, vec2, metric="invalid")

    def test_is_match_above_threshold(self):
        """Test is_match returns True above threshold."""
        result = ScoreCalculator.is_match(0.90, threshold=0.85)

        assert result is True

    def test_is_match_below_threshold(self):
        """Test is_match returns False below threshold."""
        result = ScoreCalculator.is_match(0.80, threshold=0.85)

        assert result is False

    def test_is_match_exact_threshold(self):
        """Test is_match returns True at exact threshold."""
        result = ScoreCalculator.is_match(0.85, threshold=0.85)

        assert result is True

    def test_normalize_cosine_score(self):
        """Test normalize_score with cosine similarity."""
        # Cosine already in 0-1 range
        normalized = ScoreCalculator.normalize_score(0.85, metric="cosine")

        assert abs(normalized - 0.85) < 1e-6

    def test_normalize_euclidean_score(self):
        """Test normalize_score with euclidean distance."""
        # Euclidean converted to similarity
        normalized = ScoreCalculator.normalize_score(0.0, metric="euclidean")

        assert abs(normalized - 1.0) < 1e-6

    def test_get_interpretation(self):
        """Test get_interpretation method."""
        interpretation = ScoreCalculator.get_interpretation(0.95)

        assert interpretation == ScoreInterpretation.VERY_HIGH
        assert interpretation.value == "very_high"
