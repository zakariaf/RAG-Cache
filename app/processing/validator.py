"""
Query validator.

Validates query text and parameters.

Sandi Metz Principles:
- Single Responsibility: Query validation
- Small methods: Each method < 10 lines
- Clear naming: Descriptive validation rules
"""

from typing import List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueryValidationError(Exception):
    """Query validation error."""

    def __init__(self, message: str, field: Optional[str] = None):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
        """
        super().__init__(message)
        self.field = field
        self.message = message


class QueryValidator:
    """
    Validates query text and parameters.

    Enforces rules for:
    - Query length (min/max)
    - Empty/whitespace-only queries
    - Character restrictions
    - Content requirements
    """

    def __init__(
        self,
        min_length: int = 1,
        max_length: int = 10000,
        allow_empty: bool = False,
        allow_whitespace_only: bool = False,
        required_words: Optional[List[str]] = None,
        forbidden_words: Optional[List[str]] = None,
    ):
        """
        Initialize query validator.

        Args:
            min_length: Minimum query length
            max_length: Maximum query length
            allow_empty: Allow empty queries
            allow_whitespace_only: Allow whitespace-only queries
            required_words: Words that must appear in query
            forbidden_words: Words that must not appear in query
        """
        self._min_length = min_length
        self._max_length = max_length
        self._allow_empty = allow_empty
        self._allow_whitespace_only = allow_whitespace_only
        self._required_words = required_words or []
        self._forbidden_words = forbidden_words or []

    def validate(self, query: str) -> None:
        """
        Validate query text.

        Args:
            query: Query text to validate

        Raises:
            QueryValidationError: If validation fails
        """
        # Check for None
        if query is None:
            raise QueryValidationError("Query cannot be None", field="query")

        # Check empty
        if not self._allow_empty and len(query) == 0:
            raise QueryValidationError("Query cannot be empty", field="query")

        # Check whitespace-only
        if not self._allow_whitespace_only and len(query.strip()) == 0:
            raise QueryValidationError("Query cannot be whitespace-only", field="query")

        # Check minimum length
        if len(query) < self._min_length:
            raise QueryValidationError(
                f"Query too short (min {self._min_length} characters)", field="query"
            )

        # Check maximum length
        if len(query) > self._max_length:
            raise QueryValidationError(
                f"Query too long (max {self._max_length} characters)", field="query"
            )

        # Check required words
        if self._required_words:
            self._check_required_words(query)

        # Check forbidden words
        if self._forbidden_words:
            self._check_forbidden_words(query)

        logger.debug("Query validated successfully", query_length=len(query))

    def _check_required_words(self, query: str) -> None:
        """
        Check if required words are present.

        Args:
            query: Query text

        Raises:
            QueryValidationError: If required word is missing
        """
        query_lower = query.lower()
        for word in self._required_words:
            if word.lower() not in query_lower:
                raise QueryValidationError(
                    f"Query must contain '{word}'", field="query"
                )

    def _check_forbidden_words(self, query: str) -> None:
        """
        Check if forbidden words are absent.

        Args:
            query: Query text

        Raises:
            QueryValidationError: If forbidden word is found
        """
        query_lower = query.lower()
        for word in self._forbidden_words:
            if word.lower() in query_lower:
                raise QueryValidationError(
                    f"Query cannot contain '{word}'", field="query"
                )

    def is_valid(self, query: str) -> bool:
        """
        Check if query is valid without raising exception.

        Args:
            query: Query text

        Returns:
            True if valid, False otherwise
        """
        try:
            self.validate(query)
            return True
        except QueryValidationError:
            return False

    def validate_batch(self, queries: List[str]) -> None:
        """
        Validate multiple queries.

        Args:
            queries: List of query texts

        Raises:
            QueryValidationError: If any query is invalid
        """
        if queries is None:
            raise QueryValidationError("Queries list cannot be None", field="queries")

        for i, query in enumerate(queries):
            try:
                self.validate(query)
            except QueryValidationError as e:
                raise QueryValidationError(
                    f"Query at index {i} failed validation: {e.message}",
                    field=f"queries[{i}]",
                ) from e

        logger.debug("Batch validated successfully", count=len(queries))

    def get_validation_errors(self, query: str) -> List[str]:
        """
        Get all validation errors for a query.

        Args:
            query: Query text

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        try:
            self.validate(query)
        except QueryValidationError as e:
            errors.append(e.message)

        return errors

    def get_config(self) -> dict:
        """
        Get validator configuration.

        Returns:
            Dictionary with validation settings
        """
        return {
            "min_length": self._min_length,
            "max_length": self._max_length,
            "allow_empty": self._allow_empty,
            "allow_whitespace_only": self._allow_whitespace_only,
            "required_words": self._required_words.copy(),
            "forbidden_words": self._forbidden_words.copy(),
        }


