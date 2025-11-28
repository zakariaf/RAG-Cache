"""Unit tests for Query Validator."""

import pytest

from app.exceptions import ValidationError
from app.pipeline.query_validator import (
    QueryValidator,
    ValidationResult,
    validate_query,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_success_result(self):
        """Test successful validation result."""
        result = ValidationResult.success()
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_success_with_warnings(self):
        """Test success with warnings."""
        result = ValidationResult.success(warnings=["warning1"])
        assert result.is_valid is True
        assert result.has_warnings is True
        assert "warning1" in result.warnings

    def test_failure_result(self):
        """Test failed validation result."""
        result = ValidationResult.failure(["error1", "error2"])
        assert result.is_valid is False
        assert result.has_errors is True
        assert len(result.errors) == 2


class TestQueryValidator:
    """Tests for QueryValidator class."""

    @pytest.fixture
    def validator(self):
        """Create validator with default settings."""
        return QueryValidator()

    def test_validate_valid_query(self, validator):
        """Test valid query passes."""
        result = validator.validate("What is Python?")
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_none_query(self, validator):
        """Test None query fails."""
        result = validator.validate(None)
        assert result.is_valid is False
        assert "None" in result.errors[0]

    def test_validate_empty_query(self, validator):
        """Test empty query fails."""
        result = validator.validate("")
        assert result.is_valid is False
        assert "empty" in result.errors[0].lower()

    def test_validate_whitespace_only(self, validator):
        """Test whitespace-only query fails."""
        result = validator.validate("   ")
        assert result.is_valid is False

    def test_validate_too_long_query(self):
        """Test overly long query fails."""
        validator = QueryValidator(max_length=100)
        long_query = "x" * 200
        result = validator.validate(long_query)
        assert result.is_valid is False
        assert "too long" in result.errors[0].lower()

    def test_validate_too_short_query(self):
        """Test too short query fails."""
        validator = QueryValidator(min_length=10)
        result = validator.validate("short")
        assert result.is_valid is False
        assert "too short" in result.errors[0].lower()

    def test_validate_excessive_repetition_warning(self, validator):
        """Test excessive repetition generates warning."""
        result = validator.validate("hello aaaaaaaaaa world")
        assert result.is_valid is True
        assert result.has_warnings is True
        assert "repetition" in result.warnings[0].lower()

    def test_validate_or_raise_success(self, validator):
        """Test validate_or_raise on valid query."""
        # Should not raise
        validator.validate_or_raise("Valid query")

    def test_validate_or_raise_failure(self, validator):
        """Test validate_or_raise on invalid query."""
        with pytest.raises(ValidationError):
            validator.validate_or_raise("")

    def test_is_valid_shortcut(self, validator):
        """Test is_valid shortcut method."""
        assert validator.is_valid("Valid query") is True
        assert validator.is_valid("") is False

    def test_get_constraints(self, validator):
        """Test constraints retrieval."""
        constraints = validator.get_constraints()
        assert "min_length" in constraints
        assert "max_length" in constraints
        assert "max_tokens_estimate" in constraints
        assert "block_empty" in constraints

    def test_custom_constraints(self):
        """Test custom constraint configuration."""
        validator = QueryValidator(min_length=5, max_length=50, block_empty=False)
        constraints = validator.get_constraints()
        assert constraints["min_length"] == 5
        assert constraints["max_length"] == 50
        assert constraints["block_empty"] is False

    def test_default_validator_function(self):
        """Test convenience function."""
        result = validate_query("What is AI?")
        assert result.is_valid is True
