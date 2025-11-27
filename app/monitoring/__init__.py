"""
Monitoring & Metrics module.

Provides Prometheus-compatible metrics for observability.
"""

from app.monitoring.prometheus import (
    PrometheusMetrics,
    get_metrics,
    metrics_middleware,
)
from app.monitoring.collectors import (
    RequestMetrics,
    CacheMetrics,
    LLMMetrics,
    SystemMetrics,
)
from app.monitoring.decorators import (
    track_request,
    track_cache_operation,
    track_llm_call,
    track_latency,
)
from app.monitoring.aggregator import (
    MetricsAggregator,
    AggregatedMetrics,
)
from app.monitoring.alerts import (
    AlertRule,
    AlertManager,
    AlertLevel,
)

__all__ = [
    # Prometheus
    "PrometheusMetrics",
    "get_metrics",
    "metrics_middleware",
    # Collectors
    "RequestMetrics",
    "CacheMetrics",
    "LLMMetrics",
    "SystemMetrics",
    # Decorators
    "track_request",
    "track_cache_operation",
    "track_llm_call",
    "track_latency",
    # Aggregator
    "MetricsAggregator",
    "AggregatedMetrics",
    # Alerts
    "AlertRule",
    "AlertManager",
    "AlertLevel",
]

