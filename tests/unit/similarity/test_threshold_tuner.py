"""Unit tests for threshold tuner."""

import pytest

from app.similarity.threshold_tuner import (
    ThresholdMetrics,
    ThresholdOptimizationGoal,
    ThresholdRecommendation,
    ThresholdTuner,
    UseCase,
    evaluate_threshold_quality,
    get_cache_threshold,
    get_exact_match_threshold,
    tune_threshold,
)


class TestThresholdMetrics:
    """Tests for ThresholdMetrics class."""

    def test_metrics_precision_calculation(self):
        """Test precision calculation."""
        metrics = ThresholdMetrics(
            threshold=0.85,
            true_positives=80,
            false_positives=20,
            true_negatives=70,
            false_negatives=30,
        )

        assert metrics.precision == pytest.approx(0.8, abs=0.01)  # 80 / (80 + 20)

    def test_metrics_recall_calculation(self):
        """Test recall calculation."""
        metrics = ThresholdMetrics(
            threshold=0.85,
            true_positives=80,
            false_positives=20,
            true_negatives=70,
            false_negatives=30,
        )

        assert metrics.recall == pytest.approx(0.727, abs=0.01)  # 80 / (80 + 30)

    def test_metrics_f1_score_calculation(self):
        """Test F1 score calculation."""
        metrics = ThresholdMetrics(
            threshold=0.85,
            true_positives=80,
            false_positives=20,
            true_negatives=70,
            false_negatives=30,
        )

        # F1 = 2 * (0.8 * 0.727) / (0.8 + 0.727) ≈ 0.762
        assert metrics.f1_score == pytest.approx(0.762, abs=0.01)

    def test_metrics_accuracy_calculation(self):
        """Test accuracy calculation."""
        metrics = ThresholdMetrics(
            threshold=0.85,
            true_positives=80,
            false_positives=20,
            true_negatives=70,
            false_negatives=30,
        )

        assert metrics.accuracy == pytest.approx(0.75, abs=0.01)  # (80 + 70) / 200

    def test_metrics_zero_division_handling(self):
        """Test handling of zero division."""
        metrics = ThresholdMetrics(
            threshold=0.85,
            true_positives=0,
            false_positives=0,
            true_negatives=0,
            false_negatives=0,
        )

        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1_score == 0.0
        assert metrics.accuracy == 0.0

    def test_metrics_string_representation(self):
        """Test string representation."""
        metrics = ThresholdMetrics(
            threshold=0.85,
            true_positives=80,
            false_positives=20,
            true_negatives=70,
            false_negatives=30,
        )

        string_repr = str(metrics)
        assert "Threshold: 0.850" in string_repr
        assert "Precision:" in string_repr
        assert "Recall:" in string_repr
        assert "F1 Score:" in string_repr


