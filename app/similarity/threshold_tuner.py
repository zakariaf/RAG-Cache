"""
Semantic similarity threshold tuning utilities.

Sandi Metz Principles:
- Single Responsibility: Threshold optimization
- Small methods: Each analysis isolated
- Clear naming: Descriptive method names
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ThresholdOptimizationGoal(str, Enum):
    """Optimization goals for threshold tuning."""

    PRECISION = "precision"  # Minimize false positives
    RECALL = "recall"  # Minimize false negatives
    F1_SCORE = "f1_score"  # Balance precision and recall
    BALANCED = "balanced"  # Equal weight to precision and recall


class UseCase(str, Enum):
    """Common use cases with different threshold requirements."""

    EXACT_MATCH = "exact_match"  # Strict matching (high threshold)
    CACHE_HIT = "cache_hit"  # Balance between hits and accuracy
    SIMILAR_CONTENT = "similar_content"  # Broad matching (lower threshold)
    DEDUPLICATION = "deduplication"  # Avoid duplicates (moderate threshold)


@dataclass
class ThresholdMetrics:
    """Metrics for threshold evaluation."""

    threshold: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        """Calculate precision (TP / (TP + FP))."""
        denominator = self.true_positives + self.false_positives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def recall(self) -> float:
        """Calculate recall (TP / (TP + FN))."""
        denominator = self.true_positives + self.false_negatives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def f1_score(self) -> float:
        """Calculate F1 score (harmonic mean of precision and recall)."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    @property
    def accuracy(self) -> float:
        """Calculate accuracy ((TP + TN) / Total)."""
        total = (
            self.true_positives
            + self.false_positives
            + self.true_negatives
            + self.false_negatives
        )
        if total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / total

    def __str__(self) -> str:
        """Format metrics as readable string."""
        return (
            f"Threshold: {self.threshold:.3f}\n"
            f"  Precision: {self.precision:.3f}\n"
            f"  Recall: {self.recall:.3f}\n"
            f"  F1 Score: {self.f1_score:.3f}\n"
            f"  Accuracy: {self.accuracy:.3f}\n"
            f"  TP: {self.true_positives} | FP: {self.false_positives}\n"
            f"  TN: {self.true_negatives} | FN: {self.false_negatives}"
        )


@dataclass
class ThresholdRecommendation:
    """Recommended threshold with justification."""

    threshold: float
    use_case: UseCase
    metrics: ThresholdMetrics
    reasoning: str
    confidence: float
    alternative_thresholds: Dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        """Generate recommendation summary."""
        lines = [
            f"\nThreshold Recommendation for {self.use_case.value}:",
            f"  Recommended Threshold: {self.threshold:.3f}",
            f"  Confidence: {self.confidence:.1%}",
            "\nReasoning:",
            f"  {self.reasoning}",
            "\nExpected Performance:",
            f"{self.metrics}",
        ]

        if self.alternative_thresholds:
            lines.append("\nAlternative Thresholds:")
            for name, value in self.alternative_thresholds.items():
                lines.append(f"  {name}: {value:.3f}")

        return "\n".join(lines)


