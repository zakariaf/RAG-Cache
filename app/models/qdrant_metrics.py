"""
Qdrant metrics models.

Sandi Metz Principles:
- Single Responsibility: Metrics modeling
- Small class: Focused data structures
- Clear naming: Descriptive field names
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class QdrantMetrics(BaseModel):
    """
    Qdrant collection metrics.

    Tracks operational statistics.
    """

    # Collection stats
    total_points: int = Field(default=0, ge=0, description="Total points")
    total_vectors: int = Field(default=0, ge=0, description="Total vectors")

    # Operation counters
    searches_performed: int = Field(default=0, ge=0, description="Search count")
    points_added: int = Field(default=0, ge=0, description="Points added")
    points_updated: int = Field(default=0, ge=0, description="Points updated")
    points_deleted: int = Field(default=0, ge=0, description="Points deleted")

    # Performance metrics
    avg_search_time_ms: float = Field(
        default=0.0, ge=0.0, description="Avg search time"
    )
    avg_upload_time_ms: float = Field(
        default=0.0, ge=0.0, description="Avg upload time"
    )

    # Cache metrics
    semantic_hits: int = Field(default=0, ge=0, description="Semantic cache hits")
    semantic_misses: int = Field(default=0, ge=0, description="Semantic cache misses")

    # Error tracking
    errors_count: int = Field(default=0, ge=0, description="Error count")
    last_error: Optional[str] = Field(None, description="Last error message")

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.semantic_hits + self.semantic_misses
        if total == 0:
            return 0.0
        return self.semantic_hits / total

    @property
    def total_operations(self) -> int:
        """Calculate total operations."""
        return (
            self.searches_performed
            + self.points_added
            + self.points_updated
            + self.points_deleted
        )


class OperationMetrics(BaseModel):
    """
    Metrics for a specific operation.

    Tracks timing and success rate.
    """

    operation_name: str = Field(..., description="Operation name")
    total_count: int = Field(default=0, ge=0, description="Total executions")
    success_count: int = Field(default=0, ge=0, description="Successful executions")
    failure_count: int = Field(default=0, ge=0, description="Failed executions")
    total_time_ms: float = Field(
        default=0.0, ge=0.0, description="Total execution time"
    )
    min_time_ms: float = Field(default=0.0, ge=0.0, description="Minimum time")
    max_time_ms: float = Field(default=0.0, ge=0.0, description="Maximum time")

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count

    @property
    def avg_time_ms(self) -> float:
        """Calculate average execution time."""
        if self.total_count == 0:
            return 0.0
        return self.total_time_ms / self.total_count


class SearchMetrics(BaseModel):
    """
    Semantic search specific metrics.

    Tracks search performance and quality.
    """

    total_searches: int = Field(default=0, ge=0, description="Total searches")
    avg_results_per_search: float = Field(
        default=0.0, ge=0.0, description="Avg results"
    )
    avg_search_time_ms: float = Field(
        default=0.0, ge=0.0, description="Avg search time"
    )
    avg_similarity_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Avg similarity"
    )

    # Score distribution
    high_quality_matches: int = Field(default=0, ge=0, description="Score >= 0.9")
    medium_quality_matches: int = Field(
        default=0, ge=0, description="0.7 <= Score < 0.9"
    )
    low_quality_matches: int = Field(default=0, ge=0, description="Score < 0.7")

    @property
    def high_quality_rate(self) -> float:
        """Calculate high quality match rate."""
        total = (
            self.high_quality_matches
            + self.medium_quality_matches
            + self.low_quality_matches
        )
        if total == 0:
            return 0.0
        return self.high_quality_matches / total


class MetricsSummary(BaseModel):
    """
    Complete metrics summary.

    Aggregates all metric types.
    """

    collection_metrics: QdrantMetrics
    search_metrics: SearchMetrics
    operation_metrics: Dict[str, OperationMetrics] = Field(default_factory=dict)
    uptime_seconds: float = Field(default=0.0, ge=0.0, description="Service uptime")

    def to_dict(self) -> Dict:
        """Convert to dictionary for export."""
        return {
            "collection": self.collection_metrics.model_dump(),
            "search": self.search_metrics.model_dump(),
            "operations": {
                name: metrics.model_dump()
                for name, metrics in self.operation_metrics.items()
            },
            "uptime_seconds": self.uptime_seconds,
        }
