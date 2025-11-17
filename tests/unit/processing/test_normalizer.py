"""Test query normalizer."""

import pytest

from app.processing.normalizer import (
    QueryNormalizer,
    StrictQueryNormalizer,
    normalize_query,
)


class TestQueryNormalizer:
    """Test QueryNormalizer class."""

    def test_normalize_lowercase(self):
        """Test lowercase normalization."""
        normalizer = QueryNormalizer(lowercase=True)
        result = normalizer.normalize("HELLO WORLD")
        assert result == "hello world"

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        normalizer = QueryNormalizer(strip_whitespace=True)
        result = normalizer.normalize("  hello  ")
        assert result == "hello"

    def test_normalize_multiple_spaces(self):
        """Test multiple space collapsing."""
        normalizer = QueryNormalizer(remove_extra_spaces=True)
        result = normalizer.normalize("hello    world")
        assert result == "hello world"

    def test_normalize_unicode(self):
        """Test unicode normalization."""
        normalizer = QueryNormalizer(normalize_unicode=True)
        result = normalizer.normalize("café")
        assert isinstance(result, str)

    def test_normalize_all_options(self):
        """Test all normalization options together."""
        normalizer = QueryNormalizer(
            lowercase=True,
            strip_whitespace=True,
            normalize_unicode=True,
            remove_extra_spaces=True,
        )
        result = normalizer.normalize("  HELLO    WORLD  ")
        assert result == "hello world"

    def test_normalize_empty_string(self):
        """Test normalization of empty string."""
        normalizer = QueryNormalizer()
        result = normalizer.normalize("")
        assert result == ""

    def test_normalize_batch(self):
        """Test batch normalization."""
        normalizer = QueryNormalizer(lowercase=True)
        results = normalizer.normalize_batch(["HELLO", "WORLD"])
        assert results == ["hello", "world"]

    def test_normalize_batch_none_raises(self):
        """Test batch normalization with None raises error."""
        normalizer = QueryNormalizer()
        with pytest.raises(ValueError, match="cannot be None"):
            normalizer.normalize_batch(None)

    def test_is_normalized(self):
        """Test is_normalized check."""
        normalizer = QueryNormalizer(lowercase=True, strip_whitespace=True)
        assert normalizer.is_normalized("hello")
        assert not normalizer.is_normalized("HELLO")
        assert not normalizer.is_normalized("  hello  ")

    def test_get_config(self):
        """Test get_config returns configuration."""
        normalizer = QueryNormalizer(lowercase=False, strip_whitespace=True)
        config = normalizer.get_config()
        assert config["lowercase"] is False
        assert config["strip_whitespace"] is True


class TestStrictQueryNormalizer:
    """Test StrictQueryNormalizer class."""

    def test_remove_punctuation(self):
        """Test punctuation removal."""
        normalizer = StrictQueryNormalizer(remove_punctuation=True)
        result = normalizer.normalize("Hello, world!")
        assert result == "Hello world"

    def test_normalize_numbers(self):
        """Test number normalization."""
        normalizer = StrictQueryNormalizer(normalize_numbers=True)
        result = normalizer.normalize("I have 123 apples")
        assert result == "I have <NUM> apples"

    def test_strict_all_options(self):
        """Test all strict normalization options."""
        normalizer = StrictQueryNormalizer(
            lowercase=True,
            remove_punctuation=True,
            normalize_numbers=True,
        )
        result = normalizer.normalize("HELLO, I have 123 items!")
        assert result == "hello i have <NUM> items"


def test_normalize_query_convenience():
    """Test normalize_query convenience function."""
    result = normalize_query("  HELLO WORLD  ", lowercase=True, strip_whitespace=True)
    assert result == "hello world"
