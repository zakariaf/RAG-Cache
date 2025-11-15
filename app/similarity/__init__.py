"""
Similarity calculation and threshold tuning utilities.

This module provides tools for vector similarity computation,
score interpretation, and threshold optimization.
"""

from app.similarity.score_calculator import (
    ScoreCalculator,
    ScoreInterpretation,
    SimilarityLevel,
    SimilarityScoreCalculator,
    cosine_similarity,
    euclidean_distance,
    interpret_cosine_score,
)
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
from app.similarity.vector_normalizer import (
    NormalizationType,
    VectorNormalizer,
    clip_vector,
    l1_normalize,
    l2_normalize,
    max_normalize,
    standardize_vector,
)

__all__ = [
    # Score calculator
    "SimilarityScoreCalculator",
    "ScoreCalculator",
    "SimilarityLevel",
    "ScoreInterpretation",
    "cosine_similarity",
    "euclidean_distance",
    "interpret_cosine_score",
    # Threshold tuner
    "ThresholdTuner",
    "ThresholdMetrics",
    "ThresholdRecommendation",
    "ThresholdOptimizationGoal",
    "UseCase",
    "tune_threshold",
    "get_cache_threshold",
    "get_exact_match_threshold",
    "evaluate_threshold_quality",
    # Vector normalizer
    "VectorNormalizer",
    "NormalizationType",
    "l1_normalize",
    "l2_normalize",
    "max_normalize",
    "standardize_vector",
    "clip_vector",
]