class TestThresholdTuner:
    """Tests for ThresholdTuner class."""

    def test_evaluate_threshold_perfect_classification(self):
        """Test threshold evaluation with perfect classification."""
        scores = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
        ground_truth = [True, True, True, True, False, False, False, False]
        threshold = 0.55

        metrics = ThresholdTuner.evaluate_threshold(scores, ground_truth, threshold)

        assert metrics.true_positives == 4
        assert metrics.false_positives == 0
        assert metrics.true_negatives == 4
        assert metrics.false_negatives == 0
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0

    def test_evaluate_threshold_with_errors(self):
        """Test threshold evaluation with classification errors."""
        scores = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
        ground_truth = [True, False, True, False, True, False]
        threshold = 0.65

        metrics = ThresholdTuner.evaluate_threshold(scores, ground_truth, threshold)

        assert metrics.true_positives == 2  # 0.9 and 0.7 are True
        assert metrics.false_positives == 1  # 0.8 is False but predicted True
        assert metrics.true_negatives == 2  # 0.4 and 0.6 are False
        assert metrics.false_negatives == 1  # 0.5 is True but predicted False

    def test_evaluate_threshold_length_mismatch(self):
        """Test error handling for mismatched lengths."""
        scores = [0.9, 0.8, 0.7]
        ground_truth = [True, False]

        with pytest.raises(ValueError, match="same length"):
            ThresholdTuner.evaluate_threshold(scores, ground_truth, 0.5)

    def test_find_optimal_threshold_for_f1(self):
        """Test finding optimal threshold for F1 score."""
        # Create test data where 0.7 is optimal
        scores = [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.25]
        ground_truth = [True, True, True, True, False, False, False, False]

        threshold, metrics = ThresholdTuner.find_optimal_threshold(
            scores, ground_truth, ThresholdOptimizationGoal.F1_SCORE, 0.5, 0.9, 0.05
        )

        # Optimal should be around 0.60-0.70
        assert 0.55 <= threshold <= 0.75
        assert metrics.f1_score > 0.8

    def test_find_optimal_threshold_for_precision(self):
        """Test finding optimal threshold for precision."""
        scores = [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.25]
        ground_truth = [True, True, True, True, False, False, False, False]

        threshold, metrics = ThresholdTuner.find_optimal_threshold(
            scores, ground_truth, ThresholdOptimizationGoal.PRECISION, 0.5, 0.9, 0.05
        )

        # Higher threshold for precision optimization
        assert threshold >= 0.60
        assert metrics.precision >= 0.8

    def test_find_optimal_threshold_for_recall(self):
        """Test finding optimal threshold for recall."""
        scores = [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.25]
        ground_truth = [True, True, True, True, False, False, False, False]

        threshold, metrics = ThresholdTuner.find_optimal_threshold(
            scores, ground_truth, ThresholdOptimizationGoal.RECALL, 0.5, 0.9, 0.05
        )

        # Lower threshold for recall optimization
        assert threshold <= 0.70
        assert metrics.recall >= 0.9

    def test_recommend_threshold_with_data(self):
        """Test threshold recommendation with test data."""
        scores = [0.95, 0.85, 0.75, 0.65, 0.55, 0.45]
        ground_truth = [True, True, True, False, False, False]

        recommendation = ThresholdTuner.recommend_threshold(
            UseCase.CACHE_HIT, scores, ground_truth
        )

        assert isinstance(recommendation, ThresholdRecommendation)
        assert 0.5 <= recommendation.threshold <= 0.99
        assert recommendation.use_case == UseCase.CACHE_HIT
        assert recommendation.confidence > 0
        assert len(recommendation.reasoning) > 0

    def test_recommend_threshold_without_data(self):
        """Test threshold recommendation using defaults."""
        recommendation = ThresholdTuner.recommend_threshold(UseCase.EXACT_MATCH)

        assert (
            recommendation.threshold
            == ThresholdTuner.DEFAULT_THRESHOLDS[UseCase.EXACT_MATCH]
        )
        assert recommendation.use_case == UseCase.EXACT_MATCH
        assert len(recommendation.alternative_thresholds) > 0

    def test_default_thresholds_ordering(self):
        """Test that default thresholds follow expected ordering."""
        exact = ThresholdTuner.DEFAULT_THRESHOLDS[UseCase.EXACT_MATCH]
        cache = ThresholdTuner.DEFAULT_THRESHOLDS[UseCase.CACHE_HIT]
        dedup = ThresholdTuner.DEFAULT_THRESHOLDS[UseCase.DEDUPLICATION]
        similar = ThresholdTuner.DEFAULT_THRESHOLDS[UseCase.SIMILAR_CONTENT]

        # Exact match should be highest
        assert exact >= cache
        assert exact >= dedup
        assert exact >= similar

        # Similar content should be lowest
        assert similar <= cache
        assert similar <= dedup

    def test_analyze_threshold_range(self):
        """Test threshold range analysis."""
        scores = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
        ground_truth = [True, True, True, False, False, False]

        results = ThresholdTuner.analyze_threshold_range(
            scores, ground_truth, start=0.5, end=0.8, step=0.1
        )

        assert len(results) == 4  # 0.5, 0.6, 0.7, 0.8
        assert all(isinstance(m, ThresholdMetrics) for m in results)
        assert results[0].threshold == pytest.approx(0.5, abs=0.01)
        assert results[-1].threshold == pytest.approx(0.8, abs=0.01)

    def test_format_analysis_report(self):
        """Test report formatting."""
        metrics_list = [
            ThresholdMetrics(
                threshold=0.7,
                true_positives=80,
                false_positives=20,
                true_negatives=70,
                false_negatives=30,
            ),
            ThresholdMetrics(
                threshold=0.8,
                true_positives=70,
                false_positives=10,
                true_negatives=80,
                false_negatives=40,
            ),
        ]

        report = ThresholdTuner.format_analysis_report(metrics_list)

        assert "Threshold Analysis Report" in report
        assert "0.700" in report
        assert "0.800" in report
        assert "Precision" in report
        assert "Recall" in report

    def test_get_threshold_for_use_case(self):
        """Test getting threshold by use case."""
        cache_threshold = ThresholdTuner.get_threshold_for_use_case(UseCase.CACHE_HIT)
        exact_threshold = ThresholdTuner.get_threshold_for_use_case(UseCase.EXACT_MATCH)

        assert cache_threshold == 0.85
        assert exact_threshold == 0.95
        assert exact_threshold > cache_threshold


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_tune_threshold_function(self):
        """Test tune_threshold convenience function."""
        scores = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
        ground_truth = [True, True, True, False, False, False]

        threshold = tune_threshold(scores, ground_truth)

        assert 0.5 <= threshold <= 0.99

    def test_get_cache_threshold(self):
        """Test get_cache_threshold function."""
        threshold = get_cache_threshold()
        assert threshold == 0.85

    def test_get_exact_match_threshold(self):
        """Test get_exact_match_threshold function."""
        threshold = get_exact_match_threshold()
        assert threshold == 0.95

    def test_evaluate_threshold_quality(self):
        """Test evaluate_threshold_quality function."""
        scores = [0.9, 0.8, 0.7, 0.6]
        ground_truth = [True, True, False, False]

        metrics = evaluate_threshold_quality(scores, ground_truth, 0.75)

        assert isinstance(metrics, ThresholdMetrics)
        assert metrics.threshold == 0.75


