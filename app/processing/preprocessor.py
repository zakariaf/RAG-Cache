"""
Query preprocessor.

Combines normalization and validation into preprocessing pipeline.

Sandi Metz Principles:
- Single Responsibility: Query preprocessing
- Small methods: Each method < 10 lines
- Dependency Injection: Normalizer and validator injected
"""

from typing import List, Optional

from app.processing.normalizer import QueryNormalizer
from app.processing.validator import QueryValidationError, QueryValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PreprocessingError(Exception):
    """Query preprocessing error."""

    pass


class PreprocessedQuery:
    """
    Result of query preprocessing.

    Contains original and normalized query along with metadata.
    """

    def __init__(
        self,
        original: str,
        normalized: str,
        is_valid: bool = True,
        validation_errors: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Initialize preprocessed query.

        Args:
            original: Original query text
            normalized: Normalized query text
            is_valid: Whether query passed validation
            validation_errors: List of validation errors if any
            metadata: Additional preprocessing metadata
        """
        self.original = original
        self.normalized = normalized
        self.is_valid = is_valid
        self.validation_errors = validation_errors or []
        self.metadata = metadata or {}

    def __str__(self) -> str:
        """String representation."""
        return self.normalized

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"PreprocessedQuery(original='{self.original[:50]}...', "
            f"normalized='{self.normalized[:50]}...', is_valid={self.is_valid})"
        )


class QueryPreprocessor:
    """
    Preprocesses queries through normalization and validation pipeline.

    Combines QueryNormalizer and QueryValidator into single preprocessing
    step with configurable error handling.
    """

    def __init__(
        self,
        normalizer: Optional[QueryNormalizer] = None,
        validator: Optional[QueryValidator] = None,
        validate_before_normalize: bool = False,
        raise_on_validation_error: bool = True,
    ):
        """
        Initialize query preprocessor.

        Args:
            normalizer: Query normalizer (uses default if None)
            validator: Query validator (uses default if None)
            validate_before_normalize: If True, validate before normalizing
            raise_on_validation_error: If True, raise exception on validation errors
        """
        self._normalizer = normalizer or QueryNormalizer()
        self._validator = validator or QueryValidator()
        self._validate_before_normalize = validate_before_normalize
        self._raise_on_validation_error = raise_on_validation_error

    def preprocess(self, query: str) -> PreprocessedQuery:
        """
        Preprocess query through normalization and validation.

        Args:
            query: Raw query text

        Returns:
            Preprocessed query result

        Raises:
            PreprocessingError: If preprocessing fails
            QueryValidationError: If validation fails (when raise_on_validation_error=True)
        """
        if query is None:
            raise PreprocessingError("Query cannot be None")

        try:
            original = query
            normalized = query
            is_valid = True
            validation_errors = []

            # Step 1: Optional pre-normalization validation
            if self._validate_before_normalize:
                try:
                    self._validator.validate(query)
                except QueryValidationError as e:
                    is_valid = False
                    validation_errors.append(e.message)
                    if self._raise_on_validation_error:
                        raise
                    # If not raising, continue with normalization

            # Step 2: Normalize query
            normalized = self._normalizer.normalize(query)

            # Step 3: Post-normalization validation (default)
            if not self._validate_before_normalize:
                try:
                    self._validator.validate(normalized)
                except QueryValidationError as e:
                    is_valid = False
                    validation_errors.append(e.message)
                    if self._raise_on_validation_error:
                        raise

            logger.debug(
                "Preprocessed query",
                original_length=len(original),
                normalized_length=len(normalized),
                is_valid=is_valid,
                changed=original != normalized,
            )

            return PreprocessedQuery(
                original=original,
                normalized=normalized,
                is_valid=is_valid,
                validation_errors=validation_errors,
                metadata={
                    "original_length": len(original),
                    "normalized_length": len(normalized),
                    "changed": original != normalized,
                },
            )

        except QueryValidationError:
            # Re-raise validation errors if configured to do so
            raise
        except Exception as e:
            logger.error("Query preprocessing failed", error=str(e))
            raise PreprocessingError(f"Failed to preprocess query: {str(e)}") from e

    def preprocess_batch(self, queries: List[str]) -> List[PreprocessedQuery]:
        """
        Preprocess multiple queries.

        Args:
            queries: List of query texts

        Returns:
            List of preprocessed query results

        Raises:
            PreprocessingError: If preprocessing fails
            QueryValidationError: If validation fails (when raise_on_validation_error=True)
        """
        if queries is None:
            raise PreprocessingError("Queries list cannot be None")

        results = []

        for i, query in enumerate(queries):
            try:
                result = self.preprocess(query)
                results.append(result)
            except QueryValidationError as e:
                if self._raise_on_validation_error:
                    raise PreprocessingError(
                        f"Query at index {i} failed validation: {e.message}"
                    ) from e
                # If not raising, create invalid result
                results.append(
                    PreprocessedQuery(
                        original=query,
                        normalized=query,
                        is_valid=False,
                        validation_errors=[e.message],
                    )
                )

        logger.debug(
            "Preprocessed query batch",
            count=len(queries),
            valid_count=sum(1 for r in results if r.is_valid),
            invalid_count=sum(1 for r in results if not r.is_valid),
        )

        return results

    def is_valid_query(self, query: str) -> bool:
        """
        Check if query would pass preprocessing.

        Args:
            query: Query text

        Returns:
            True if query would be valid
        """
        try:
            result = self.preprocess(query)
            return result.is_valid
        except Exception:
            return False

    def get_normalized_query(self, query: str) -> str:
        """
        Get normalized query without full preprocessing.

        Args:
            query: Query text

        Returns:
            Normalized query text

        Raises:
            PreprocessingError: If normalization fails
        """
        try:
            return self._normalizer.normalize(query)
        except Exception as e:
            raise PreprocessingError(f"Failed to normalize query: {str(e)}") from e

    def validate_only(self, query: str) -> None:
        """
        Validate query without normalization.

        Args:
            query: Query text

        Raises:
            QueryValidationError: If validation fails
        """
        self._validator.validate(query)

    def set_normalizer(self, normalizer: QueryNormalizer) -> None:
        """
        Set new normalizer.

        Args:
            normalizer: Query normalizer
        """
        self._normalizer = normalizer
        logger.info("Updated query normalizer")

    def set_validator(self, validator: QueryValidator) -> None:
        """
        Set new validator.

        Args:
            validator: Query validator
        """
        self._validator = validator
        logger.info("Updated query validator")

    def get_config(self) -> dict:
        """
        Get preprocessor configuration.

        Returns:
            Dictionary with configuration
        """
        return {
            "normalizer": self._normalizer.get_config(),
            "validator": self._validator.get_config(),
            "validate_before_normalize": self._validate_before_normalize,
            "raise_on_validation_error": self._raise_on_validation_error,
        }


class LenientQueryPreprocessor(QueryPreprocessor):
    """
    Lenient preprocessor that doesn't raise on validation errors.

    Useful for scenarios where you want to process queries even if
    they don't pass strict validation.
    """

    def __init__(
        self,
        normalizer: Optional[QueryNormalizer] = None,
        validator: Optional[QueryValidator] = None,
    ):
        """
        Initialize lenient preprocessor.

        Args:
            normalizer: Query normalizer (uses default if None)
            validator: Query validator (uses default if None)
        """
        super().__init__(
            normalizer=normalizer,
            validator=validator,
            validate_before_normalize=False,
            raise_on_validation_error=False,
        )


class StrictQueryPreprocessor(QueryPreprocessor):
    """
    Strict preprocessor that validates before normalizing.

    Ensures raw input meets requirements before any transformation.
    """

    def __init__(
        self,
        normalizer: Optional[QueryNormalizer] = None,
        validator: Optional[QueryValidator] = None,
    ):
        """
        Initialize strict preprocessor.

        Args:
            normalizer: Query normalizer (uses default if None)
            validator: Query validator (uses default if None)
        """
        super().__init__(
            normalizer=normalizer,
            validator=validator,
            validate_before_normalize=True,
            raise_on_validation_error=True,
        )


# Convenience function
def preprocess_query(
    query: str,
    normalizer: Optional[QueryNormalizer] = None,
    validator: Optional[QueryValidator] = None,
) -> PreprocessedQuery:
    """
    Preprocess query (convenience function).

    Args:
        query: Query text
        normalizer: Query normalizer (optional)
        validator: Query validator (optional)

    Returns:
        Preprocessed query result
    """
    preprocessor = QueryPreprocessor(normalizer=normalizer, validator=validator)
    return preprocessor.preprocess(query)
