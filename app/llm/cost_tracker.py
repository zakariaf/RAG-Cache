"""
LLM cost tracking.

Sandi Metz Principles:
- Single Responsibility: Track and report LLM costs
- Small methods: Each method < 10 lines
- Clear naming: Self-documenting code
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from app.llm.cost_calculator import CostCalculator
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CostEntry:
    """Single cost entry for tracking."""

    timestamp: datetime
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: float


@dataclass
class CostSummary:
    """Summary of costs."""

    total_cost: float
    total_requests: int
    total_tokens: int
    provider_costs: Dict[str, float] = field(default_factory=dict)
    model_costs: Dict[str, float] = field(default_factory=dict)


class LLMCostTracker:
    """
    Track LLM API costs in real-time.

    Records cost data for analysis and reporting.
    """

    def __init__(self, cost_calculator: CostCalculator | None = None):
        """
        Initialize cost tracker.

        Args:
            cost_calculator: Cost calculator instance (creates default if None)
        """
        self._calculator = cost_calculator or CostCalculator()
        self._entries: List[CostEntry] = []

    def track_request(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Track cost for a request.

        Args:
            provider: Provider name
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Cost for this request
        """
        cost = self._calculator.calculate(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
        )

        entry = CostEntry(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
        )

        self._entries.append(entry)

        logger.info(
            "Tracked request cost",
            provider=provider,
            model=model,
            tokens=prompt_tokens + completion_tokens,
            cost=cost,
        )

        return cost

    def get_summary(self) -> CostSummary:
        """
        Get cost summary.

        Returns:
            Summary of all tracked costs
        """
        if not self._entries:
            return CostSummary(
                total_cost=0.0,
                total_requests=0,
                total_tokens=0,
            )

        total_cost = sum(e.cost for e in self._entries)
        total_tokens = sum(e.prompt_tokens + e.completion_tokens for e in self._entries)

        provider_costs = self._calculate_provider_costs()
        model_costs = self._calculate_model_costs()

        return CostSummary(
            total_cost=total_cost,
            total_requests=len(self._entries),
            total_tokens=total_tokens,
            provider_costs=provider_costs,
            model_costs=model_costs,
        )

    def _calculate_provider_costs(self) -> Dict[str, float]:
        """Calculate costs grouped by provider."""
        costs: Dict[str, float] = {}

        for entry in self._entries:
            costs[entry.provider] = costs.get(entry.provider, 0.0) + entry.cost

        return costs

    def _calculate_model_costs(self) -> Dict[str, float]:
        """Calculate costs grouped by model."""
        costs: Dict[str, float] = {}

        for entry in self._entries:
            costs[entry.model] = costs.get(entry.model, 0.0) + entry.cost

        return costs

    def get_entries_by_provider(self, provider: str) -> List[CostEntry]:
        """
        Get entries for specific provider.

        Args:
            provider: Provider name

        Returns:
            List of cost entries for provider
        """
        return [e for e in self._entries if e.provider == provider]

    def get_entries_by_model(self, model: str) -> List[CostEntry]:
        """
        Get entries for specific model.

        Args:
            model: Model name

        Returns:
            List of cost entries for model
        """
        return [e for e in self._entries if e.model == model]

    def get_total_cost(self) -> float:
        """
        Get total cost across all requests.

        Returns:
            Total cost in dollars
        """
        return sum(e.cost for e in self._entries)

    def get_total_tokens(self) -> int:
        """
        Get total tokens across all requests.

        Returns:
            Total token count
        """
        return sum(e.prompt_tokens + e.completion_tokens for e in self._entries)

    def get_request_count(self) -> int:
        """
        Get total number of tracked requests.

        Returns:
            Number of requests
        """
        return len(self._entries)

    def reset(self) -> None:
        """Clear all tracked entries."""
        self._entries.clear()
        logger.info("Cost tracker reset")

    def get_all_entries(self) -> List[CostEntry]:
        """
        Get all cost entries.

        Returns:
            List of all cost entries
        """
        return self._entries.copy()
