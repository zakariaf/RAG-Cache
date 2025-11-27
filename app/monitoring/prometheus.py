"""
Prometheus metrics setup and configuration.

Provides core metrics for monitoring the RAGCache service.

Sandi Metz Principles:
- Single Responsibility: Metrics definition and exposure
- Configurable: Flexible metric configuration
- Observable: All key system aspects measured
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MetricValue:
    """Single metric value with labels."""

    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # gauge, counter, histogram, summary
    help_text: str = ""


@dataclass
class HistogramValue:
    """Histogram metric value."""

    name: str
    buckets: Dict[float, int]  # bucket_le -> count
    sum_value: float
    count: int
    labels: Dict[str, str] = field(default_factory=dict)
    help_text: str = ""


class PrometheusMetrics:
    """
    Prometheus-compatible metrics collection.

    Collects and exposes metrics in Prometheus format.
    """

    def __init__(self):
        """Initialize metrics storage."""
        self._counters: Dict[str, Dict[str, float]] = {}
        self._gauges: Dict[str, Dict[str, float]] = {}
        self._histograms: Dict[str, Dict[str, HistogramValue]] = {}
        self._start_time = time.time()

        # Default histogram buckets (in seconds for latency)
        self._default_buckets = [
            0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0
        ]

        # Initialize core metrics
        self._init_core_metrics()

    def _init_core_metrics(self) -> None:
        """Initialize core application metrics."""
        # Request metrics
        self._register_counter(
            "ragcache_requests_total",
            "Total number of requests processed"
        )
        self._register_counter(
            "ragcache_requests_errors_total",
            "Total number of request errors"
        )
        self._register_histogram(
            "ragcache_request_duration_seconds",
            "Request duration in seconds"
        )

        # Cache metrics
        self._register_counter(
            "ragcache_cache_hits_total",
            "Total number of cache hits"
        )
        self._register_counter(
            "ragcache_cache_misses_total",
            "Total number of cache misses"
        )
        self._register_gauge(
            "ragcache_cache_hit_rate",
            "Current cache hit rate"
        )

        # LLM metrics
        self._register_counter(
            "ragcache_llm_requests_total",
            "Total number of LLM API requests"
        )
        self._register_counter(
            "ragcache_llm_tokens_total",
            "Total tokens processed by LLM"
        )
        self._register_gauge(
            "ragcache_llm_cost_total",
            "Total cost of LLM API calls"
        )
        self._register_histogram(
            "ragcache_llm_latency_seconds",
            "LLM API call latency in seconds"
        )

        # System metrics
        self._register_gauge(
            "ragcache_uptime_seconds",
            "Service uptime in seconds"
        )

    def _register_counter(self, name: str, help_text: str) -> None:
        """Register a counter metric."""
        if name not in self._counters:
            self._counters[name] = {"_help": 0, "_meta": help_text}  # type: ignore

    def _register_gauge(self, name: str, help_text: str) -> None:
        """Register a gauge metric."""
        if name not in self._gauges:
            self._gauges[name] = {"_help": 0, "_meta": help_text}  # type: ignore

    def _register_histogram(self, name: str, help_text: str) -> None:
        """Register a histogram metric."""
        if name not in self._histograms:
            self._histograms[name] = {"_meta": help_text}  # type: ignore

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to string key."""
        if not labels:
            return ""
        sorted_items = sorted(labels.items())
        return ",".join(f'{k}="{v}"' for k, v in sorted_items)

    # Counter operations
    def inc_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter."""
        labels = labels or {}
        key = self._labels_to_key(labels)

        if name not in self._counters:
            self._counters[name] = {}

        full_key = f"{name}{{{key}}}" if key else name
        self._counters[name][full_key] = self._counters[name].get(full_key, 0) + value

    # Gauge operations
    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge value."""
        labels = labels or {}
        key = self._labels_to_key(labels)

        if name not in self._gauges:
            self._gauges[name] = {}

        full_key = f"{name}{{{key}}}" if key else name
        self._gauges[name][full_key] = value

    def inc_gauge(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a gauge."""
        labels = labels or {}
        key = self._labels_to_key(labels)

        if name not in self._gauges:
            self._gauges[name] = {}

        full_key = f"{name}{{{key}}}" if key else name
        self._gauges[name][full_key] = self._gauges[name].get(full_key, 0) + value

    def dec_gauge(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Decrement a gauge."""
        self.inc_gauge(name, -value, labels)

    # Histogram operations
    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None
    ) -> None:
        """Observe a value for histogram."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        buckets = buckets or self._default_buckets

        if name not in self._histograms:
            self._histograms[name] = {}

        full_key = f"{name}{{{key}}}" if key else name

        if full_key not in self._histograms[name]:
            self._histograms[name][full_key] = HistogramValue(
                name=name,
                buckets={b: 0 for b in buckets},
                sum_value=0.0,
                count=0,
                labels=labels,
            )

        hist = self._histograms[name][full_key]
        hist.count += 1
        hist.sum_value += value

        # Update bucket counts
        for bucket_le in hist.buckets:
            if value <= bucket_le:
                hist.buckets[bucket_le] += 1

    # Convenience methods for common metrics
    def track_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float
    ) -> None:
        """Track an HTTP request."""
        labels = {"method": method, "path": path, "status": str(status_code)}

        self.inc_counter("ragcache_requests_total", labels=labels)
        self.observe_histogram("ragcache_request_duration_seconds", duration_seconds, labels)

        if status_code >= 400:
            self.inc_counter("ragcache_requests_errors_total", labels=labels)

    def track_cache_hit(self, cache_type: str = "exact") -> None:
        """Track a cache hit."""
        self.inc_counter("ragcache_cache_hits_total", labels={"type": cache_type})
        self._update_hit_rate()

    def track_cache_miss(self) -> None:
        """Track a cache miss."""
        self.inc_counter("ragcache_cache_misses_total")
        self._update_hit_rate()

    def _update_hit_rate(self) -> None:
        """Update the cache hit rate gauge."""
        hits = sum(
            v for k, v in self._counters.get("ragcache_cache_hits_total", {}).items()
            if not k.startswith("_")
        )
        misses = sum(
            v for k, v in self._counters.get("ragcache_cache_misses_total", {}).items()
            if not k.startswith("_")
        )
        total = hits + misses
        rate = hits / total if total > 0 else 0.0
        self.set_gauge("ragcache_cache_hit_rate", rate)

    def track_llm_call(
        self,
        provider: str,
        model: str,
        tokens: int,
        cost: float,
        latency_seconds: float,
        success: bool = True
    ) -> None:
        """Track an LLM API call."""
        labels = {"provider": provider, "model": model}

        self.inc_counter("ragcache_llm_requests_total", labels=labels)
        self.inc_counter(
            "ragcache_llm_tokens_total", value=float(tokens), labels=labels
        )
        self.inc_gauge("ragcache_llm_cost_total", value=cost, labels=labels)
        self.observe_histogram(
            "ragcache_llm_latency_seconds", latency_seconds, labels
        )

        if not success:
            self.inc_counter(
                "ragcache_llm_errors_total",
                labels={"provider": provider, "model": model}
            )

    def get_uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self._start_time

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []

        # Update uptime
        self.set_gauge("ragcache_uptime_seconds", self.get_uptime_seconds())

        # Export counters
        for name, values in self._counters.items():
            help_text = values.get("_meta", f"{name} counter")
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} counter")

            for key, value in values.items():
                if key.startswith("_"):
                    continue
                lines.append(f"{key} {value}")

        # Export gauges
        for name, values in self._gauges.items():
            help_text = values.get("_meta", f"{name} gauge")
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} gauge")

            for key, value in values.items():
                if key.startswith("_"):
                    continue
                lines.append(f"{key} {value}")

        # Export histograms
        for name, values in self._histograms.items():
            help_text = values.get("_meta", f"{name} histogram")
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} histogram")

            for key, hist in values.items():
                if key.startswith("_") or not isinstance(hist, HistogramValue):
                    continue

                label_str = self._labels_to_key(hist.labels)
                base = f"{name}{{{label_str}}}" if label_str else name

                # Bucket values
                for bucket_le, count in sorted(hist.buckets.items()):
                    if label_str:
                        lines.append(
                            f'{name}_bucket{{le="{bucket_le}",{label_str}}} {count}'
                        )
                    else:
                        lines.append(f'{name}_bucket{{le="{bucket_le}"}} {count}')

                # +Inf bucket
                if label_str:
                    lines.append(f'{name}_bucket{{le="+Inf",{label_str}}} {hist.count}')
                else:
                    lines.append(f'{name}_bucket{{le="+Inf"}} {hist.count}')

                # Sum and count
                if label_str:
                    lines.append(f"{name}_sum{{{label_str}}} {hist.sum_value}")
                    lines.append(f"{name}_count{{{label_str}}} {hist.count}")
                else:
                    lines.append(f"{name}_sum {hist.sum_value}")
                    lines.append(f"{name}_count {hist.count}")

        return "\n".join(lines)

    def get_summary(self) -> Dict:
        """Get metrics summary as dictionary."""
        return {
            "uptime_seconds": self.get_uptime_seconds(),
            "counters": {
                k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                for k, v in self._counters.items()
            },
            "gauges": {
                k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                for k, v in self._gauges.items()
            },
        }


# Global metrics instance
_metrics: Optional[PrometheusMetrics] = None


def get_metrics() -> PrometheusMetrics:
    """Get the global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = PrometheusMetrics()
    return _metrics


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic request metrics.

    Tracks request count, duration, and errors.
    """

    def __init__(self, app, metrics: Optional[PrometheusMetrics] = None):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            metrics: Metrics instance (uses global if None)
        """
        super().__init__(app)
        self._metrics = metrics or get_metrics()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with metrics tracking."""
        # Skip metrics for metrics endpoint itself
        if request.url.path in ("/metrics", "/api/v1/metrics/prometheus"):
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            self._metrics.track_request(
                method=request.method,
                path=self._normalize_path(request.url.path),
                status_code=response.status_code,
                duration_seconds=duration,
            )

            return response

        except Exception as e:
            duration = time.time() - start_time
            self._metrics.track_request(
                method=request.method,
                path=self._normalize_path(request.url.path),
                status_code=500,
                duration_seconds=duration,
            )
            raise

    def _normalize_path(self, path: str) -> str:
        """Normalize path to reduce cardinality."""
        # Remove query parameters and normalize common patterns
        # e.g., /api/v1/users/123 -> /api/v1/users/:id
        parts = path.split("/")
        normalized = []
        for part in parts:
            # Replace UUIDs and numeric IDs
            if part.isdigit() or (len(part) == 36 and "-" in part):
                normalized.append(":id")
            else:
                normalized.append(part)
        return "/".join(normalized)


# Convenience function
def metrics_middleware(app):
    """Add metrics middleware to app."""
    return MetricsMiddleware(app)

