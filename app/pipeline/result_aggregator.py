"""
Result Aggregation.

Aggregates results from multiple queries or sources.

Sandi Metz Principles:
- Single Responsibility: Result aggregation
- Composable: Works with various result types
- Configurable: Multiple aggregation strategies
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.models.response import CacheInfo, QueryResponse, UsageMetrics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AggregationStrategy(str, Enum):
    """Strategy for aggregating results."""

    FIRST = "first"  # Use first successful result
    BEST = "best"  # Use highest quality result
    MERGE = "merge"  # Merge all results
    VOTE = "vote"  # Majority voting


@dataclass
class AggregatedResult:
    """Result of aggregation."""

    responses: List[QueryResponse]
    selected_response: Optional[QueryResponse]
    strategy_used: AggregationStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        """Number of responses aggregated."""
        return len(self.responses)

    @property
    def success(self) -> bool:
        """Check if aggregation was successful."""
        return self.selected_response is not None


@dataclass
class BatchResult:
    """Result of batch query processing."""

    results: List[Optional[QueryResponse]]
    successful: int
    failed: int
    total_latency_ms: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.successful + self.failed
        if total == 0:
            return 0.0
        return self.successful / total

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.successful == 0:
            return 0.0
        return self.total_latency_ms / self.successful


class ResultAggregator:
    """
    Aggregates query results.

    Supports multiple aggregation strategies.
    """

    def __init__(
        self,
        strategy: AggregationStrategy = AggregationStrategy.FIRST,
        quality_scorer: Optional[Callable[[QueryResponse], float]] = None,
    ):
        """
        Initialize aggregator.

        Args:
            strategy: Aggregation strategy
            quality_scorer: Optional function to score response quality
        """
        self._strategy = strategy
        self._quality_scorer = quality_scorer or self._default_quality_score

    def aggregate(self, responses: List[QueryResponse]) -> AggregatedResult:
        """
        Aggregate multiple responses.

        Args:
            responses: List of responses

        Returns:
            AggregatedResult
        """
        if not responses:
            return AggregatedResult(
                responses=[],
                selected_response=None,
                strategy_used=self._strategy,
            )

        selected = None

        if self._strategy == AggregationStrategy.FIRST:
            selected = self._select_first(responses)
        elif self._strategy == AggregationStrategy.BEST:
            selected = self._select_best(responses)
        elif self._strategy == AggregationStrategy.MERGE:
            selected = self._merge_responses(responses)
        elif self._strategy == AggregationStrategy.VOTE:
            selected = self._vote_responses(responses)

        return AggregatedResult(
            responses=responses,
            selected_response=selected,
            strategy_used=self._strategy,
            metadata={
                "count": len(responses),
                "selected_index": responses.index(selected)
                if selected in responses
                else -1,
            },
        )

    def _select_first(self, responses: List[QueryResponse]) -> QueryResponse:
        """Select first response."""
        return responses[0]

    def _select_best(self, responses: List[QueryResponse]) -> QueryResponse:
        """Select best quality response."""
        scored = [(r, self._quality_scorer(r)) for r in responses]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def _merge_responses(self, responses: List[QueryResponse]) -> QueryResponse:
        """Merge multiple responses into one."""
        # Simple merge: concatenate responses with separator
        merged_text = "\n---\n".join(r.response for r in responses)

        # Aggregate usage
        total_prompt = sum(r.usage.prompt_tokens for r in responses)
        total_completion = sum(r.usage.completion_tokens for r in responses)

        # Use first response as template
        first = responses[0]
        return QueryResponse(
            response=merged_text,
            provider="merged",
            model=first.model,
            usage=UsageMetrics.create(total_prompt, total_completion),
            cache_info=CacheInfo.miss(),
            latency_ms=max(r.latency_ms for r in responses),
        )

    def _vote_responses(self, responses: List[QueryResponse]) -> QueryResponse:
        """Select response by majority voting (simplified)."""
        # For now, just return the most common response
        # In practice, would use semantic similarity
        response_texts = [r.response for r in responses]
        most_common = max(set(response_texts), key=response_texts.count)

        for r in responses:
            if r.response == most_common:
                return r

        return responses[0]

    @staticmethod
    def _default_quality_score(response: QueryResponse) -> float:
        """
        Calculate default quality score.

        Higher is better.
        """
        score = 0.0

        # Prefer cache hits
        if response.from_cache:
            score += 10.0

        # Prefer lower latency
        if response.latency_ms < 100:
            score += 5.0
        elif response.latency_ms < 500:
            score += 3.0
        elif response.latency_ms < 1000:
            score += 1.0

        # Prefer appropriate response length
        length = len(response.response)
        if 100 <= length <= 2000:
            score += 2.0

        return score


class BatchAggregator:
    """
    Aggregates batch processing results.

    Provides summary statistics.
    """

    def aggregate_batch(self, results: List[Optional[QueryResponse]]) -> BatchResult:
        """
        Aggregate batch results.

        Args:
            results: List of responses (None for failures)

        Returns:
            BatchResult with statistics
        """
        successful = sum(1 for r in results if r is not None)
        failed = len(results) - successful

        total_latency = sum(r.latency_ms for r in results if r is not None)

        return BatchResult(
            results=results,
            successful=successful,
            failed=failed,
            total_latency_ms=total_latency,
        )

    def summarize(self, batch_result: BatchResult) -> Dict[str, Any]:
        """
        Create summary of batch result.

        Args:
            batch_result: Batch processing result

        Returns:
            Summary dictionary
        """
        cache_hits = sum(
            1 for r in batch_result.results if r is not None and r.from_cache
        )

        return {
            "total": len(batch_result.results),
            "successful": batch_result.successful,
            "failed": batch_result.failed,
            "success_rate": round(batch_result.success_rate, 4),
            "cache_hits": cache_hits,
            "avg_latency_ms": round(batch_result.avg_latency_ms, 2),
            "total_latency_ms": round(batch_result.total_latency_ms, 2),
        }
