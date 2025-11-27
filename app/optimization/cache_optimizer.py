"""
Cache hit rate optimization.

Sandi Metz Principles:
- Single Responsibility: Cache optimization
- Small methods: Each strategy isolated
- Configurable: Flexible optimization settings
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CacheStrategy(str, Enum):
    """Cache optimization strategies."""

    WRITE_THROUGH = "write_through"  # Write to cache on every write
    WRITE_BEHIND = "write_behind"    # Async cache writes
    READ_THROUGH = "read_through"    # Load on miss
    REFRESH_AHEAD = "refresh_ahead"  # Proactively refresh


@dataclass
class CacheStats:
    """Cache statistics for optimization decisions."""

    total_requests: int = 0
    exact_hits: int = 0
    semantic_hits: int = 0
    misses: int = 0
    stores: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate overall hit rate."""
        total = self.exact_hits + self.semantic_hits + self.misses
        if total == 0:
            return 0.0
        return (self.exact_hits + self.semantic_hits) / total

    @property
    def exact_hit_rate(self) -> float:
        """Calculate exact hit rate."""
        total = self.exact_hits + self.semantic_hits + self.misses
        if total == 0:
            return 0.0
        return self.exact_hits / total


@dataclass
class CacheConfig:
    """Cache optimization configuration."""

    # Threshold optimization
    initial_threshold: float = 0.85
    min_threshold: float = 0.70
    max_threshold: float = 0.95
    threshold_adjustment_rate: float = 0.01

    # TTL optimization
    base_ttl_seconds: int = 3600
    min_ttl_seconds: int = 300
    max_ttl_seconds: int = 86400

    # Hit rate targets
    target_hit_rate: float = 0.50
    hit_rate_tolerance: float = 0.05

    # Eviction policy
    max_cache_size: int = 10000
    eviction_batch_size: int = 100


