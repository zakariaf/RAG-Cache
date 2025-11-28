"""
Metrics aggregation and summary generation.

Sandi Metz Principles:
- Single Responsibility: Aggregate and summarize metrics
- Small methods: Each aggregation isolated
- Clear output: Well-structured summaries
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.monitoring.collectors import (
    CacheMetrics,
    LLMMetrics,
    RequestMetrics,
    SystemMetrics,
)
from app.monitoring.prometheus import get_metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AggregatedMetrics:
    """
    Aggregated metrics from all collectors.

    Provides a unified view of system metrics.
    """

    timestamp: float = field(default_factory=time.time)
    request_metrics: Dict[str, Any] = field(default_factory=dict)
    cache_metrics: Dict[str, Any] = field(default_factory=dict)
    llm_metrics: Dict[str, Any] = field(default_factory=dict)
    system_metrics: Dict[str, Any] = field(default_factory=dict)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "requests": self.request_metrics,
            "cache": self.cache_metrics,
            "llm": self.llm_metrics,
            "system": self.system_metrics,
            "custom": self.custom_metrics,
        }

    def to_prometheus_format(self) -> str:
        """Convert to Prometheus text format."""
        lines = []

        # Convert nested metrics to flat Prometheus format
        def flatten(prefix: str, data: Dict, labels: Dict = None):
            labels = labels or {}
            for key, value in data.items():
                if isinstance(value, dict):
                    flatten(f"{prefix}_{key}", value, labels)
                elif isinstance(value, (int, float)):
                    label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                    metric_name = f"{prefix}_{key}".replace("-", "_")
                    if label_str:
                        lines.append(f"{metric_name}{{{label_str}}} {value}")
                    else:
                        lines.append(f"{metric_name} {value}")

        flatten("ragcache_aggregated", self.to_dict())
        return "\n".join(lines)


class MetricsAggregator:
    """
    Aggregates metrics from multiple collectors.

    Provides unified metrics view and analysis.
    """

    def __init__(self):
        """Initialize aggregator with collectors."""
        self._request_metrics = RequestMetrics()
        self._cache_metrics = CacheMetrics()
        self._llm_metrics = LLMMetrics()
        self._system_metrics = SystemMetrics()
        self._custom_metrics: Dict[str, Any] = {}
        self._history: List[AggregatedMetrics] = []
        self._max_history = 1000

    @property
    def requests(self) -> RequestMetrics:
        """Get request metrics collector."""
        return self._request_metrics

    @property
    def cache(self) -> CacheMetrics:
        """Get cache metrics collector."""
        return self._cache_metrics

    @property
    def llm(self) -> LLMMetrics:
        """Get LLM metrics collector."""
        return self._llm_metrics

    @property
    def system(self) -> SystemMetrics:
        """Get system metrics collector."""
        return self._system_metrics

    def record_custom(self, name: str, value: Any) -> None:
        """Record a custom metric."""
        self._custom_metrics[name] = value

    def aggregate(self) -> AggregatedMetrics:
        """
        Aggregate all metrics into a single snapshot.

        Returns:
            Aggregated metrics snapshot
        """
        aggregated = AggregatedMetrics(
            timestamp=time.time(),
            request_metrics=self._request_metrics.to_dict(),
            cache_metrics=self._cache_metrics.to_dict(),
            llm_metrics=self._llm_metrics.to_dict(),
            system_metrics=self._system_metrics.to_dict(),
            custom_metrics=self._custom_metrics.copy(),
        )

        # Store in history
        self._history.append(aggregated)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return aggregated

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics.

        Returns:
            Summary dictionary
        """
        return {
            "requests": self._request_metrics.to_dict(),
            "cache": self._cache_metrics.to_dict(),
            "llm": self._llm_metrics.to_dict(),
            "system": self._system_metrics.to_dict(),
            "custom": self._custom_metrics,
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get health-focused summary.

        Returns:
            Health summary dictionary
        """
        return {
            "status": self._calculate_health_status(),
            "uptime_seconds": self._system_metrics.uptime_seconds,
            "request_rate": self._calculate_request_rate(),
            "error_rate": self._request_metrics.error_rate,
            "cache_hit_rate": self._cache_metrics.hit_rate,
            "llm_success_rate": self._llm_metrics.success_rate,
            "active_requests": self._system_metrics.active_requests,
        }

    def _calculate_health_status(self) -> str:
        """Calculate overall health status."""
        error_rate = self._request_metrics.error_rate
        cache_hit_rate = self._cache_metrics.hit_rate
        llm_success_rate = self._llm_metrics.success_rate

        if error_rate > 0.1:  # More than 10% errors
            return "unhealthy"
        elif error_rate > 0.05 or llm_success_rate < 0.9:
            return "degraded"
        else:
            return "healthy"

    def _calculate_request_rate(self) -> float:
        """Calculate requests per second."""
        uptime = self._system_metrics.uptime_seconds
        if uptime == 0:
            return 0.0
        return self._request_metrics.total_requests / uptime

    def get_time_series(
        self, metric_path: str, duration_seconds: int = 3600
    ) -> List[tuple]:
        """
        Get time series data for a specific metric.

        Args:
            metric_path: Dot-separated path to metric (e.g., "cache.hit_rate")
            duration_seconds: Time window in seconds

        Returns:
            List of (timestamp, value) tuples
        """
        cutoff = time.time() - duration_seconds
        series = []

        for snapshot in self._history:
            if snapshot.timestamp < cutoff:
                continue

            # Navigate to the metric
            value = self._get_nested_value(snapshot.to_dict(), metric_path)
            if value is not None:
                series.append((snapshot.timestamp, value))

        return series

    def _get_nested_value(self, data: Dict, path: str) -> Optional[Any]:
        """Get nested value from dictionary using dot notation."""
        parts = path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def reset(self) -> None:
        """Reset all metrics."""
        self._request_metrics = RequestMetrics()
        self._cache_metrics = CacheMetrics()
        self._llm_metrics = LLMMetrics()
        self._system_metrics = SystemMetrics()
        self._custom_metrics = {}
        self._history = []

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus format."""
        # Sync with global prometheus metrics
        prometheus = get_metrics()

        # Add aggregated metrics
        aggregated = self.aggregate()

        # Combine Prometheus metrics with aggregated
        prometheus_output = prometheus.export_prometheus()
        aggregated_output = aggregated.to_prometheus_format()

        return f"{prometheus_output}\n{aggregated_output}"


# Global aggregator instance
_aggregator: Optional[MetricsAggregator] = None


def get_aggregator() -> MetricsAggregator:
    """Get the global aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = MetricsAggregator()
    return _aggregator
