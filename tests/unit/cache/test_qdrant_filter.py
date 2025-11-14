"""Unit tests for Qdrant filter builder."""

from qdrant_client.models import (
    FieldCondition,
    IsEmptyCondition,
    MatchAny,
    MatchValue,
    PayloadField,
    Range,
)

from app.cache.qdrant_filter import QdrantFilterBuilder, create_filter
from app.models.qdrant_schema import QdrantSchema


class TestQdrantFilterBuilder:
    """Tests for QdrantFilterBuilder class."""

    def test_match_field(self):
        """Test match_field adds exact match condition."""
        builder = QdrantFilterBuilder()
        result = builder.match_field("provider", "openai")

        assert result is builder  # Test fluent API
        assert len(builder._must) == 1
        condition = builder._must[0]
        assert isinstance(condition, FieldCondition)
        assert condition.key == "provider"
        assert isinstance(condition.match, MatchValue)
        assert condition.match.value == "openai"

    def test_match_any(self):
        """Test match_any adds match any condition."""
        builder = QdrantFilterBuilder()
        values = ["openai", "anthropic", "cohere"]
        result = builder.match_any("provider", values)

        assert result is builder
        assert len(builder._must) == 1
        condition = builder._must[0]
        assert isinstance(condition, FieldCondition)
        assert isinstance(condition.match, MatchAny)
        assert condition.match.any == values

    def test_range_field_gte(self):
        """Test range_field with gte parameter."""
        builder = QdrantFilterBuilder()
        result = builder.range_field("created_at", gte=1000.0)

        assert result is builder
        assert len(builder._must) == 1
        condition = builder._must[0]
        assert isinstance(condition, FieldCondition)
        assert isinstance(condition.range, Range)
        assert condition.range.gte == 1000.0

    def test_range_field_between(self):
        """Test range_field with gte and lte parameters."""
        builder = QdrantFilterBuilder()
        result = builder.range_field("created_at", gte=1000.0, lte=2000.0)

        assert result is builder
        condition = builder._must[0]
        assert condition.range.gte == 1000.0
        assert condition.range.lte == 2000.0

    def test_is_empty(self):
        """Test is_empty adds is empty condition."""
        builder = QdrantFilterBuilder()
        result = builder.is_empty("tags")

        assert result is builder
        assert len(builder._must) == 1
        condition = builder._must[0]
        assert isinstance(condition, IsEmptyCondition)
        assert isinstance(condition.is_empty, PayloadField)
        assert condition.is_empty.key == "tags"

    def test_is_not_empty(self):
        """Test is_not_empty adds is not empty condition."""
        builder = QdrantFilterBuilder()
        result = builder.is_not_empty("tags")

        assert result is builder
        assert len(builder._must_not) == 1
        condition = builder._must_not[0]
        assert isinstance(condition, IsEmptyCondition)

    def test_with_provider(self):
        """Test with_provider convenience method."""
        builder = QdrantFilterBuilder()
        result = builder.with_provider("openai")

        assert result is builder
        assert len(builder._must) == 1
        condition = builder._must[0]
        assert condition.key == QdrantSchema.FIELD_PROVIDER
        assert condition.match.value == "openai"

    def test_with_model(self):
        """Test with_model convenience method."""
        builder = QdrantFilterBuilder()
        result = builder.with_model("gpt-4")

        assert result is builder
        condition = builder._must[0]
        assert condition.key == QdrantSchema.FIELD_MODEL
        assert condition.match.value == "gpt-4"

    def test_with_query_hash(self):
        """Test with_query_hash convenience method."""
        builder = QdrantFilterBuilder()
        result = builder.with_query_hash("abc123")

        assert result is builder
        condition = builder._must[0]
        assert condition.key == QdrantSchema.FIELD_QUERY_HASH
        assert condition.match.value == "abc123"

    def test_created_after(self):
        """Test created_after convenience method."""
        builder = QdrantFilterBuilder()
        timestamp = 1234567890.0
        result = builder.created_after(timestamp)

        assert result is builder
        condition = builder._must[0]
        assert condition.key == QdrantSchema.FIELD_CREATED_AT
        assert condition.range.gte == timestamp

    def test_created_before(self):
        """Test created_before convenience method."""
        builder = QdrantFilterBuilder()
        timestamp = 1234567890.0
        result = builder.created_before(timestamp)

        assert result is builder
        condition = builder._must[0]
        assert condition.range.lte == timestamp

    def test_created_between(self):
        """Test created_between convenience method."""
        builder = QdrantFilterBuilder()
        start = 1000.0
        end = 2000.0
        result = builder.created_between(start, end)

        assert result is builder
        condition = builder._must[0]
        assert condition.range.gte == start
        assert condition.range.lte == end

    def test_with_tags(self):
        """Test with_tags convenience method."""
        builder = QdrantFilterBuilder()
        tags = ["production", "cache"]
        result = builder.with_tags(tags)

        assert result is builder
        condition = builder._must[0]
        assert condition.key == QdrantSchema.FIELD_TAGS
        assert condition.match.any == tags

    def test_build_with_conditions(self):
        """Test build creates Filter with conditions."""
        builder = QdrantFilterBuilder()
        builder.match_field("provider", "openai")
        builder.match_field("model", "gpt-4")

        filter_obj = builder.build()

        assert filter_obj is not None
        assert filter_obj.must is not None
        assert len(filter_obj.must) == 2

    def test_build_empty(self):
        """Test build returns None when no conditions."""
        builder = QdrantFilterBuilder()
        filter_obj = builder.build()

        assert filter_obj is None

    def test_reset(self):
        """Test reset clears all conditions."""
        builder = QdrantFilterBuilder()
        builder.match_field("provider", "openai")
        builder.match_field("model", "gpt-4")

        result = builder.reset()

        assert result is builder
        assert len(builder._must) == 0
        assert len(builder._should) == 0
        assert len(builder._must_not) == 0

    def test_chaining(self):
        """Test method chaining works correctly."""
        builder = QdrantFilterBuilder()
        result = (
            builder.with_provider("openai").with_model("gpt-4").created_after(1000.0)
        )

        assert result is builder
        assert len(builder._must) == 3

    def test_create_filter_function(self):
        """Test create_filter factory function."""
        builder = create_filter()

        assert isinstance(builder, QdrantFilterBuilder)
        assert len(builder._must) == 0
