"""Unit tests for Qdrant point models."""

import time
from datetime import datetime
from unittest.mock import patch

import pytest
from qdrant_client.models import PointStruct

from app.models.cache_entry import CacheEntry
from app.models.qdrant_point import (
    BatchUploadResult,
    DeleteResult,
    QdrantPoint,
    SearchResult,
)


class TestQdrantPoint:
    """Tests for QdrantPoint model."""

    @pytest.fixture
    def cache_entry(self):
        """Create sample cache entry."""
        return CacheEntry(
            query_hash="abc123",
            original_query="What is the weather?",
            response="It's sunny today",
            provider="openai",
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=5,
            embedding=[0.1, 0.2, 0.3],
        )

    def test_qdrant_point_creation(self):
        """Test creating QdrantPoint."""
        point = QdrantPoint(
            id="test-123", vector=[0.1, 0.2, 0.3], payload={"key": "value"}
        )

        assert point.id == "test-123"
        assert point.vector == [0.1, 0.2, 0.3]
        assert point.payload == {"key": "value"}

    def test_qdrant_point_auto_id(self):
        """Test QdrantPoint generates ID if not provided."""
        point = QdrantPoint(vector=[0.1, 0.2, 0.3])

        assert point.id is not None
        assert len(point.id) > 0

    def test_from_cache_entry(self, cache_entry):
        """Test creating point from cache entry."""
        embedding = [0.1, 0.2, 0.3]

        with patch("time.time", return_value=1234567890.0):
            point = QdrantPoint.from_cache_entry(cache_entry, embedding)

            assert point.vector == embedding
            assert point.payload["query_hash"] == "abc123"
            assert point.payload["original_query"] == "What is the weather?"
            assert point.payload["response"] == "It's sunny today"
            assert point.payload["provider"] == "openai"
            assert point.payload["model"] == "gpt-4"
            assert point.payload["prompt_tokens"] == 10
            assert point.payload["completion_tokens"] == 5
            assert point.payload["cached_at"] == 1234567890.0
            assert "created_at" in point.payload

    def test_from_cache_entry_with_embedding_flag(self):
        """Test from_cache_entry sets has_embedding flag."""
        entry = CacheEntry(
            query_hash="abc123",
            original_query="Query",
            response="Response",
            provider="openai",
            model="gpt-4",
            embedding=[0.1, 0.2],
        )

        point = QdrantPoint.from_cache_entry(entry, [0.1, 0.2])

        assert point.payload["has_embedding"] is True

    def test_from_cache_entry_without_embedding(self):
        """Test from_cache_entry when entry has no embedding."""
        entry = CacheEntry(
            query_hash="abc123",
            original_query="Query",
            response="Response",
            provider="openai",
            model="gpt-4",
            embedding=None,
        )

        point = QdrantPoint.from_cache_entry(entry, [0.1, 0.2])

        assert "has_embedding" not in point.payload

    def test_to_qdrant_point(self):
        """Test converting to Qdrant PointStruct."""
        point = QdrantPoint(
            id="test-123", vector=[0.1, 0.2, 0.3], payload={"key": "value"}
        )

        qdrant_point = point.to_qdrant_point()

        assert isinstance(qdrant_point, PointStruct)
        assert qdrant_point.id == "test-123"
        assert qdrant_point.vector == [0.1, 0.2, 0.3]
        assert qdrant_point.payload == {"key": "value"}

    def test_from_qdrant_point(self):
        """Test creating from Qdrant point data."""
        point = QdrantPoint.from_qdrant_point(
            point_id="test-123",
            vector=[0.1, 0.2, 0.3],
            payload={"query_hash": "abc123"},
        )

        assert point.id == "test-123"
        assert point.vector == [0.1, 0.2, 0.3]
        assert point.payload["query_hash"] == "abc123"


