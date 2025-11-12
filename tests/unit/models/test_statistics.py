"""Test cache statistics models."""

import pytest

from app.models.statistics import CacheStatistics


class TestCacheStatistics:
    """Test cache statistics model."""

    def test_should_create_with_factory_method(self):
        """Test statistics creation with calculated hit rate."""
        stats = CacheStatistics.create(
            total_queries=1000,
            cache_hits=600,
            cache_misses=400,
            exact_hits=350,
            semantic_hits=250,
            avg_latency_ms=150,
            avg_cache_latency_ms=20,
            avg_llm_latency_ms=500,
            tokens_saved=50000,
            uptime_seconds=3600,
        )

        assert stats.total_queries == 1000
        assert stats.cache_hits == 600
        assert stats.cache_misses == 400
        assert stats.hit_rate == 60.0  # 600/1000 * 100
        assert stats.exact_hits == 350
        assert stats.semantic_hits == 250
        assert stats.tokens_saved == 50000
        assert stats.uptime_seconds == 3600

    def test_should_create_empty_statistics(self):
        """Test empty statistics creation."""
        stats = CacheStatistics.empty()

        assert stats.total_queries == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.hit_rate == 0.0
        assert stats.exact_hits == 0
        assert stats.semantic_hits == 0
        assert stats.tokens_saved == 0

    def test_should_create_empty_with_uptime(self):
        """Test empty statistics with custom uptime."""
        stats = CacheStatistics.empty(uptime_seconds=7200)
        assert stats.uptime_seconds == 7200
        assert stats.total_queries == 0

    def test_should_calculate_hit_rate_correctly(self):
        """Test hit rate calculation."""
        # 75% hit rate
        stats = CacheStatistics.create(
            total_queries=400,
            cache_hits=300,
            cache_misses=100,
            exact_hits=200,
            semantic_hits=100,
            avg_latency_ms=100,
            avg_cache_latency_ms=10,
            avg_llm_latency_ms=400,
            tokens_saved=10000,
            uptime_seconds=1800,
        )
        assert stats.hit_rate == 75.0

        # 33.33% hit rate
        stats = CacheStatistics.create(
            total_queries=300,
            cache_hits=100,
            cache_misses=200,
            exact_hits=60,
            semantic_hits=40,
            avg_latency_ms=200,
            avg_cache_latency_ms=15,
            avg_llm_latency_ms=500,
            tokens_saved=5000,
            uptime_seconds=900,
        )
        assert stats.hit_rate == 33.33

    def test_should_handle_zero_queries(self):
        """Test statistics with zero queries."""
        stats = CacheStatistics.create(
            total_queries=0,
            cache_hits=0,
            cache_misses=0,
            exact_hits=0,
            semantic_hits=0,
            avg_latency_ms=0,
            avg_cache_latency_ms=0,
            avg_llm_latency_ms=0,
            tokens_saved=0,
            uptime_seconds=60,
        )
        assert stats.hit_rate == 0.0
        assert stats.total_queries == 0

    def test_should_validate_total_equals_hits_plus_misses(self):
        """Test validation that total equals hits plus misses."""
        with pytest.raises(ValueError, match="total_queries.*must equal.*cache_hits.*cache_misses"):
            CacheStatistics.create(
                total_queries=100,  # Should be 150
                cache_hits=100,
                cache_misses=50,
                exact_hits=60,
                semantic_hits=40,
                avg_latency_ms=100,
                avg_cache_latency_ms=10,
                avg_llm_latency_ms=400,
                tokens_saved=5000,
                uptime_seconds=300,
            )

    def test_should_validate_cache_hits_equals_exact_plus_semantic(self):
        """Test validation that cache hits equals exact plus semantic."""
        with pytest.raises(ValueError, match="cache_hits.*must equal.*exact_hits.*semantic_hits"):
            CacheStatistics.create(
                total_queries=150,
                cache_hits=100,  # Should be 120
                cache_misses=50,
                exact_hits=70,
                semantic_hits=50,
                avg_latency_ms=100,
                avg_cache_latency_ms=10,
                avg_llm_latency_ms=400,
                tokens_saved=5000,
                uptime_seconds=300,
            )

    def test_should_provide_cache_efficiency_rating(self):
        """Test cache efficiency property."""
        # Excellent (>= 80%)
        stats = CacheStatistics.create(
            total_queries=100,
            cache_hits=85,
            cache_misses=15,
            exact_hits=50,
            semantic_hits=35,
            avg_latency_ms=100,
            avg_cache_latency_ms=10,
            avg_llm_latency_ms=400,
            tokens_saved=5000,
            uptime_seconds=300,
        )
        assert stats.cache_efficiency == "excellent"

        # Good (>= 60%)
        stats = CacheStatistics.create(
            total_queries=100,
            cache_hits=65,
            cache_misses=35,
            exact_hits=40,
            semantic_hits=25,
            avg_latency_ms=100,
            avg_cache_latency_ms=10,
            avg_llm_latency_ms=400,
            tokens_saved=5000,
            uptime_seconds=300,
        )
        assert stats.cache_efficiency == "good"

        # Moderate (>= 40%)
        stats = CacheStatistics.create(
            total_queries=100,
            cache_hits=45,
            cache_misses=55,
            exact_hits=25,
            semantic_hits=20,
            avg_latency_ms=100,
            avg_cache_latency_ms=10,
            avg_llm_latency_ms=400,
            tokens_saved=5000,
            uptime_seconds=300,
        )
        assert stats.cache_efficiency == "moderate"

        # Low (>= 20%)
        stats = CacheStatistics.create(
            total_queries=100,
            cache_hits=25,
            cache_misses=75,
            exact_hits=15,
            semantic_hits=10,
            avg_latency_ms=100,
            avg_cache_latency_ms=10,
            avg_llm_latency_ms=400,
            tokens_saved=5000,
            uptime_seconds=300,
        )
        assert stats.cache_efficiency == "low"

        # Very low (< 20%)
        stats = CacheStatistics.create(
            total_queries=100,
            cache_hits=10,
            cache_misses=90,
            exact_hits=6,
            semantic_hits=4,
            avg_latency_ms=100,
            avg_cache_latency_ms=10,
            avg_llm_latency_ms=400,
            tokens_saved=5000,
            uptime_seconds=300,
        )
        assert stats.cache_efficiency == "very_low"

    def test_should_calculate_semantic_ratio(self):
        """Test semantic hits ratio."""
        stats = CacheStatistics.create(
            total_queries=100,
            cache_hits=60,
            cache_misses=40,
            exact_hits=20,
            semantic_hits=40,  # 40/60 = 66.67%
            avg_latency_ms=100,
            avg_cache_latency_ms=10,
            avg_llm_latency_ms=400,
            tokens_saved=5000,
            uptime_seconds=300,
        )
        assert stats.semantic_ratio == 66.67

    def test_should_calculate_exact_ratio(self):
        """Test exact hits ratio."""
        stats = CacheStatistics.create(
            total_queries=100,
            cache_hits=60,
            cache_misses=40,
            exact_hits=45,  # 45/60 = 75%
            semantic_hits=15,
            avg_latency_ms=100,
            avg_cache_latency_ms=10,
            avg_llm_latency_ms=400,
            tokens_saved=5000,
            uptime_seconds=300,
        )
        assert stats.exact_ratio == 75.0

    def test_should_handle_zero_cache_hits_for_ratios(self):
        """Test ratios when there are no cache hits."""
        stats = CacheStatistics.create(
            total_queries=100,
            cache_hits=0,
            cache_misses=100,
            exact_hits=0,
            semantic_hits=0,
            avg_latency_ms=100,
            avg_cache_latency_ms=10,
            avg_llm_latency_ms=400,
            tokens_saved=0,
            uptime_seconds=300,
        )
        assert stats.semantic_ratio == 0.0
        assert stats.exact_ratio == 0.0

    def test_should_calculate_latency_improvement(self):
        """Test latency improvement calculation."""
        stats = CacheStatistics.create(
            total_queries=100,
            cache_hits=60,
            cache_misses=40,
            exact_hits=30,
            semantic_hits=30,
            avg_latency_ms=100,
            avg_cache_latency_ms=20,  # Cache is 20ms
            avg_llm_latency_ms=500,  # LLM is 500ms
            tokens_saved=5000,
            uptime_seconds=300,
        )
        # Improvement: (500 - 20) / 500 * 100 = 96%
        assert stats.latency_improvement == 96.0

    def test_should_handle_no_llm_calls_for_latency_improvement(self):
        """Test latency improvement when no LLM calls made."""
        stats = CacheStatistics.create(
            total_queries=100,
            cache_hits=100,
            cache_misses=0,
            exact_hits=60,
            semantic_hits=40,
            avg_latency_ms=10,
            avg_cache_latency_ms=10,
            avg_llm_latency_ms=0,  # No LLM calls
            tokens_saved=5000,
            uptime_seconds=300,
        )
        assert stats.latency_improvement is None

    def test_should_serialize_to_json(self):
        """Test statistics serialization."""
        stats = CacheStatistics.create(
            total_queries=1000,
            cache_hits=600,
            cache_misses=400,
            exact_hits=350,
            semantic_hits=250,
            avg_latency_ms=150,
            avg_cache_latency_ms=20,
            avg_llm_latency_ms=500,
            tokens_saved=50000,
            uptime_seconds=3600,
        )

        json_data = stats.model_dump()

        assert json_data["total_queries"] == 1000
        assert json_data["cache_hits"] == 600
        assert json_data["hit_rate"] == 60.0
        assert json_data["tokens_saved"] == 50000

    def test_should_deserialize_from_json(self):
        """Test statistics deserialization."""
        data = {
            "total_queries": 1000,
            "cache_hits": 600,
            "cache_misses": 400,
            "hit_rate": 60.0,
            "exact_hits": 350,
            "semantic_hits": 250,
            "avg_latency_ms": 150,
            "avg_cache_latency_ms": 20,
            "avg_llm_latency_ms": 500,
            "tokens_saved": 50000,
            "uptime_seconds": 3600,
        }

        stats = CacheStatistics.model_validate(data)

        assert stats.total_queries == 1000
        assert stats.cache_hits == 600
        assert stats.hit_rate == 60.0