class CacheOptimizer:
    """
    Optimizes cache performance for higher hit rates.

    Dynamically adjusts cache parameters based on performance.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize optimizer.

        Args:
            config: Cache configuration
        """
        self._config = config or CacheConfig()
        self._stats = CacheStats()
        self._current_threshold = self._config.initial_threshold
        self._query_frequency: Dict[str, int] = {}
        self._query_recency: Dict[str, float] = {}
        self._adjustment_history: List[Tuple[float, float, float]] = []

    @property
    def current_threshold(self) -> float:
        """Get current semantic threshold."""
        return self._current_threshold

    @property
    def stats(self) -> CacheStats:
        """Get current cache stats."""
        return self._stats

    def record_hit(self, cache_type: str, query_hash: str) -> None:
        """
        Record a cache hit.

        Args:
            cache_type: Type of hit (exact or semantic)
            query_hash: Hash of the query
        """
        self._stats.total_requests += 1
        if cache_type == "exact":
            self._stats.exact_hits += 1
        else:
            self._stats.semantic_hits += 1

        self._update_query_stats(query_hash)
        self._maybe_adjust_threshold()

    def record_miss(self, query_hash: str) -> None:
        """
        Record a cache miss.

        Args:
            query_hash: Hash of the query
        """
        self._stats.total_requests += 1
        self._stats.misses += 1
        self._update_query_stats(query_hash)
        self._maybe_adjust_threshold()

    def record_store(self) -> None:
        """Record a cache store operation."""
        self._stats.stores += 1

    def record_eviction(self, count: int = 1) -> None:
        """Record cache evictions."""
        self._stats.evictions += count

    def _update_query_stats(self, query_hash: str) -> None:
        """Update query frequency and recency."""
        self._query_frequency[query_hash] = (
            self._query_frequency.get(query_hash, 0) + 1
        )
        self._query_recency[query_hash] = time.time()

        # Limit tracking size
        if len(self._query_frequency) > self._config.max_cache_size * 2:
            self._cleanup_query_stats()

    def _cleanup_query_stats(self) -> None:
        """Remove old query stats."""
        cutoff = time.time() - 86400  # 24 hours

        self._query_recency = {
            k: v for k, v in self._query_recency.items() if v > cutoff
        }
        self._query_frequency = {
            k: v for k, v in self._query_frequency.items()
            if k in self._query_recency
        }

    def _maybe_adjust_threshold(self) -> None:
        """Dynamically adjust semantic threshold based on hit rate."""
        # Only adjust after enough samples
        if self._stats.total_requests < 100:
            return

        # Only adjust periodically
        if self._stats.total_requests % 50 != 0:
            return

        current_hit_rate = self._stats.hit_rate
        target = self._config.target_hit_rate
        tolerance = self._config.hit_rate_tolerance

        old_threshold = self._current_threshold

        if current_hit_rate < target - tolerance:
            # Hit rate too low - lower threshold to get more matches
            self._current_threshold = max(
                self._config.min_threshold,
                self._current_threshold - self._config.threshold_adjustment_rate
            )
        elif current_hit_rate > target + tolerance:
            # Hit rate exceeds target - can raise threshold for precision
            self._current_threshold = min(
                self._config.max_threshold,
                self._current_threshold + self._config.threshold_adjustment_rate
            )

        if old_threshold != self._current_threshold:
            self._adjustment_history.append(
                (time.time(), old_threshold, self._current_threshold)
            )
            logger.info(
                "Adjusted semantic threshold",
                old=old_threshold,
                new=self._current_threshold,
                hit_rate=current_hit_rate
            )

    def get_optimal_ttl(self, query_hash: str) -> int:
        """
        Calculate optimal TTL for a query.

        Args:
            query_hash: Hash of the query

        Returns:
            Optimal TTL in seconds
        """
        frequency = self._query_frequency.get(query_hash, 0)

        # High frequency queries get longer TTL
        if frequency >= 10:
            return self._config.max_ttl_seconds
        elif frequency >= 5:
            return self._config.base_ttl_seconds * 2
        elif frequency >= 2:
            return self._config.base_ttl_seconds
        else:
            return self._config.min_ttl_seconds

    def get_eviction_candidates(
        self,
        cache_entries: List[Dict[str, Any]],
        count: int
    ) -> List[str]:
        """
        Get candidates for cache eviction using LRU-LFU hybrid.

        Args:
            cache_entries: List of cache entries with id, last_accessed, access_count
            count: Number of entries to evict

        Returns:
            List of entry IDs to evict
        """
        if not cache_entries:
            return []

        # Score each entry (lower score = better eviction candidate)
        scored = []
        current_time = time.time()

        for entry in cache_entries:
            entry_id = entry.get("id", "")
            last_accessed = entry.get("last_accessed", 0)
            access_count = entry.get("access_count", 1)

            # Time since last access (in hours)
            recency_hours = (current_time - last_accessed) / 3600

            # Score combines frequency and recency
            # Higher score = more valuable (keep)
            score = access_count / (1 + recency_hours)

            scored.append((entry_id, score))

        # Sort by score ascending (lowest scores first)
        scored.sort(key=lambda x: x[1])

        # Return IDs of entries to evict
        return [entry_id for entry_id, _ in scored[:count]]

    def should_cache(self, query_hash: str, response_tokens: int) -> bool:
        """
        Determine if a response should be cached.

        Args:
            query_hash: Hash of the query
            response_tokens: Number of tokens in response

        Returns:
            True if response should be cached
        """
        # Always cache frequently requested queries
        if self._query_frequency.get(query_hash, 0) >= 2:
            return True

        # Cache responses with significant token count (cost savings)
        if response_tokens >= 100:
            return True

        # Cache if hit rate is below target
        if self._stats.hit_rate < self._config.target_hit_rate:
            return True

        return True  # Default to caching

    def get_optimization_report(self) -> Dict[str, Any]:
        """
        Get optimization status report.

        Returns:
            Optimization report dictionary
        """
        return {
            "current_threshold": self._current_threshold,
            "hit_rate": round(self._stats.hit_rate, 4),
            "exact_hit_rate": round(self._stats.exact_hit_rate, 4),
            "total_requests": self._stats.total_requests,
            "target_hit_rate": self._config.target_hit_rate,
            "threshold_adjustments": len(self._adjustment_history),
            "unique_queries_tracked": len(self._query_frequency),
        }

