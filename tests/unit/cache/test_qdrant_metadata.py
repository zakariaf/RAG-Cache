"""Unit tests for Qdrant metadata handler."""

from unittest.mock import patch

import pytest

from app.cache.qdrant_metadata import MetadataHandler
from app.models.cache_entry import CacheEntry
from app.models.qdrant_schema import QdrantSchema


class TestMetadataHandler:
    """Tests for MetadataHandler class."""

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

    @pytest.fixture
    def valid_payload(self):
        """Create valid payload."""
        return {
            QdrantSchema.FIELD_QUERY_HASH: "abc123",
            QdrantSchema.FIELD_ORIGINAL_QUERY: "What is the weather?",
            QdrantSchema.FIELD_RESPONSE: "It's sunny today",
            QdrantSchema.FIELD_PROVIDER: "openai",
            QdrantSchema.FIELD_MODEL: "gpt-4",
            QdrantSchema.FIELD_PROMPT_TOKENS: 10,
            QdrantSchema.FIELD_COMPLETION_TOKENS: 5,
        }

    def test_create_from_cache_entry(self, cache_entry):
        """Test creating metadata from cache entry."""
        with patch("time.time", return_value=1234567890.0):
            metadata = MetadataHandler.create_from_cache_entry(cache_entry)

            assert metadata[QdrantSchema.FIELD_QUERY_HASH] == "abc123"
            assert metadata[QdrantSchema.FIELD_ORIGINAL_QUERY] == "What is the weather?"
            assert metadata[QdrantSchema.FIELD_RESPONSE] == "It's sunny today"
            assert metadata[QdrantSchema.FIELD_PROVIDER] == "openai"
            assert metadata[QdrantSchema.FIELD_MODEL] == "gpt-4"
            assert metadata[QdrantSchema.FIELD_PROMPT_TOKENS] == 10
            assert metadata[QdrantSchema.FIELD_COMPLETION_TOKENS] == 5
            assert metadata[QdrantSchema.FIELD_CREATED_AT] == 1234567890.0
            assert metadata[QdrantSchema.FIELD_CACHED_AT] == 1234567890.0

    def test_validate_payload_valid(self, valid_payload):
        """Test validating valid payload."""
        is_valid = MetadataHandler.validate_payload(valid_payload)

        assert is_valid is True

    def test_validate_payload_missing_field(self):
        """Test validating payload with missing required field."""
        invalid_payload = {
            QdrantSchema.FIELD_QUERY_HASH: "abc123",
            # Missing other required fields
        }

        is_valid = MetadataHandler.validate_payload(invalid_payload)

        assert is_valid is False

    def test_extract_cache_entry_success(self, valid_payload):
        """Test extracting cache entry from valid payload."""
        entry = MetadataHandler.extract_cache_entry(valid_payload)

        assert entry is not None
        assert entry.query_hash == "abc123"
        assert entry.original_query == "What is the weather?"
        assert entry.response == "It's sunny today"
        assert entry.provider == "openai"
        assert entry.model == "gpt-4"
        assert entry.prompt_tokens == 10
        assert entry.completion_tokens == 5

    def test_extract_cache_entry_with_defaults(self):
        """Test extracting cache entry uses defaults for optional fields."""
        payload = {
            QdrantSchema.FIELD_QUERY_HASH: "abc123",
            QdrantSchema.FIELD_ORIGINAL_QUERY: "Query",
            QdrantSchema.FIELD_RESPONSE: "Response",
            QdrantSchema.FIELD_PROVIDER: "openai",
            QdrantSchema.FIELD_MODEL: "gpt-4",
            # Missing token fields - should default to 0
        }

        entry = MetadataHandler.extract_cache_entry(payload)

        assert entry is not None
        assert entry.prompt_tokens == 0
        assert entry.completion_tokens == 0

    def test_extract_cache_entry_missing_required_field(self):
        """Test extracting cache entry with missing required field."""
        invalid_payload = {
            QdrantSchema.FIELD_QUERY_HASH: "abc123",
            # Missing other required fields
        }

        entry = MetadataHandler.extract_cache_entry(invalid_payload)

        assert entry is None

    def test_extract_cache_entry_handles_exception(self):
        """Test extracting cache entry handles exceptions."""
        invalid_payload = {"invalid": "data"}

        entry = MetadataHandler.extract_cache_entry(invalid_payload)

        assert entry is None

    def test_add_tags_to_empty_payload(self):
        """Test adding tags to payload without existing tags."""
        payload = {}
        tags = ["tag1", "tag2"]

        result = MetadataHandler.add_tags(payload, tags)

        assert QdrantSchema.FIELD_TAGS in result
        assert set(result[QdrantSchema.FIELD_TAGS]) == {"tag1", "tag2"}

    def test_add_tags_to_existing_payload(self):
        """Test adding tags to payload with existing tags."""
        payload = {QdrantSchema.FIELD_TAGS: ["tag1", "tag2"]}
        tags = ["tag2", "tag3"]

        result = MetadataHandler.add_tags(payload, tags)

        assert set(result[QdrantSchema.FIELD_TAGS]) == {"tag1", "tag2", "tag3"}

    def test_add_metadata_to_empty_payload(self):
        """Test adding metadata to payload without existing metadata."""
        payload = {}
        metadata = {"key1": "value1", "key2": "value2"}

        result = MetadataHandler.add_metadata(payload, metadata)

        assert QdrantSchema.FIELD_METADATA in result
        assert result[QdrantSchema.FIELD_METADATA] == metadata

    def test_add_metadata_to_existing_payload(self):
        """Test adding metadata to payload with existing metadata."""
        payload = {QdrantSchema.FIELD_METADATA: {"key1": "old_value", "key2": "value2"}}
        metadata = {"key1": "new_value", "key3": "value3"}

        result = MetadataHandler.add_metadata(payload, metadata)

        assert result[QdrantSchema.FIELD_METADATA]["key1"] == "new_value"
        assert result[QdrantSchema.FIELD_METADATA]["key2"] == "value2"
        assert result[QdrantSchema.FIELD_METADATA]["key3"] == "value3"

    def test_get_field_exists(self, valid_payload):
        """Test getting existing field from payload."""
        value = MetadataHandler.get_field(valid_payload, QdrantSchema.FIELD_QUERY_HASH)

        assert value == "abc123"

    def test_get_field_not_exists(self, valid_payload):
        """Test getting non-existing field from payload."""
        value = MetadataHandler.get_field(valid_payload, "nonexistent_field")

        assert value is None

    def test_has_field_exists(self, valid_payload):
        """Test checking if field exists."""
        exists = MetadataHandler.has_field(valid_payload, QdrantSchema.FIELD_QUERY_HASH)

        assert exists is True

    def test_has_field_not_exists(self, valid_payload):
        """Test checking if field doesn't exist."""
        exists = MetadataHandler.has_field(valid_payload, "nonexistent_field")

        assert exists is False

    def test_filter_sensitive_fields(self, valid_payload):
        """Test filtering sensitive fields from payload."""
        filtered = MetadataHandler.filter_sensitive_fields(valid_payload)

        assert filtered[QdrantSchema.FIELD_RESPONSE] == "[REDACTED]"
        assert filtered[QdrantSchema.FIELD_QUERY_HASH] == "abc123"
        # Original should be unchanged
        assert valid_payload[QdrantSchema.FIELD_RESPONSE] == "It's sunny today"

    def test_get_metadata_summary(self, valid_payload):
        """Test getting metadata summary."""
        summary = MetadataHandler.get_metadata_summary(valid_payload)

        assert summary["query_hash"] == "abc123"
        assert summary["provider"] == "openai"
        assert summary["model"] == "gpt-4"
        assert summary["prompt_tokens"] == 10
        assert summary["completion_tokens"] == 5
        assert summary["has_tags"] is False
        assert summary["has_metadata"] is False

    def test_get_metadata_summary_with_tags_and_metadata(self):
        """Test getting metadata summary with tags and metadata."""
        payload = {
            QdrantSchema.FIELD_QUERY_HASH: "abc123",
            QdrantSchema.FIELD_PROVIDER: "openai",
            QdrantSchema.FIELD_MODEL: "gpt-4",
            QdrantSchema.FIELD_TAGS: ["tag1"],
            QdrantSchema.FIELD_METADATA: {"key": "value"},
        }

        summary = MetadataHandler.get_metadata_summary(payload)

        assert summary["has_tags"] is True
        assert summary["has_metadata"] is True

    def test_merge_payloads_simple(self):
        """Test merging two payloads."""
        base = {"field1": "value1", "field2": "value2"}
        updates = {"field2": "new_value2", "field3": "value3"}

        merged = MetadataHandler.merge_payloads(base, updates)

        assert merged["field1"] == "value1"
        assert merged["field2"] == "new_value2"
        assert merged["field3"] == "value3"

    def test_merge_payloads_combines_tags(self):
        """Test merging payloads combines tags."""
        base = {QdrantSchema.FIELD_TAGS: ["tag1", "tag2"]}
        updates = {QdrantSchema.FIELD_TAGS: ["tag2", "tag3"]}

        merged = MetadataHandler.merge_payloads(base, updates)

        assert set(merged[QdrantSchema.FIELD_TAGS]) == {"tag1", "tag2", "tag3"}

    def test_merge_payloads_merges_metadata(self):
        """Test merging payloads merges metadata dicts."""
        base = {QdrantSchema.FIELD_METADATA: {"key1": "value1", "key2": "value2"}}
        updates = {
            QdrantSchema.FIELD_METADATA: {"key2": "new_value2", "key3": "value3"}
        }

        merged = MetadataHandler.merge_payloads(base, updates)

        assert merged[QdrantSchema.FIELD_METADATA]["key1"] == "value1"
        assert merged[QdrantSchema.FIELD_METADATA]["key2"] == "new_value2"
        assert merged[QdrantSchema.FIELD_METADATA]["key3"] == "value3"

    def test_merge_payloads_preserves_original(self):
        """Test merging payloads doesn't modify originals."""
        base = {"field1": "value1"}
        updates = {"field2": "value2"}

        merged = MetadataHandler.merge_payloads(base, updates)

        assert "field2" not in base
        assert "field1" not in updates
        assert merged["field1"] == "value1"
        assert merged["field2"] == "value2"
