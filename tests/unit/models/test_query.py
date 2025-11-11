"""Test query request model."""

import pytest
from pydantic import ValidationError

from app.models.query import QueryRequest


class TestQueryRequest:
    """Test query request validation."""

    def test_should_validate_valid_query(self):
        """Test valid query passes validation."""
        request = QueryRequest(query="What is AI?")
        assert request.query == "What is AI?"
        assert request.use_cache is True

    def test_should_reject_empty_query(self):
        """Test empty query fails validation."""
        with pytest.raises(ValidationError):
            QueryRequest(query="")

    def test_should_strip_whitespace(self):
        """Test query whitespace is stripped."""
        request = QueryRequest(query="  test query  ")
        assert request.query == "test query"

    def test_should_use_default_values(self):
        """Test default values."""
        request = QueryRequest(query="test")
        assert request.use_cache is True
        assert request.use_semantic_cache is True
        assert request.provider is None

    def test_should_validate_temperature_range(self):
        """Test temperature validation."""
        # Valid temperature
        request = QueryRequest(query="test", temperature=0.7)
        assert request.temperature == 0.7

        # Invalid temperature (too high)
        with pytest.raises(ValidationError):
            QueryRequest(query="test", temperature=2.5)

    def test_should_get_defaults(self):
        """Test default getters."""
        request = QueryRequest(query="test")
        assert request.get_provider("openai") == "openai"
        assert request.get_model("gpt-3.5-turbo") == "gpt-3.5-turbo"
        assert request.get_max_tokens(1000) == 1000
        assert request.get_temperature(0.7) == 0.7
