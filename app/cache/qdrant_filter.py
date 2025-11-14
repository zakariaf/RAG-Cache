"""
Qdrant filter builder for advanced queries.

Sandi Metz Principles:
- Single Responsibility: Filter construction
- Small methods: Each filter type isolated
- Clear naming: Descriptive method names
"""

from typing import Any, List, Optional

from qdrant_client.models import (
    Condition,
    FieldCondition,
    Filter,
    IsEmptyCondition,
    MatchAny,
    MatchValue,
    Range,
)

from app.models.qdrant_schema import QdrantSchema
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QdrantFilterBuilder:
    """
    Builder for Qdrant filter conditions.

    Provides fluent API for constructing complex filters.
    """

    def __init__(self):
        """Initialize filter builder."""
        self._must: List[Condition] = []
        self._should: List[Condition] = []
        self._must_not: List[Condition] = []

    def match_field(self, field: str, value: Any) -> "QdrantFilterBuilder":
        """
        Add exact match condition.

        Args:
            field: Field name to match
            value: Value to match

        Returns:
            Self for chaining
        """
        condition = FieldCondition(key=field, match=MatchValue(value=value))
        self._must.append(condition)
        return self

    def match_any(self, field: str, values: List[Any]) -> "QdrantFilterBuilder":
        """
        Add match any condition.

        Args:
            field: Field name to match
            values: List of acceptable values

        Returns:
            Self for chaining
        """
        condition = FieldCondition(key=field, match=MatchAny(any=values))
        self._must.append(condition)
        return self

    def range_field(
        self,
        field: str,
        gte: Optional[float] = None,
        gt: Optional[float] = None,
        lte: Optional[float] = None,
        lt: Optional[float] = None,
    ) -> "QdrantFilterBuilder":
        """
        Add range condition.

        Args:
            field: Field name for range
            gte: Greater than or equal to
            gt: Greater than
            lte: Less than or equal to
            lt: Less than

        Returns:
            Self for chaining
        """
        condition = FieldCondition(
            key=field, range=Range(gte=gte, gt=gt, lte=lte, lt=lt)
        )
        self._must.append(condition)
        return self

    def is_empty(self, field: str) -> "QdrantFilterBuilder":
        """
        Add is empty condition.

        Args:
            field: Field name to check

        Returns:
            Self for chaining
        """
        condition = IsEmptyCondition(is_empty=FieldCondition(key=field))
        self._must.append(condition)
        return self

    def is_not_empty(self, field: str) -> "QdrantFilterBuilder":
        """
        Add is not empty condition.

        Args:
            field: Field name to check

        Returns:
            Self for chaining
        """
        condition = IsEmptyCondition(is_empty=FieldCondition(key=field))
        self._must_not.append(condition)
        return self

    def with_provider(self, provider: str) -> "QdrantFilterBuilder":
        """
        Filter by LLM provider.

        Args:
            provider: Provider name

        Returns:
            Self for chaining
        """
        return self.match_field(QdrantSchema.FIELD_PROVIDER, provider)

    def with_model(self, model: str) -> "QdrantFilterBuilder":
        """
        Filter by LLM model.

        Args:
            model: Model name

        Returns:
            Self for chaining
        """
        return self.match_field(QdrantSchema.FIELD_MODEL, model)

    def with_query_hash(self, query_hash: str) -> "QdrantFilterBuilder":
        """
        Filter by query hash.

        Args:
            query_hash: Query hash value

        Returns:
            Self for chaining
        """
        return self.match_field(QdrantSchema.FIELD_QUERY_HASH, query_hash)

    def created_after(self, timestamp: float) -> "QdrantFilterBuilder":
        """
        Filter by creation time (after timestamp).

        Args:
            timestamp: Unix timestamp

        Returns:
            Self for chaining
        """
        return self.range_field(QdrantSchema.FIELD_CREATED_AT, gte=timestamp)

    def created_before(self, timestamp: float) -> "QdrantFilterBuilder":
        """
        Filter by creation time (before timestamp).

        Args:
            timestamp: Unix timestamp

        Returns:
            Self for chaining
        """
        return self.range_field(QdrantSchema.FIELD_CREATED_AT, lte=timestamp)

    def created_between(
        self, start_time: float, end_time: float
    ) -> "QdrantFilterBuilder":
        """
        Filter by creation time range.

        Args:
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            Self for chaining
        """
        return self.range_field(
            QdrantSchema.FIELD_CREATED_AT, gte=start_time, lte=end_time
        )

    def with_tags(self, tags: List[str]) -> "QdrantFilterBuilder":
        """
        Filter by tags.

        Args:
            tags: List of tags to match

        Returns:
            Self for chaining
        """
        return self.match_any(QdrantSchema.FIELD_TAGS, tags)

    def build(self) -> Optional[Filter]:
        """
        Build the filter.

        Returns:
            Filter object if conditions exist, None otherwise
        """
        if not (self._must or self._should or self._must_not):
            return None

        filter_obj = Filter(
            must=self._must if self._must else None,
            should=self._should if self._should else None,
            must_not=self._must_not if self._must_not else None,
        )

        logger.debug(
            "Filter built",
            must_count=len(self._must),
            should_count=len(self._should),
            must_not_count=len(self._must_not),
        )

        return filter_obj

    def reset(self) -> "QdrantFilterBuilder":
        """
        Reset builder to empty state.

        Returns:
            Self for chaining
        """
        self._must = []
        self._should = []
        self._must_not = []
        return self


def create_filter() -> QdrantFilterBuilder:
    """
    Create a new filter builder.

    Returns:
        QdrantFilterBuilder instance
    """
    return QdrantFilterBuilder()