class ThresholdTuner:
    """
    Utilities for tuning similarity thresholds.

    Analyzes test data to recommend optimal thresholds.
    """

    # Default recommended thresholds by use case
    DEFAULT_THRESHOLDS = {
        UseCase.EXACT_MATCH: 0.95,
        UseCase.CACHE_HIT: 0.85,
        UseCase.SIMILAR_CONTENT: 0.70,
        UseCase.DEDUPLICATION: 0.80,
    }

    @staticmethod
    def evaluate_threshold(
        scores: List[float],
        ground_truth: List[bool],
        threshold: float,
    ) -> ThresholdMetrics:
        """
        Evaluate threshold performance.

        Args:
            scores: Similarity scores
            ground_truth: True labels (True = should match)
            threshold: Threshold to evaluate

        Returns:
            ThresholdMetrics with performance data

        Raises:
            ValueError: If scores and ground_truth have different lengths
        """
        if len(scores) != len(ground_truth):
            raise ValueError(
                f"Scores and ground_truth must have same length: "
                f"{len(scores)} != {len(ground_truth)}"
            )

        tp = fp = tn = fn = 0

        for score, is_match in zip(scores, ground_truth):
            predicted_match = score >= threshold

            if predicted_match and is_match:
                tp += 1
            elif predicted_match and not is_match:
                fp += 1
            elif not predicted_match and not is_match:
                tn += 1
            else:
                fn += 1

        return ThresholdMetrics(
            threshold=threshold,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
        )

    @classmethod
    def find_optimal_threshold(
        cls,
        scores: List[float],
        ground_truth: List[bool],
        goal: ThresholdOptimizationGoal = ThresholdOptimizationGoal.F1_SCORE,
        min_threshold: float = 0.5,
        max_threshold: float = 0.99,
        step: float = 0.01,
    ) -> Tuple[float, ThresholdMetrics]:
        """
        Find optimal threshold using grid search.

        Args:
            scores: Similarity scores
            ground_truth: True labels
            goal: Optimization goal
            min_threshold: Minimum threshold to test
            max_threshold: Maximum threshold to test
            step: Step size for grid search

        Returns:
            Tuple of (optimal_threshold, metrics)
        """
        best_threshold = min_threshold
        best_metrics = None
        best_score = 0.0

        current = min_threshold
        while current <= max_threshold:
            metrics = cls.evaluate_threshold(scores, ground_truth, current)

            if goal == ThresholdOptimizationGoal.PRECISION:
                score = metrics.precision
            elif goal == ThresholdOptimizationGoal.RECALL:
                score = metrics.recall
            elif goal == ThresholdOptimizationGoal.F1_SCORE:
                score = metrics.f1_score
            else:  # BALANCED
                score = (metrics.precision + metrics.recall) / 2

            if score > best_score:
                best_score = score
                best_threshold = current
                best_metrics = metrics

            current += step

        logger.info(
            "Optimal threshold found",
            threshold=best_threshold,
            goal=goal.value,
            score=best_score,
        )

        return best_threshold, best_metrics

    @classmethod
    def recommend_threshold(
        cls,
        use_case: UseCase,
        scores: List[float] = None,
        ground_truth: List[bool] = None,
    ) -> ThresholdRecommendation:
        """
        Recommend threshold for specific use case.

        Args:
            use_case: Target use case
            scores: Optional test scores for tuning
            ground_truth: Optional ground truth labels

        Returns:
            ThresholdRecommendation with detailed analysis
        """
        if scores is not None and ground_truth is not None:
            # Tune based on provided data
            goal_map = {
                UseCase.EXACT_MATCH: ThresholdOptimizationGoal.PRECISION,
                UseCase.CACHE_HIT: ThresholdOptimizationGoal.F1_SCORE,
                UseCase.SIMILAR_CONTENT: ThresholdOptimizationGoal.RECALL,
                UseCase.DEDUPLICATION: ThresholdOptimizationGoal.F1_SCORE,
            }

            goal = goal_map.get(use_case, ThresholdOptimizationGoal.F1_SCORE)
            threshold, metrics = cls.find_optimal_threshold(scores, ground_truth, goal)

            # Calculate alternatives
            alt_thresholds = {}
            for alt_goal in ThresholdOptimizationGoal:
                if alt_goal != goal:
                    alt_thresh, _ = cls.find_optimal_threshold(
                        scores, ground_truth, alt_goal
                    )
                    alt_thresholds[alt_goal.value] = alt_thresh

            confidence = metrics.f1_score
        else:
            # Use default threshold
            threshold = cls.DEFAULT_THRESHOLDS[use_case]
            metrics = ThresholdMetrics(
                threshold=threshold,
                true_positives=0,
                false_positives=0,
                true_negatives=0,
                false_negatives=0,
            )
            alt_thresholds = {
                name.value: thresh
                for name, thresh in cls.DEFAULT_THRESHOLDS.items()
                if name != use_case
            }
            confidence = 0.8

        reasoning = cls._generate_reasoning(use_case, threshold)

        return ThresholdRecommendation(
            threshold=threshold,
            use_case=use_case,
            metrics=metrics,
            reasoning=reasoning,
            confidence=confidence,
            alternative_thresholds=alt_thresholds,
        )

    @staticmethod
    def _generate_reasoning(use_case: UseCase, threshold: float) -> str:
        """Generate reasoning for threshold recommendation."""
        if use_case == UseCase.EXACT_MATCH:
            return (
                f"For exact matching, a high threshold ({threshold:.3f}) minimizes "
                f"false positives, ensuring only nearly identical queries match."
            )
        elif use_case == UseCase.CACHE_HIT:
            return (
                f"For cache hits, threshold {threshold:.3f} balances between "
                f"cache effectiveness and accuracy, optimizing for F1 score."
            )
        elif use_case == UseCase.SIMILAR_CONTENT:
            return (
                f"For similar content detection, a moderate threshold "
                f"({threshold:.3f}) allows broader matching while "
                f"maintaining relevance."
            )
        elif use_case == UseCase.DEDUPLICATION:
            return (
                f"For deduplication, threshold {threshold:.3f} prevents duplicates "
                f"while avoiding false merges of distinct content."
            )
        return f"Recommended threshold: {threshold:.3f}"

    @classmethod
    def analyze_threshold_range(
        cls,
        scores: List[float],
        ground_truth: List[bool],
        start: float = 0.5,
        end: float = 0.99,
        step: float = 0.05,
    ) -> List[ThresholdMetrics]:
        """
        Analyze performance across threshold range.

        Args:
            scores: Similarity scores
            ground_truth: True labels
            start: Start threshold
            end: End threshold
            step: Step size

        Returns:
            List of ThresholdMetrics for each threshold
        """
        results = []
        current = start

        while current <= end:
            metrics = cls.evaluate_threshold(scores, ground_truth, current)
            results.append(metrics)
            current += step

        return results

    @staticmethod
    def format_analysis_report(metrics_list: List[ThresholdMetrics]) -> str:
        """
        Format analysis report for threshold range.

        Args:
            metrics_list: List of metrics to report

        Returns:
            Formatted report string
        """
        lines = [
            "\nThreshold Analysis Report",
            "=" * 80,
            f"{'Threshold':<12} {'Precision':<12} {'Recall':<12} "
            f"{'F1 Score':<12} {'Accuracy':<12}",
            "-" * 80,
        ]

        for metrics in metrics_list:
            lines.append(
                f"{metrics.threshold:<12.3f} {metrics.precision:<12.3f} "
                f"{metrics.recall:<12.3f} {metrics.f1_score:<12.3f} "
                f"{metrics.accuracy:<12.3f}"
            )

        return "\n".join(lines)

    @classmethod
    def get_threshold_for_use_case(cls, use_case: UseCase) -> float:
        """
        Get recommended threshold for use case.

        Args:
            use_case: Target use case

        Returns:
            Recommended threshold value
        """
        return cls.DEFAULT_THRESHOLDS.get(use_case, 0.85)