class TestThresholdRecommendation:
    """Tests for ThresholdRecommendation class."""

    def test_recommendation_summary(self):
        """Test recommendation summary formatting."""
        metrics = ThresholdMetrics(
            threshold=0.85,
            true_positives=80,
            false_positives=20,
            true_negatives=70,
            false_negatives=30,
        )

        recommendation = ThresholdRecommendation(
            threshold=0.85,
            use_case=UseCase.CACHE_HIT,
            metrics=metrics,
            reasoning="Test reasoning",
            confidence=0.9,
            alternative_thresholds={"precision": 0.90, "recall": 0.80},
        )

        summary = recommendation.summary()

        assert "Threshold Recommendation" in summary
        assert "0.850" in summary
        assert "90.0%" in summary
        assert "Test reasoning" in summary
        assert "Alternative Thresholds" in summary


class TestUseCaseThresholds:
    """Tests for use case specific thresholds."""

    def test_exact_match_use_case(self):
        """Test exact match use case has high threshold."""
        threshold = ThresholdTuner.get_threshold_for_use_case(UseCase.EXACT_MATCH)
        assert threshold >= 0.90

    def test_cache_hit_use_case(self):
        """Test cache hit use case has balanced threshold."""
        threshold = ThresholdTuner.get_threshold_for_use_case(UseCase.CACHE_HIT)
        assert 0.80 <= threshold <= 0.90

    def test_similar_content_use_case(self):
        """Test similar content use case has moderate threshold."""
        threshold = ThresholdTuner.get_threshold_for_use_case(UseCase.SIMILAR_CONTENT)
        assert 0.60 <= threshold <= 0.80

    def test_deduplication_use_case(self):
        """Test deduplication use case has moderate-high threshold."""
        threshold = ThresholdTuner.get_threshold_for_use_case(UseCase.DEDUPLICATION)
        assert 0.75 <= threshold <= 0.85


class TestEdgeCases:
    """Tests for edge cases."""

    def test_all_true_positives(self):
        """Test when all predictions are true positives."""
        scores = [0.9, 0.8, 0.7]
        ground_truth = [True, True, True]

        metrics = ThresholdTuner.evaluate_threshold(scores, ground_truth, 0.6)

        assert metrics.true_positives == 3
        assert metrics.false_positives == 0
        assert metrics.true_negatives == 0
        assert metrics.false_negatives == 0
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0

    def test_all_true_negatives(self):
        """Test when all predictions are true negatives."""
        scores = [0.3, 0.2, 0.1]
        ground_truth = [False, False, False]

        metrics = ThresholdTuner.evaluate_threshold(scores, ground_truth, 0.5)

        assert metrics.true_positives == 0
        assert metrics.false_positives == 0
        assert metrics.true_negatives == 3
        assert metrics.false_negatives == 0

    def test_empty_datasets(self):
        """Test with empty datasets."""
        scores = []
        ground_truth = []

        metrics = ThresholdTuner.evaluate_threshold(scores, ground_truth, 0.5)

        assert metrics.true_positives == 0
        assert metrics.false_positives == 0
        assert metrics.true_negatives == 0
        assert metrics.false_negatives == 0

    def test_single_data_point(self):
        """Test with single data point."""
        scores = [0.85]
        ground_truth = [True]

        metrics = ThresholdTuner.evaluate_threshold(scores, ground_truth, 0.80)

        assert metrics.true_positives == 1
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
