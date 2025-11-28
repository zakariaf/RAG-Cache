"""
Query Validator Service.

Validates user queries before processing.

Sandi Metz Principles:
- Single Responsibility: Query validation
- Small methods: Each validation isolated
- Clear errors: Descriptive validation messages
"""

from dataclasses import dataclass
from typing import List, Optional

from app.exceptions import ValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of query validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]

    @property
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0

    @classmethod
    def success(cls, warnings: Optional[List[str]] = None) -> "ValidationResult":
        """Create successful validation result."""
        return cls(is_valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def failure(cls, errors: List[str]) -> "ValidationResult":
        """Create failed validation result."""
        return cls(is_valid=False, errors=errors, warnings=[])


class QueryValidator:
    """
    Validates queries meet processing requirements.

    Checks length, content, and safety constraints.
    """

    # Default constraints
    DEFAULT_MIN_LENGTH = 1
    DEFAULT_MAX_LENGTH = 10000
    DEFAULT_MAX_TOKENS_ESTIMATE = 4000

    def __init__(
        self,
        min_length: int = DEFAULT_MIN_LENGTH,
        max_length: int = DEFAULT_MAX_LENGTH,
        max_tokens_estimate: int = DEFAULT_MAX_TOKENS_ESTIMATE,
        block_empty: bool = True,
    ):
        """
        Initialize validator with constraints.

        Args:
            min_length: Minimum query length
            max_length: Maximum query length
            max_tokens_estimate: Estimated max tokens
            block_empty: Block empty queries
        """
        self._min_length = min_length
        self._max_length = max_length
        self._max_tokens_estimate = max_tokens_estimate
        self._block_empty = block_empty

    def validate(self, query: str) -> ValidationResult:
        """
        Validate a query string.

        Args:
            query: Query to validate

        Returns:
            ValidationResult with status and messages
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Check for None
        if query is None:
            errors.append("Query cannot be None")
            return ValidationResult.failure(errors)

        # Check empty
        if self._block_empty and not query.strip():
            errors.append("Query cannot be empty")
            return ValidationResult.failure(errors)

        # Check minimum length
        if len(query) < self._min_length:
            errors.append(f"Query too short (min {self._min_length} chars)")

        # Check maximum length
        if len(query) > self._max_length:
            errors.append(f"Query too long (max {self._max_length} chars)")

        # Check token estimate
        token_estimate = self._estimate_tokens(query)
        if token_estimate > self._max_tokens_estimate:
            warnings.append(
                f"Query may exceed token limit (estimated {token_estimate} tokens)"
            )

        # Check for potential issues
        if self._has_excessive_repetition(query):
            warnings.append("Query contains excessive repetition")

        if errors:
            logger.warning("Query validation failed", errors=errors)
            return ValidationResult.failure(errors)

        if warnings:
            logger.info("Query validation passed with warnings", warnings=warnings)

        return ValidationResult.success(warnings)

    def validate_or_raise(self, query: str) -> None:
        """
        Validate query and raise exception on failure.

        Args:
            query: Query to validate

        Raises:
            ValidationError: If validation fails
        """
        result = self.validate(query)
        if not result.is_valid:
            raise ValidationError("; ".join(result.errors))

    def is_valid(self, query: str) -> bool:
        """
        Quick check if query is valid.

        Args:
            query: Query to validate

        Returns:
            True if valid
        """
        return self.validate(query).is_valid

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        Estimate token count (rough approximation).

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 chars per token for English
        return len(text) // 4

    @staticmethod
    def _has_excessive_repetition(text: str, threshold: int = 10) -> bool:
        """
        Check for excessive character repetition.

        Args:
            text: Input text
            threshold: Max allowed consecutive repeats

        Returns:
            True if excessive repetition found
        """
        if not text:
            return False

        count = 1
        for i in range(1, len(text)):
            if text[i] == text[i - 1]:
                count += 1
                if count >= threshold:
                    return True
            else:
                count = 1
        return False

    def get_constraints(self) -> dict:
        """
        Get validator constraints.

        Returns:
            Constraints dict
        """
        return {
            "min_length": self._min_length,
            "max_length": self._max_length,
            "max_tokens_estimate": self._max_tokens_estimate,
            "block_empty": self._block_empty,
        }


# Default validator instance
default_validator = QueryValidator()


def validate_query(query: str) -> ValidationResult:
    """
    Validate query using default settings.

    Args:
        query: Query to validate

    Returns:
        ValidationResult
    """
    return default_validator.validate(query)
