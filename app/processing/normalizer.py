"""
Query normalizer.

Normalizes query text for consistent processing.

Sandi Metz Principles:
- Single Responsibility: Query normalization
- Small methods: Each method < 10 lines
- Clear naming: Descriptive method names
"""

import re
import unicodedata
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueryNormalizer:
    """
    Normalizes query text for consistent processing.

    Performs text normalization including:
    - Whitespace normalization
    - Case normalization
    - Unicode normalization
    - Special character handling
    """

    def __init__(
        self,
        lowercase: bool = True,
        strip_whitespace: bool = True,
        normalize_unicode: bool = True,
        remove_extra_spaces: bool = True,
    ):
        """
        Initialize query normalizer.

        Args:
            lowercase: Convert to lowercase
            strip_whitespace: Strip leading/trailing whitespace
            normalize_unicode: Normalize unicode characters (NFKC)
            remove_extra_spaces: Replace multiple spaces with single space
        """
        self._lowercase = lowercase
        self._strip_whitespace = strip_whitespace
        self._normalize_unicode = normalize_unicode
        self._remove_extra_spaces = remove_extra_spaces

    def normalize(self, query: str) -> str:
        """
        Normalize query text.

        Args:
            query: Raw query text

        Returns:
            Normalized query text

        Raises:
            ValueError: If query is None
        """
        if query is None:
            raise ValueError("Query cannot be None")

        original_length = len(query)
        normalized = query

        # Apply normalization steps in order
        if self._normalize_unicode:
            normalized = self._normalize_unicode_text(normalized)

        if self._strip_whitespace:
            normalized = normalized.strip()

        if self._remove_extra_spaces:
            normalized = self._remove_multiple_spaces(normalized)

        if self._lowercase:
            normalized = normalized.lower()

        logger.debug(
            "Normalized query",
            original_length=original_length,
            normalized_length=len(normalized),
            changed=query != normalized,
        )

        return normalized

    def _normalize_unicode_text(self, text: str) -> str:
        """
        Normalize unicode characters.

        Uses NFKC normalization (canonical decomposition followed by
        canonical composition with compatibility).

        Args:
            text: Text to normalize

        Returns:
            Unicode-normalized text
        """
        return unicodedata.normalize("NFKC", text)

    def _remove_multiple_spaces(self, text: str) -> str:
        """
        Replace multiple consecutive spaces with single space.

        Args:
            text: Text to process

        Returns:
            Text with normalized spacing
        """
        return re.sub(r"\s+", " ", text)

    def normalize_batch(self, queries: list[str]) -> list[str]:
        """
        Normalize multiple queries.

        Args:
            queries: List of query texts

        Returns:
            List of normalized queries

        Raises:
            ValueError: If queries list is None or contains None
        """
        if queries is None:
            raise ValueError("Queries list cannot be None")

        normalized = []
        for i, query in enumerate(queries):
            if query is None:
                raise ValueError(f"Query at index {i} cannot be None")
            normalized.append(self.normalize(query))

        logger.debug("Normalized query batch", count=len(queries))

        return normalized

    def is_normalized(self, query: str) -> bool:
        """
        Check if query is already normalized.

        Args:
            query: Query text to check

        Returns:
            True if query is normalized according to current settings
        """
        try:
            normalized = self.normalize(query)
            return query == normalized
        except Exception:
            return False

    def get_config(self) -> dict:
        """
        Get normalizer configuration.

        Returns:
            Dictionary with normalization settings
        """
        return {
            "lowercase": self._lowercase,
            "strip_whitespace": self._strip_whitespace,
            "normalize_unicode": self._normalize_unicode,
            "remove_extra_spaces": self._remove_extra_spaces,
        }


class StrictQueryNormalizer(QueryNormalizer):
    """
    Strict query normalizer with additional rules.

    Extends base normalizer with:
    - Punctuation removal
    - Number normalization
    """

    def __init__(
        self,
        lowercase: bool = True,
        strip_whitespace: bool = True,
        normalize_unicode: bool = True,
        remove_extra_spaces: bool = True,
        remove_punctuation: bool = False,
        normalize_numbers: bool = False,
    ):
        """
        Initialize strict normalizer.

        Args:
            lowercase: Convert to lowercase
            strip_whitespace: Strip whitespace
            normalize_unicode: Normalize unicode
            remove_extra_spaces: Remove multiple spaces
            remove_punctuation: Remove punctuation characters
            normalize_numbers: Convert digit sequences to placeholder
        """
        super().__init__(
            lowercase=lowercase,
            strip_whitespace=strip_whitespace,
            normalize_unicode=normalize_unicode,
            remove_extra_spaces=remove_extra_spaces,
        )
        self._remove_punctuation = remove_punctuation
        self._normalize_numbers = normalize_numbers

    def normalize(self, query: str) -> str:
        """
        Normalize with strict rules.

        Args:
            query: Raw query text

        Returns:
            Strictly normalized query text
        """
        # Apply base normalization first
        normalized = super().normalize(query)

        # Apply strict rules
        if self._remove_punctuation:
            normalized = self._remove_punct(normalized)

        if self._normalize_numbers:
            normalized = self._normalize_nums(normalized)

        # Clean up extra spaces that might result from punctuation removal
        if self._remove_extra_spaces and (
            self._remove_punctuation or self._normalize_numbers
        ):
            normalized = self._remove_multiple_spaces(normalized)
            normalized = normalized.strip()

        return normalized

    def _remove_punct(self, text: str) -> str:
        """
        Remove punctuation characters.

        Args:
            text: Text to process

        Returns:
            Text without punctuation
        """
        # Remove all punctuation except spaces
        return re.sub(r"[^\w\s]", "", text)

    def _normalize_nums(self, text: str) -> str:
        """
        Normalize number sequences.

        Replaces digit sequences with a placeholder.

        Args:
            text: Text to process

        Returns:
            Text with normalized numbers
        """
        # Replace sequences of digits with <NUM> placeholder
        return re.sub(r"\d+", "<NUM>", text)


# Convenience functions
def normalize_query(
    query: str,
    lowercase: bool = True,
    strip_whitespace: bool = True,
    normalize_unicode: bool = True,
    remove_extra_spaces: bool = True,
) -> str:
    """
    Normalize query (convenience function).

    Args:
        query: Query text
        lowercase: Convert to lowercase
        strip_whitespace: Strip whitespace
        normalize_unicode: Normalize unicode
        remove_extra_spaces: Remove multiple spaces

    Returns:
        Normalized query
    """
    normalizer = QueryNormalizer(
        lowercase=lowercase,
        strip_whitespace=strip_whitespace,
        normalize_unicode=normalize_unicode,
        remove_extra_spaces=remove_extra_spaces,
    )
    return normalizer.normalize(query)
