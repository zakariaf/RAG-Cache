"""
Metrics collectors for different system components.

Sandi Metz Principles:
- Single Responsibility: Each collector for one component
- Small classes: Focused collection logic
- Clear naming: Descriptive metric names
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RequestMetrics:
    """
    Collects HTTP request metrics.

    Tracks request counts, latency, and error rates.
    """

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    latencies: List[float] = field(default_factory=list)
    status_codes: Dict[int, int] = field(default_factory=dict)
    methods: Dict[str, int] = field(default_factory=dict)
    paths: Dict[str, int] = field(default_factory=dict)

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float
    ) -> None:
        """Record a request."""
        self.total_requests += 1
        self.total_latency_ms += latency_ms
        self.latencies.append(latency_ms)

        if status_code < 400:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        self.methods[method] = self.methods.get(method, 0) + 1
        self.paths[path] = self.paths.get(path, 0) + 1

    @property
    def avg_latency_ms(self) -> float:
        """Get average latency."""
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def success_rate(self) -> float:
        """Get success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def error_rate(self) -> float:
        """Get error rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def get_percentile(self, p: float) -> float:
        """Get latency percentile."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * p / 100)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p50_latency_ms": round(self.get_percentile(50), 2),
            "p95_latency_ms": round(self.get_percentile(95), 2),
            "p99_latency_ms": round(self.get_percentile(99), 2),
            "success_rate": round(self.success_rate, 4),
            "error_rate": round(self.error_rate, 4),
        }


@dataclass
class CacheMetrics:
    """
    Collects cache performance metrics.

    Tracks hits, misses, and cache efficiency.
    """

    exact_hits: int = 0
    semantic_hits: int = 0
    misses: int = 0
    stores: int = 0
    deletes: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    hit_latencies: List[float] = field(default_factory=list)
    miss_latencies: List[float] = field(default_factory=list)

    def record_hit(self, cache_type: str, latency_ms: float) -> None:
        """Record a cache hit."""
        if cache_type == "exact":
            self.exact_hits += 1
        else:
            self.semantic_hits += 1
        self.total_latency_ms += latency_ms
        self.hit_latencies.append(latency_ms)

    def record_miss(self, latency_ms: float) -> None:
        """Record a cache miss."""
        self.misses += 1
        self.total_latency_ms += latency_ms
        self.miss_latencies.append(latency_ms)

    def record_store(self) -> None:
        """Record a cache store."""
        self.stores += 1

    def record_delete(self) -> None:
        """Record a cache delete."""
        self.deletes += 1

    def record_error(self) -> None:
        """Record a cache error."""
        self.errors += 1

    @property
    def total_hits(self) -> int:
        """Get total hits."""
        return self.exact_hits + self.semantic_hits

    @property
    def total_operations(self) -> int:
        """Get total operations."""
        return self.total_hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self.total_operations
        if total == 0:
            return 0.0
        return self.total_hits / total

    @property
    def exact_hit_rate(self) -> float:
        """Get exact hit rate."""
        if self.total_hits == 0:
            return 0.0
        return self.exact_hits / self.total_hits

    @property
    def semantic_hit_rate(self) -> float:
        """Get semantic hit rate."""
        if self.total_hits == 0:
            return 0.0
        return self.semantic_hits / self.total_hits

    @property
    def avg_hit_latency_ms(self) -> float:
        """Get average hit latency."""
        if not self.hit_latencies:
            return 0.0
        return sum(self.hit_latencies) / len(self.hit_latencies)

    @property
    def avg_miss_latency_ms(self) -> float:
        """Get average miss latency."""
        if not self.miss_latencies:
            return 0.0
        return sum(self.miss_latencies) / len(self.miss_latencies)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "exact_hits": self.exact_hits,
            "semantic_hits": self.semantic_hits,
            "total_hits": self.total_hits,
            "misses": self.misses,
            "stores": self.stores,
            "deletes": self.deletes,
            "errors": self.errors,
            "hit_rate": round(self.hit_rate, 4),
            "exact_hit_rate": round(self.exact_hit_rate, 4),
            "semantic_hit_rate": round(self.semantic_hit_rate, 4),
            "avg_hit_latency_ms": round(self.avg_hit_latency_ms, 2),
            "avg_miss_latency_ms": round(self.avg_miss_latency_ms, 2),
        }


@dataclass
class LLMMetrics:
    """
    Collects LLM provider metrics.

    Tracks API calls, tokens, costs, and latency.
    """

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    latencies: List[float] = field(default_factory=list)
    providers: Dict[str, int] = field(default_factory=dict)
    models: Dict[str, int] = field(default_factory=dict)
    errors_by_type: Dict[str, int] = field(default_factory=dict)

    def record_request(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        latency_ms: float,
        success: bool = True,
        error_type: Optional[str] = None
    ) -> None:
        """Record an LLM request."""
        self.total_requests += 1
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost += cost
        self.total_latency_ms += latency_ms
        self.latencies.append(latency_ms)

        self.providers[provider] = self.providers.get(provider, 0) + 1
        self.models[model] = self.models.get(model, 0) + 1

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.errors_by_type[error_type] = (
                    self.errors_by_type.get(error_type, 0) + 1
                )

    @property
    def total_tokens(self) -> int:
        """Get total tokens."""
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def avg_latency_ms(self) -> float:
        """Get average latency."""
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def avg_tokens_per_request(self) -> float:
        """Get average tokens per request."""
        if self.total_requests == 0:
            return 0.0
        return self.total_tokens / self.total_requests

    @property
    def avg_cost_per_request(self) -> float:
        """Get average cost per request."""
        if self.total_requests == 0:
            return 0.0
        return self.total_cost / self.total_requests

    @property
    def success_rate(self) -> float:
        """Get success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "avg_tokens_per_request": round(self.avg_tokens_per_request, 2),
            "avg_cost_per_request": round(self.avg_cost_per_request, 6),
            "success_rate": round(self.success_rate, 4),
            "providers": self.providers,
            "models": self.models,
        }


@dataclass
class SystemMetrics:
    """
    Collects system-level metrics.

    Tracks uptime, memory, and connection pools.
    """

    start_time: float = field(default_factory=time.time)
    redis_connections: int = 0
    qdrant_connections: int = 0
    active_requests: int = 0
    peak_active_requests: int = 0

    @property
    def uptime_seconds(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self.start_time

    def increment_active_requests(self) -> None:
        """Increment active request counter."""
        self.active_requests += 1
        if self.active_requests > self.peak_active_requests:
            self.peak_active_requests = self.active_requests

    def decrement_active_requests(self) -> None:
        """Decrement active request counter."""
        if self.active_requests > 0:
            self.active_requests -= 1

    def set_redis_connections(self, count: int) -> None:
        """Set Redis connection count."""
        self.redis_connections = count

    def set_qdrant_connections(self, count: int) -> None:
        """Set Qdrant connection count."""
        self.qdrant_connections = count

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "uptime_seconds": round(self.uptime_seconds, 2),
            "redis_connections": self.redis_connections,
            "qdrant_connections": self.qdrant_connections,
            "active_requests": self.active_requests,
            "peak_active_requests": self.peak_active_requests,
        }

