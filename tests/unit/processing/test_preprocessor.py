"""Test query preprocessor."""

import pytest

from app.processing.normalizer import QueryNormalizer
from app.processing.preprocessor import (
    LenientQueryPreprocessor,
    PreprocessedQuery,
    PreprocessingError,
    QueryPreprocessor,
    StrictQueryPreprocessor,
    preprocess_query,
)
from app.processing.validator import QueryValidationError, QueryValidator


class TestPreprocessedQuery:
    """Test PreprocessedQuery class."""

    def test_create_preprocessed_query(self):
        """Test creating PreprocessedQuery."""
        result = PreprocessedQuery(
            original="HELLO",
            normalized="hello",
            is_valid=True,
        )
        assert result.original == "HELLO"
        assert result.normalized == "hello"
        assert result.is_valid is True

    def test_preprocessed_query_str(self):
        """Test string representation."""
        result = PreprocessedQuery(original="HELLO", normalized="hello")
        assert str(result) == "hello"

    def test_preprocessed_query_repr(self):
        """Test detailed representation."""
        result = PreprocessedQuery(original="HELLO", normalized="hello")
        repr_str = repr(result)
        assert "PreprocessedQuery" in repr_str
        assert "is_valid" in repr_str


class TestQueryPreprocessor:
    """Test QueryPreprocessor class."""

    def test_preprocess_valid_query(self):
        """Test preprocessing valid query."""
        preprocessor = QueryPreprocessor()
        result = preprocessor.preprocess("  HELLO WORLD  ")
        assert result.is_valid is True
        assert result.normalized == "hello world"

    def test_preprocess_none_raises(self):
        """Test preprocessing None raises error."""
        preprocessor = QueryPreprocessor()
        with pytest.raises(PreprocessingError, match="cannot be None"):
            preprocessor.preprocess(None)

    def test_preprocess_with_custom_normalizer(self):
        """Test preprocessing with custom normalizer."""
        normalizer = QueryNormalizer(lowercase=True, strip_whitespace=True)
        preprocessor = QueryPreprocessor(normalizer=normalizer)
        result = preprocessor.preprocess("  HELLO  ")
        assert result.normalized == "hello"

    def test_preprocess_with_custom_validator(self):
        """Test preprocessing with custom validator."""
        validator = QueryValidator(min_length=5)
        preprocessor = QueryPreprocessor(validator=validator)

        # Valid query
        result = preprocessor.preprocess("hello")
        assert result.is_valid is True

        # Invalid query with raise_on_validation_error=True
        with pytest.raises(QueryValidationError):
            preprocessor.preprocess("hi")

    def test_preprocess_validation_error_collected(self):
        """Test validation errors are collected when not raising."""
        validator = QueryValidator(min_length=10)
        preprocessor = QueryPreprocessor(
            validator=validator,
            raise_on_validation_error=False,
        )
        result = preprocessor.preprocess("short")
        assert result.is_valid is False
        assert len(result.validation_errors) > 0

    def test_preprocess_validate_before_normalize(self):
        """Test validation before normalization."""
        normalizer = QueryNormalizer(lowercase=True)
        validator = QueryValidator(min_length=5)
        preprocessor = QueryPreprocessor(
            normalizer=normalizer,
            validator=validator,
            validate_before_normalize=True,
        )
        result = preprocessor.preprocess("HELLO")
        assert result.is_valid is True

    def test_preprocess_batch(self):
        """Test batch preprocessing."""
        preprocessor = QueryPreprocessor()
        results = preprocessor.preprocess_batch(["HELLO", "WORLD"])
        assert len(results) == 2
        assert all(r.is_valid for r in results)

    def test_preprocess_batch_none_raises(self):
        """Test batch preprocessing with None raises error."""
        preprocessor = QueryPreprocessor()
        with pytest.raises(PreprocessingError, match="cannot be None"):
            preprocessor.preprocess_batch(None)

    def test_is_valid_query(self):
        """Test is_valid_query method."""
        preprocessor = QueryPreprocessor()
        assert preprocessor.is_valid_query("hello world")

    def test_get_normalized_query(self):
        """Test get_normalized_query method."""
        preprocessor = QueryPreprocessor()
        normalized = preprocessor.get_normalized_query("  HELLO  ")
        assert normalized == "hello"

    def test_validate_only(self):
        """Test validate_only method."""
        preprocessor = QueryPreprocessor()
        preprocessor.validate_only("hello")  # Should not raise

    def test_set_normalizer(self):
        """Test set_normalizer method."""
        preprocessor = QueryPreprocessor()
        new_normalizer = QueryNormalizer(lowercase=False)
        preprocessor.set_normalizer(new_normalizer)
        result = preprocessor.preprocess("HELLO")
        assert result.normalized == "HELLO"

    def test_set_validator(self):
        """Test set_validator method."""
        preprocessor = QueryPreprocessor()
        new_validator = QueryValidator(min_length=10)
        preprocessor.set_validator(new_validator)
        with pytest.raises(QueryValidationError):
            preprocessor.preprocess("short")

    def test_get_config(self):
        """Test get_config returns configuration."""
        preprocessor = QueryPreprocessor()
        config = preprocessor.get_config()
        assert "normalizer" in config
        assert "validator" in config


class TestLenientQueryPreprocessor:
    """Test LenientQueryPreprocessor class."""

    def test_lenient_does_not_raise(self):
        """Test lenient preprocessor doesn't raise on validation errors."""
        preprocessor = LenientQueryPreprocessor()
        # Add a strict validator
        preprocessor.set_validator(QueryValidator(min_length=100))

        result = preprocessor.preprocess("short")
        assert result.is_valid is False
        assert len(result.validation_errors) > 0


class TestStrictQueryPreprocessor:
    """Test StrictQueryPreprocessor class."""

    def test_strict_validates_before_normalize(self):
        """Test strict preprocessor validates before normalizing."""
        preprocessor = StrictQueryPreprocessor()
        preprocessor.set_validator(QueryValidator(min_length=3))

        with pytest.raises(QueryValidationError):
            preprocessor.preprocess("hi")


def test_preprocess_query_convenience():
    """Test preprocess_query convenience function."""
    result = preprocess_query("  HELLO  ")
    assert result.is_valid is True
    assert result.normalized == "hello"
