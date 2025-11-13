"""
Cache statistics models.

Sandi Metz Principles:
- Small classes with clear purpose
- Computed properties for derived metrics
- Clear naming conventions
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class CacheStatistics(BaseModel):
    """Cache performance statistics."""

    total_queries: int = Field(
        ..., ge=0, description="Total number of queries processed"
    )
    cache_hits: int = Field(..., ge=0, description="Total cache hits")
    cache_misses: int = Field(..., ge=0, description="Total cache misses")
    hit_rate: float = Field(
        ..., ge=0.0, le=100.0, description="Cache hit rate percentage"
    )
    exact_hits: int = Field(..., ge=0, description="Exact cache hits")
    semantic_hits: int = Field(..., ge=0, description="Semantic cache hits")
    avg_latency_ms: int = Field(
        ..., ge=0, description="Average query latency in milliseconds"
    )
    avg_cache_latency_ms: int = Field(
        ..., ge=0, description="Average cache hit latency in milliseconds"
    )
    avg_llm_latency_ms: int = Field(
        ..., ge=0, description="Average LLM query latency in milliseconds"
    )
    tokens_saved: int = Field(..., ge=0, description="Total tokens saved by caching")
    uptime_seconds: int = Field(..., ge=0, description="Service uptime in seconds")

    @model_validator(mode="after")
    def validate_statistics_consistency(self) -> "CacheStatistics":
        """Validate statistics consistency across all fields."""
        # Validate total equals hits + misses
        if self.total_queries != self.cache_hits + self.cache_misses:
            raise ValueError(
                f"total_queries ({self.total_queries}) must equal cache_hits "
                f"({self.cache_hits}) + cache_misses ({self.cache_misses})"
            )

        # Validate exact + semantic = cache_hits
        if self.cache_hits != self.exact_hits + self.semantic_hits:
            raise ValueError(
                f"cache_hits ({self.cache_hits}) must equal exact_hits "
                f"({self.exact_hits}) + semantic_hits ({self.semantic_hits})"
            )

        return self

    @classmethod
    def create(
        cls,
        total_queries: int,
        cache_hits: int,
        cache_misses: int,
        exact_hits: int,
        semantic_hits: int,
        avg_latency_ms: int,
        avg_cache_latency_ms: int,
        avg_llm_latency_ms: int,
        tokens_saved: int,
        uptime_seconds: int,
    ) -> "CacheStatistics":
        """
        Create cache statistics with calculated hit rate.

        Args:
            total_queries: Total number of queries
            cache_hits: Total cache hits
            cache_misses: Total cache misses
            exact_hits: Exact cache hits
            semantic_hits: Semantic cache hits
            avg_latency_ms: Average latency
            avg_cache_latency_ms: Average cache hit latency
            avg_llm_latency_ms: Average LLM latency
            tokens_saved: Tokens saved by caching
            uptime_seconds: Service uptime

        Returns:
            CacheStatistics instance

        Raises:
            ValueError: If validation fails (via model_validator)
        """
        # Validation happens in model_validator
        # Calculate hit rate
        hit_rate = (cache_hits / total_queries * 100.0) if total_queries > 0 else 0.0

        return cls(
            total_queries=total_queries,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            hit_rate=round(hit_rate, 2),
            exact_hits=exact_hits,
            semantic_hits=semantic_hits,
            avg_latency_ms=avg_latency_ms,
            avg_cache_latency_ms=avg_cache_latency_ms,
            avg_llm_latency_ms=avg_llm_latency_ms,
            tokens_saved=tokens_saved,
            uptime_seconds=uptime_seconds,
        )

    @classmethod
    def empty(cls, uptime_seconds: int = 0) -> "CacheStatistics":
        """Create empty statistics (no queries processed yet)."""
        return cls(
            total_queries=0,
            cache_hits=0,
            cache_misses=0,
            hit_rate=0.0,
            exact_hits=0,
            semantic_hits=0,
            avg_latency_ms=0,
            avg_cache_latency_ms=0,
            avg_llm_latency_ms=0,
            tokens_saved=0,
            uptime_seconds=uptime_seconds,
        )

    @property
    def cache_efficiency(self) -> str:
        """Get human-readable cache efficiency rating."""
        if self.hit_rate >= 80.0:
            return "excellent"
        elif self.hit_rate >= 60.0:
            return "good"
        elif self.hit_rate >= 40.0:
            return "moderate"
        elif self.hit_rate >= 20.0:
            return "low"
        else:
            return "very_low"

    @property
    def semantic_ratio(self) -> float:
        """Get ratio of semantic hits to total cache hits."""
        if self.cache_hits == 0:
            return 0.0
        return round((self.semantic_hits / self.cache_hits) * 100.0, 2)

    @property
    def exact_ratio(self) -> float:
        """Get ratio of exact hits to total cache hits."""
        if self.cache_hits == 0:
            return 0.0
        return round((self.exact_hits / self.cache_hits) * 100.0, 2)

    @property
    def latency_improvement(self) -> Optional[float]:
        """
        Get latency improvement percentage from using cache.

        Returns percentage reduction in latency when cache is hit vs LLM call.
        Returns None if no LLM calls have been made.
        """
        if self.avg_llm_latency_ms == 0:
            return None
        improvement = (
            (self.avg_llm_latency_ms - self.avg_cache_latency_ms)
            / self.avg_llm_latency_ms
        ) * 100.0
        return round(improvement, 2)


class RedisMetrics(BaseModel):
    """Redis cache metrics and statistics."""

    total_keys: int = Field(..., ge=0, description="Total number of keys in Redis")
    memory_used_bytes: int = Field(..., ge=0, description="Memory used in bytes")
    memory_peak_bytes: int = Field(..., ge=0, description="Peak memory used in bytes")
    total_connections: int = Field(..., ge=0, description="Total client connections")
    connected_clients: int = Field(..., ge=0, description="Currently connected clients")
    total_commands_processed: int = Field(
        ..., ge=0, description="Total commands processed"
    )
    uptime_seconds: int = Field(..., ge=0, description="Redis server uptime in seconds")
    hits: int = Field(..., ge=0, description="Number of successful key lookups")
    misses: int = Field(..., ge=0, description="Number of failed key lookups")
    evicted_keys: int = Field(..., ge=0, description="Number of evicted keys")
    expired_keys: int = Field(..., ge=0, description="Number of expired keys")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Metrics collection timestamp"
    )

    @property
    def memory_used_mb(self) -> float:
        """Get memory used in megabytes."""
        return round(self.memory_used_bytes / (1024 * 1024), 2)

    @property
    def memory_peak_mb(self) -> float:
        """Get peak memory in megabytes."""
        return round(self.memory_peak_bytes / (1024 * 1024), 2)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round((self.hits / total) * 100.0, 2)

    @property
    def is_healthy(self) -> bool:
        """Check if Redis metrics indicate healthy state."""
        return (
            self.connected_clients > 0
            and self.memory_used_bytes < self.memory_peak_bytes * 0.95
        )
