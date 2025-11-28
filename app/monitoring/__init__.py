"""
Monitoring & Metrics module.

Provides Prometheus-compatible metrics for observability.
"""

from app.monitoring.aggregator import (
    AggregatedMetrics,
    MetricsAggregator,
)
from app.monitoring.alerts import (
    AlertLevel,
    AlertManager,
    AlertRule,
)
from app.monitoring.collectors import (
    CacheMetrics,
    LLMMetrics,
    RequestMetrics,
    SystemMetrics,
)
from app.monitoring.decorators import (
    track_cache_operation,
    track_latency,
    track_llm_call,
    track_request,
)
from app.monitoring.prometheus import (
    PrometheusMetrics,
    get_metrics,
    metrics_middleware,
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
