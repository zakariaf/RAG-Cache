"""Unit tests for Query Normalizer."""

import pytest

from app.pipeline.query_normalizer import QueryNormalizer, normalize_query


class TestQueryNormalizer:
    """Tests for QueryNormalizer class."""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer with default settings."""
        return QueryNormalizer()

    def test_normalize_lowercase(self, normalizer):
        """Test lowercase conversion."""
        result = normalizer.normalize("Hello WORLD")
        assert result == "hello world"

    def test_normalize_strip_whitespace(self, normalizer):
        """Test whitespace stripping."""
        result = normalizer.normalize("  hello world  ")
        assert result == "hello world"

    def test_normalize_collapse_spaces(self, normalizer):
        """Test multiple spaces collapsed."""
        result = normalizer.normalize("hello    world")
        assert result == "hello world"

    def test_normalize_empty_string(self, normalizer):
        """Test empty string handling."""
        result = normalizer.normalize("")
        assert result == ""

    def test_normalize_unicode(self, normalizer):
        """Test unicode normalization."""
        # Composed vs decomposed é
        result1 = normalizer.normalize("café")  # composed
        result2 = normalizer.normalize("café")  # could be decomposed
        assert result1 == result2

    def test_normalize_with_punctuation_removal(self):
        """Test punctuation removal when enabled."""
        normalizer = QueryNormalizer(remove_punctuation=True)
        result = normalizer.normalize("Hello, world!")
        assert result == "hello world"

    def test_normalize_preserves_punctuation_by_default(self, normalizer):
        """Test punctuation preserved by default."""
        result = normalizer.normalize("Hello, world!")
        assert result == "hello, world!"

    def test_normalize_batch(self, normalizer):
        """Test batch normalization."""
        queries = ["Hello World", "TESTING", "  spaces  "]
        results = normalizer.normalize_batch(queries)
        assert results == ["hello world", "testing", "spaces"]

    def test_normalize_config(self, normalizer):
        """Test configuration retrieval."""
        config = normalizer.get_config()
        assert config["lowercase"] is True
        assert config["strip_whitespace"] is True
        assert config["collapse_whitespace"] is True
        assert config["remove_punctuation"] is False
        assert config["unicode_normalize"] is True

    def test_normalize_custom_config(self):
        """Test custom configuration."""
        normalizer = QueryNormalizer(
            lowercase=False, strip_whitespace=False, collapse_whitespace=False
        )
        result = normalizer.normalize("  Hello  ")
        assert result == "  Hello  "

    def test_default_normalizer_function(self):
        """Test convenience function."""
        result = normalize_query("  Hello WORLD  ")
        assert result == "hello world"

