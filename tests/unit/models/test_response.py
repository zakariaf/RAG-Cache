"""Test response models."""

import pytest

from app.models.response import UsageMetrics, CacheInfo, QueryResponse


class TestUsageMetrics:
    """Test usage metrics model."""

    def test_should_create_with_calculated_total(self):
        """Test total tokens calculation."""
        metrics = UsageMetrics.create(10, 20)
        assert metrics.prompt_tokens == 10
        assert metrics.completion_tokens == 20
        assert metrics.total_tokens == 30


class TestCacheInfo:
    """Test cache info model."""

    def test_should_create_cache_miss(self):
        """Test cache miss creation."""
        info = CacheInfo.miss()
        assert info.cache_hit is False
        assert info.cache_type is None

    def test_should_create_exact_hit(self):
        """Test exact cache hit creation."""
        info = CacheInfo.exact_hit()
        assert info.cache_hit is True
        assert info.cache_type == "exact"

    def test_should_create_semantic_hit(self):
        """Test semantic cache hit creation."""
        info = CacheInfo.semantic_hit(0.95)
        assert info.cache_hit is True
        assert info.cache_type == "semantic"
        assert info.similarity_score == 0.95


class TestQueryResponse:
    """Test query response model."""

    def test_should_create_response(self):
        """Test response creation."""
        response = QueryResponse(
            response="Paris",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageMetrics.create(10, 5),
            cache_info=CacheInfo.miss(),
            latency_ms=150.5
        )
        assert response.response == "Paris"
        assert response.provider == "openai"
        assert response.from_cache is False

    def test_should_identify_cache_types(self):
        """Test cache type identification."""
        # Cache miss
        response = QueryResponse(
            response="test",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageMetrics.create(1, 1),
            cache_info=CacheInfo.miss(),
            latency_ms=100.0
        )
        assert response.from_cache is False
        assert response.is_exact_match is False
        assert response.is_semantic_match is False

        # Exact match
        response = QueryResponse(
            response="test",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageMetrics.create(1, 1),
            cache_info=CacheInfo.exact_hit(),
            latency_ms=10.0
        )
        assert response.from_cache is True
        assert response.is_exact_match is True
        assert response.is_semantic_match is False
