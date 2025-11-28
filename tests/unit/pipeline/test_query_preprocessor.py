"""Unit tests for Query Preprocessor."""

import pytest

from app.exceptions import ValidationError
from app.pipeline.query_preprocessor import (
    PreprocessResult,
    QueryPreprocessor,
    preprocess_query,
)
from app.pipeline.query_normalizer import QueryNormalizer
from app.pipeline.query_validator import QueryValidator


class TestPreprocessResult:
    """Tests for PreprocessResult dataclass."""

    def test_query_property_valid(self):
        """Test query property returns normalized when valid."""
        from app.pipeline.query_validator import ValidationResult

        result = PreprocessResult(
            original_query="Hello World",
            normalized_query="hello world",
            is_valid=True,
            validation_result=ValidationResult.success(),
        )
        assert result.query == "hello world"

    def test_query_property_invalid(self):
        """Test query property returns original when invalid."""
        from app.pipeline.query_validator import ValidationResult

        result = PreprocessResult(
            original_query="",
            normalized_query="",
            is_valid=False,
            validation_result=ValidationResult.failure(["empty"]),
        )
        assert result.query == ""


class TestQueryPreprocessor:
    """Tests for QueryPreprocessor class."""

    @pytest.fixture
    def preprocessor(self):
        """Create preprocessor with default settings."""
        return QueryPreprocessor()

    def test_process_valid_query(self, preprocessor):
        """Test processing valid query."""
        result = preprocessor.process("  Hello WORLD  ")
        assert result.is_valid is True
        assert result.normalized_query == "hello world"
        assert result.original_query == "  Hello WORLD  "

    def test_process_invalid_query(self, preprocessor):
        """Test processing invalid query."""
        result = preprocessor.process("")
        assert result.is_valid is False
        assert result.validation_result.has_errors is True

    def test_process_or_raise_success(self, preprocessor):
        """Test process_or_raise on valid query."""
        result = preprocessor.process_or_raise("Valid query")
        assert result == "valid query"

    def test_process_or_raise_failure(self, preprocessor):
        """Test process_or_raise on invalid query."""
        with pytest.raises(ValidationError):
            preprocessor.process_or_raise("")

    def test_get_normalized(self, preprocessor):
        """Test get_normalized bypasses validation."""
        result = preprocessor.get_normalized("  HELLO  ")
        assert result == "hello"

    def test_validate_only(self, preprocessor):
        """Test validate_only bypasses normalization."""
        result = preprocessor.validate_only("Valid query")
        assert result.is_valid is True

    def test_normalize_before_validate(self):
        """Test normalization before validation mode."""
        preprocessor = QueryPreprocessor(normalize_before_validate=True)
        result = preprocessor.process("  HELLO WORLD  ")
        assert result.is_valid is True
        assert result.normalized_query == "hello world"

    def test_custom_normalizer(self):
        """Test custom normalizer injection."""
        normalizer = QueryNormalizer(lowercase=False)
        preprocessor = QueryPreprocessor(normalizer=normalizer)
        result = preprocessor.process("Hello World")
        assert result.normalized_query == "Hello World"

    def test_custom_validator(self):
        """Test custom validator injection."""
        validator = QueryValidator(min_length=20)
        preprocessor = QueryPreprocessor(validator=validator)
        result = preprocessor.process("Short")
        assert result.is_valid is False

    def test_default_preprocessor_function(self):
        """Test convenience function."""
        result = preprocess_query("  Hello WORLD  ")
        assert result.is_valid is True
        assert result.normalized_query == "hello world"
