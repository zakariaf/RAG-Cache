"""
Query Normalizer Service.

Normalizes user queries for consistent processing and caching.

Sandi Metz Principles:
- Single Responsibility: Text normalization
- Small methods: Each normalization step isolated
- Composable: Steps can be enabled/disabled
"""

import re
import unicodedata
from typing import List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueryNormalizer:
    """
    Normalizes queries for consistent cache matching.

    Applies various text normalization techniques.
    """

    def __init__(
        self,
        lowercase: bool = True,
        strip_whitespace: bool = True,
        collapse_whitespace: bool = True,
        remove_punctuation: bool = False,
        unicode_normalize: bool = True,
    ):
        """
        Initialize normalizer with options.

        Args:
            lowercase: Convert to lowercase
            strip_whitespace: Strip leading/trailing whitespace
            collapse_whitespace: Collapse multiple spaces to one
            remove_punctuation: Remove punctuation marks
            unicode_normalize: Normalize unicode characters
        """
        self._lowercase = lowercase
        self._strip_whitespace = strip_whitespace
        self._collapse_whitespace = collapse_whitespace
        self._remove_punctuation = remove_punctuation
        self._unicode_normalize = unicode_normalize

    def normalize(self, query: str) -> str:
        """
        Normalize a query string.

        Args:
            query: Raw query string

        Returns:
            Normalized query string
        """
        if not query:
            return ""

        result = query

        if self._unicode_normalize:
            result = self._normalize_unicode(result)

        if self._strip_whitespace:
            result = result.strip()

        if self._lowercase:
            result = result.lower()

        if self._collapse_whitespace:
            result = self._collapse_spaces(result)

        if self._remove_punctuation:
            result = self._strip_punctuation(result)

        logger.debug("Query normalized", original=query[:50], normalized=result[:50])
        return result

    def normalize_batch(self, queries: List[str]) -> List[str]:
        """
        Normalize a batch of queries.

        Args:
            queries: List of raw queries

        Returns:
            List of normalized queries
        """
        return [self.normalize(q) for q in queries]

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        """
        Normalize unicode to NFC form.

        Args:
            text: Input text

        Returns:
            Unicode normalized text
        """
        return unicodedata.normalize("NFC", text)

    @staticmethod
    def _collapse_spaces(text: str) -> str:
        """
        Collapse multiple spaces to single space.

        Args:
            text: Input text

        Returns:
            Text with collapsed spaces
        """
        return re.sub(r"\s+", " ", text)

    @staticmethod
    def _strip_punctuation(text: str) -> str:
        """
        Remove punctuation from text.

        Args:
            text: Input text

        Returns:
            Text without punctuation
        """
        return re.sub(r"[^\w\s]", "", text)

    def get_config(self) -> dict:
        """
        Get normalizer configuration.

        Returns:
            Configuration dict
        """
        return {
            "lowercase": self._lowercase,
            "strip_whitespace": self._strip_whitespace,
            "collapse_whitespace": self._collapse_whitespace,
            "remove_punctuation": self._remove_punctuation,
            "unicode_normalize": self._unicode_normalize,
        }


# Default normalizer instance
default_normalizer = QueryNormalizer()


def normalize_query(query: str) -> str:
    """
    Normalize a query using default settings.

    Args:
        query: Raw query string

    Returns:
        Normalized query string
    """
    return default_normalizer.normalize(query)

