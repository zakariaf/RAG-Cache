"""Test hash utilities."""

import pytest

from app.utils.hasher import normalize_query, generate_cache_key, generate_embedding_key


class TestHashUtilities:
    """Test hash utility functions."""

    def test_should_normalize_query(self):
        """Test query normalization."""
        query = "  What is AI?  "
        normalized = normalize_query(query)
        assert normalized == "what is ai?"

    def test_should_generate_consistent_cache_keys(self):
        """Test cache key generation consistency."""
        query1 = "What is AI?"
        query2 = "what is ai?"
        key1 = generate_cache_key(query1)
        key2 = generate_cache_key(query2)
        assert key1 == key2

    def test_should_generate_different_keys_for_different_queries(self):
        """Test different queries generate different keys."""
        query1 = "What is AI?"
        query2 = "What is ML?"
        key1 = generate_cache_key(query1)
        key2 = generate_cache_key(query2)
        assert key1 != key2

    def test_cache_key_should_have_correct_prefix(self):
        """Test cache key format."""
        query = "test query"
        key = generate_cache_key(query)
        assert key.startswith("query:")

    def test_embedding_key_should_have_correct_prefix(self):
        """Test embedding key format."""
        query_hash = "abc123"
        key = generate_embedding_key(query_hash)
        assert key == "embedding:abc123"