# Convenience functions
def tune_threshold(
    scores: List[float],
    ground_truth: List[bool],
    goal: ThresholdOptimizationGoal = ThresholdOptimizationGoal.F1_SCORE,
) -> float:
    """
    Quick threshold tuning.

    Args:
        scores: Similarity scores
        ground_truth: True labels
        goal: Optimization goal

    Returns:
        Optimal threshold
    """
    threshold, _ = ThresholdTuner.find_optimal_threshold(scores, ground_truth, goal)
    return threshold


def get_cache_threshold() -> float:
    """Get recommended threshold for cache hits."""
    return ThresholdTuner.get_threshold_for_use_case(UseCase.CACHE_HIT)


def get_exact_match_threshold() -> float:
    """Get recommended threshold for exact matching."""
    return ThresholdTuner.get_threshold_for_use_case(UseCase.EXACT_MATCH)


def evaluate_threshold_quality(
    scores: List[float], ground_truth: List[bool], threshold: float
) -> ThresholdMetrics:
    """
    Evaluate threshold quality.

    Args:
        scores: Similarity scores
        ground_truth: True labels
        threshold: Threshold to evaluate

    Returns:
        ThresholdMetrics with performance data
    """
    return ThresholdTuner.evaluate_threshold(scores, ground_truth, threshold)
