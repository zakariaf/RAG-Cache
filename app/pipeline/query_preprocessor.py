"""
Query Preprocessor Service.

Orchestrates query normalization and validation.

Sandi Metz Principles:
- Single Responsibility: Query preprocessing
- Dependency Injection: Normalizer and validator injected
- Composable: Pipeline steps configurable
"""

from dataclasses import dataclass
from typing import Optional

from app.pipeline.query_normalizer import QueryNormalizer, default_normalizer
from app.pipeline.query_validator import (
    QueryValidator,
    ValidationResult,
    default_validator,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PreprocessResult:
    """Result of query preprocessing."""

    original_query: str
    normalized_query: str
    is_valid: bool
    validation_result: ValidationResult

    @property
    def query(self) -> str:
        """Get the processed query."""
        return self.normalized_query if self.is_valid else self.original_query


class QueryPreprocessor:
    """
    Preprocesses queries before cache lookup and LLM calls.

    Combines validation and normalization.
    """

    def __init__(
        self,
        normalizer: Optional[QueryNormalizer] = None,
        validator: Optional[QueryValidator] = None,
        normalize_before_validate: bool = False,
    ):
        """
        Initialize preprocessor with components.

        Args:
            normalizer: Query normalizer instance
            validator: Query validator instance
            normalize_before_validate: Normalize before validating
        """
        self._normalizer = normalizer or default_normalizer
        self._validator = validator or default_validator
        self._normalize_first = normalize_before_validate

    def process(self, query: str) -> PreprocessResult:
        """
        Preprocess a query.

        Args:
            query: Raw query string

        Returns:
            PreprocessResult with validation and normalization
        """
        original = query

        if self._normalize_first:
            # Normalize then validate
            normalized = self._normalizer.normalize(query)
            validation = self._validator.validate(normalized)
        else:
            # Validate then normalize
            validation = self._validator.validate(query)
            normalized = (
                self._normalizer.normalize(query) if validation.is_valid else query
            )

        result = PreprocessResult(
            original_query=original,
            normalized_query=normalized,
            is_valid=validation.is_valid,
            validation_result=validation,
        )

        logger.info(
            "Query preprocessed",
            valid=result.is_valid,
            original_len=len(original),
            normalized_len=len(result.normalized_query),
        )

        return result

    def process_or_raise(self, query: str) -> str:
        """
        Preprocess query, raising on validation failure.

        Args:
            query: Raw query string

        Returns:
            Normalized query string

        Raises:
            ValidationError: If validation fails
        """
        from app.exceptions import ValidationError

        result = self.process(query)
        if not result.is_valid:
            raise ValidationError("; ".join(result.validation_result.errors))
        return result.normalized_query

    def get_normalized(self, query: str) -> str:
        """
        Get normalized query (skip validation).

        Args:
            query: Raw query string

        Returns:
            Normalized query string
        """
        return self._normalizer.normalize(query)

    def validate_only(self, query: str) -> ValidationResult:
        """
        Validate query only (skip normalization).

        Args:
            query: Raw query string

        Returns:
            ValidationResult
        """
        return self._validator.validate(query)


# Default preprocessor instance
default_preprocessor = QueryPreprocessor()


def preprocess_query(query: str) -> PreprocessResult:
    """
    Preprocess query using default settings.

    Args:
        query: Raw query string

    Returns:
        PreprocessResult
    """
    return default_preprocessor.process(query)