class TestSearchResult:
    """Tests for SearchResult model."""

    @pytest.fixture
    def search_result(self):
        """Create sample search result."""
        return SearchResult(
            point_id="test-123",
            score=0.95,
            vector=[0.1, 0.2, 0.3],
            payload={
                "query_hash": "abc123",
                "original_query": "What is the weather?",
                "response": "It's sunny today",
                "provider": "openai",
                "model": "gpt-4",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "created_at": 1234567890.0,
            },
        )

    def test_search_result_creation(self):
        """Test creating SearchResult."""
        result = SearchResult(
            point_id="test-123", score=0.95, payload={"query_hash": "abc123"}
        )

        assert result.point_id == "test-123"
        assert result.score == 0.95
        assert result.payload["query_hash"] == "abc123"

    def test_query_hash_property(self, search_result):
        """Test query_hash property."""
        assert search_result.query_hash == "abc123"

    def test_query_hash_property_missing(self):
        """Test query_hash property when missing."""
        result = SearchResult(point_id="test-123", score=0.95, payload={})

        assert result.query_hash is None

    def test_original_query_property(self, search_result):
        """Test original_query property."""
        assert search_result.original_query == "What is the weather?"

    def test_original_query_property_missing(self):
        """Test original_query property when missing."""
        result = SearchResult(point_id="test-123", score=0.95, payload={})

        assert result.original_query is None

    def test_response_property(self, search_result):
        """Test response property."""
        assert search_result.response == "It's sunny today"

    def test_response_property_missing(self):
        """Test response property when missing."""
        result = SearchResult(point_id="test-123", score=0.95, payload={})

        assert result.response is None

    def test_provider_property(self, search_result):
        """Test provider property."""
        assert search_result.provider == "openai"

    def test_provider_property_missing(self):
        """Test provider property when missing."""
        result = SearchResult(point_id="test-123", score=0.95, payload={})

        assert result.provider is None

    def test_model_property(self, search_result):
        """Test model property."""
        assert search_result.model == "gpt-4"

    def test_model_property_missing(self):
        """Test model property when missing."""
        result = SearchResult(point_id="test-123", score=0.95, payload={})

        assert result.model is None

    def test_to_cache_entry_success(self, search_result):
        """Test converting to cache entry."""
        entry = search_result.to_cache_entry()

        assert entry is not None
        assert entry.query_hash == "abc123"
        assert entry.original_query == "What is the weather?"
        assert entry.response == "It's sunny today"
        assert entry.provider == "openai"
        assert entry.model == "gpt-4"
        assert entry.prompt_tokens == 10
        assert entry.completion_tokens == 5
        assert entry.embedding == [0.1, 0.2, 0.3]

    def test_to_cache_entry_with_timestamp(self):
        """Test converting to cache entry preserves timestamp."""
        result = SearchResult(
            point_id="test-123",
            score=0.95,
            payload={
                "query_hash": "abc123",
                "original_query": "Query",
                "response": "Response",
                "provider": "openai",
                "model": "gpt-4",
                "created_at": 1234567890.0,
            },
        )

        entry = result.to_cache_entry()

        assert entry is not None
        assert isinstance(entry.created_at, datetime)

    def test_to_cache_entry_missing_required_field(self):
        """Test converting to cache entry with missing required field."""
        result = SearchResult(
            point_id="test-123",
            score=0.95,
            payload={"query_hash": "abc123"},  # Missing other required fields
        )

        entry = result.to_cache_entry()

        assert entry is None

    def test_to_cache_entry_invalid_timestamp(self):
        """Test converting to cache entry with invalid timestamp."""
        result = SearchResult(
            point_id="test-123",
            score=0.95,
            payload={
                "query_hash": "abc123",
                "original_query": "Query",
                "response": "Response",
                "provider": "openai",
                "model": "gpt-4",
                "created_at": "invalid",  # Invalid timestamp
            },
        )

        entry = result.to_cache_entry()

        assert entry is None

    def test_to_cache_entry_defaults_tokens(self):
        """Test converting to cache entry uses default token values."""
        result = SearchResult(
            point_id="test-123",
            score=0.95,
            payload={
                "query_hash": "abc123",
                "original_query": "Query",
                "response": "Response",
                "provider": "openai",
                "model": "gpt-4",
                # No token fields
            },
        )

        entry = result.to_cache_entry()

        assert entry is not None
        assert entry.prompt_tokens == 0
        assert entry.completion_tokens == 0


class TestBatchUploadResult:
    """Tests for BatchUploadResult model."""

    def test_batch_upload_result_creation(self):
        """Test creating BatchUploadResult."""
        result = BatchUploadResult(total=10, successful=8, failed=2)

        assert result.total == 10
        assert result.successful == 8
        assert result.failed == 2

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        result = BatchUploadResult(total=10, successful=8, failed=2)

        assert result.success_rate == 0.8

    def test_success_rate_zero_total(self):
        """Test success rate with zero total."""
        result = BatchUploadResult(total=0, successful=0, failed=0)

        assert result.success_rate == 0.0

    def test_success_rate_complete_success(self):
        """Test success rate with complete success."""
        result = BatchUploadResult(total=10, successful=10, failed=0)

        assert result.success_rate == 1.0

    def test_has_failures_true(self):
        """Test has_failures when there are failures."""
        result = BatchUploadResult(total=10, successful=8, failed=2)

        assert result.has_failures is True

    def test_has_failures_false(self):
        """Test has_failures when no failures."""
        result = BatchUploadResult(total=10, successful=10, failed=0)

        assert result.has_failures is False

    def test_batch_upload_result_with_details(self):
        """Test BatchUploadResult with point IDs and errors."""
        result = BatchUploadResult(
            total=10,
            successful=8,
            failed=2,
            point_ids=["id1", "id2", "id3"],
            errors=["Error 1", "Error 2"],
        )

        assert len(result.point_ids) == 3
        assert len(result.errors) == 2


class TestDeleteResult:
    """Tests for DeleteResult model."""

    def test_delete_result_success(self):
        """Test creating successful DeleteResult."""
        result = DeleteResult(deleted_count=5, success=True, message="Deleted 5 points")

        assert result.deleted_count == 5
        assert result.success is True
        assert result.message == "Deleted 5 points"

    def test_delete_result_failure(self):
        """Test creating failed DeleteResult."""
        result = DeleteResult(deleted_count=0, success=False, message="Delete failed")

        assert result.deleted_count == 0
        assert result.success is False
        assert result.message == "Delete failed"

    def test_delete_result_without_message(self):
        """Test DeleteResult without message."""
        result = DeleteResult(deleted_count=5, success=True)

        assert result.deleted_count == 5
        assert result.success is True
        assert result.message is None
