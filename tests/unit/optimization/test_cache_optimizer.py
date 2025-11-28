"""Tests for cache optimizer."""

import pytest

from app.optimization.cache_optimizer import (
    CacheConfig,
    CacheOptimizer,
    CacheStats,
    CacheStrategy,
)


class TestCacheStats:
    """Test cases for CacheStats."""

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(
            exact_hits=30,
            semantic_hits=20,
            misses=50,
        )
        assert stats.hit_rate == 0.5

    def test_hit_rate_zero_requests(self):
        """Test hit rate with no requests."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_exact_hit_rate(self):
        """Test exact hit rate calculation."""
        stats = CacheStats(
            exact_hits=30,
            semantic_hits=20,
            misses=50,
        )
        assert stats.exact_hit_rate == 0.3


class TestCacheOptimizer:
    """Test cases for CacheOptimizer."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return CacheConfig(
            initial_threshold=0.85,
            target_hit_rate=0.50,
        )

    @pytest.fixture
    def optimizer(self, config):
        """Create optimizer instance."""
        return CacheOptimizer(config)

    def test_initial_threshold(self, optimizer):
        """Test initial threshold value."""
        assert optimizer.current_threshold == 0.85

    def test_record_hit(self, optimizer):
        """Test recording cache hit."""
        optimizer.record_hit("exact", "hash123")

        assert optimizer.stats.exact_hits == 1
        assert optimizer.stats.total_requests == 1

    def test_record_miss(self, optimizer):
        """Test recording cache miss."""
        optimizer.record_miss("hash456")

        assert optimizer.stats.misses == 1
        assert optimizer.stats.total_requests == 1

    def test_optimal_ttl_high_frequency(self, optimizer):
        """Test TTL for high frequency queries."""
        # Simulate high frequency
        for _ in range(10):
            optimizer._update_query_stats("frequent_hash")

        ttl = optimizer.get_optimal_ttl("frequent_hash")
        assert ttl == optimizer._config.max_ttl_seconds

    def test_optimal_ttl_low_frequency(self, optimizer):
        """Test TTL for low frequency queries."""
        optimizer._update_query_stats("rare_hash")

        ttl = optimizer.get_optimal_ttl("rare_hash")
        assert ttl == optimizer._config.min_ttl_seconds

    def test_should_cache_high_tokens(self, optimizer):
        """Test should cache for high token responses."""
        result = optimizer.should_cache("hash123", response_tokens=200)
        assert result is True

    def test_eviction_candidates(self, optimizer):
        """Test getting eviction candidates."""
        import time

        entries = [
            {"id": "entry1", "last_accessed": time.time() - 3600, "access_count": 1},
            {"id": "entry2", "last_accessed": time.time(), "access_count": 10},
            {"id": "entry3", "last_accessed": time.time() - 7200, "access_count": 2},
        ]

        candidates = optimizer.get_eviction_candidates(entries, count=1)

        # entry1 should be evicted (old and low frequency)
        assert "entry1" in candidates

    def test_optimization_report(self, optimizer):
        """Test getting optimization report."""
        optimizer.record_hit("exact", "hash1")
        optimizer.record_miss("hash2")

        report = optimizer.get_optimization_report()

        assert "current_threshold" in report
        assert "hit_rate" in report
        assert report["total_requests"] == 2


class TestCacheStrategy:
    """Test CacheStrategy enum."""

    def test_strategy_values(self):
        """Test strategy enum values."""
        assert CacheStrategy.WRITE_THROUGH.value == "write_through"
        assert CacheStrategy.READ_THROUGH.value == "read_through"