class LLMQueryValidator(QueryValidator):
    """
    Validator specifically for LLM queries.

    Adds LLM-specific validation rules:
    - Token count estimation
    - Prompt injection detection
    - SQL injection detection
    """

    def __init__(
        self,
        min_length: int = 1,
        max_length: int = 10000,
        max_tokens: int = 2048,
        check_prompt_injection: bool = True,
        check_sql_injection: bool = True,
    ):
        """
        Initialize LLM query validator.

        Args:
            min_length: Minimum query length
            max_length: Maximum query length
            max_tokens: Maximum estimated token count
            check_prompt_injection: Check for prompt injection attempts
            check_sql_injection: Check for SQL injection attempts
        """
        super().__init__(
            min_length=min_length,
            max_length=max_length,
            allow_empty=False,
            allow_whitespace_only=False,
        )
        self._max_tokens = max_tokens
        self._check_prompt_injection = check_prompt_injection
        self._check_sql_injection = check_sql_injection

        # Prompt injection patterns
        self._prompt_injection_patterns = [
            "ignore previous",
            "ignore all previous",
            "disregard previous",
            "forget previous",
            "new instructions",
            "system:",
            "assistant:",
            "<|im_start|>",
            "<|im_end|>",
        ]

        # SQL injection patterns
        self._sql_injection_patterns = [
            "drop table",
            "delete from",
            "insert into",
            "update set",
            "union select",
            "or 1=1",
            "'; --",
            "' or '1'='1",
        ]

    def validate(self, query: str) -> None:
        """
        Validate LLM query with additional checks.

        Args:
            query: Query text

        Raises:
            QueryValidationError: If validation fails
        """
        # Run base validation
        super().validate(query)

        # Check token count estimate
        estimated_tokens = self._estimate_tokens(query)
        if estimated_tokens > self._max_tokens:
            raise QueryValidationError(
                f"Query too long ({estimated_tokens} tokens, max {self._max_tokens})",
                field="query",
            )

        # Check prompt injection
        if self._check_prompt_injection:
            self._check_prompt_injection_patterns(query)

        # Check SQL injection
        if self._check_sql_injection:
            self._check_sql_injection_patterns(query)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        Estimate token count for text.

        Uses simple heuristic: ~4 characters per token.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return max(1, len(text) // 4)

    def _check_prompt_injection_patterns(self, query: str) -> None:
        """
        Check for prompt injection patterns.

        Args:
            query: Query text

        Raises:
            QueryValidationError: If potential injection detected
        """
        query_lower = query.lower()
        for pattern in self._prompt_injection_patterns:
            if pattern.lower() in query_lower:
                logger.warning(
                    "Potential prompt injection detected",
                    pattern=pattern,
                    query=query[:100],
                )
                raise QueryValidationError(
                    f"Potential prompt injection detected: '{pattern}'",
                    field="query",
                )

    def _check_sql_injection_patterns(self, query: str) -> None:
        """
        Check for SQL injection patterns.

        Args:
            query: Query text

        Raises:
            QueryValidationError: If potential injection detected
        """
        query_lower = query.lower()
        for pattern in self._sql_injection_patterns:
            if pattern.lower() in query_lower:
                logger.warning(
                    "Potential SQL injection detected",
                    pattern=pattern,
                    query=query[:100],
                )
                raise QueryValidationError(
                    f"Potential SQL injection detected: '{pattern}'",
                    field="query",
                )


# Convenience function
def validate_query(
    query: str,
    min_length: int = 1,
    max_length: int = 10000,
) -> None:
    """
    Validate query (convenience function).

    Args:
        query: Query text
        min_length: Minimum length
        max_length: Maximum length

    Raises:
        QueryValidationError: If validation fails
    """
    validator = QueryValidator(min_length=min_length, max_length=max_length)
    validator.validate(query)
