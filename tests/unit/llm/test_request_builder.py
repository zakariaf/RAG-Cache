"""Tests for LLM request builder."""

from app.llm.request_builder import LLMRequestBuilder
from app.models.query import QueryRequest


class TestLLMRequestBuilder:
    """Test LLM request builder."""

    def test_build_messages(self):
        """Test building messages array."""
        request = QueryRequest(query="Hello world")
        builder = LLMRequestBuilder(request)

        messages = builder.build_messages()

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello world"

    def test_get_model_with_explicit_model(self):
        """Test get_model with explicit model in request."""
        request = QueryRequest(query="test", model="gpt-4")
        builder = LLMRequestBuilder(request)

        model = builder.get_model()

        assert model == "gpt-4"

    def test_get_model_with_provider_default(self):
        """Test get_model with provider default."""
        request = QueryRequest(query="test")
        builder = LLMRequestBuilder(request)

        model = builder.get_model(provider_default="claude-3-opus")

        assert model == "claude-3-opus"

    def test_get_model_with_config_default(self):
        """Test get_model falls back to config default."""
        request = QueryRequest(query="test")
        builder = LLMRequestBuilder(request)

        model = builder.get_model()

        assert model is not None  # Uses config default

    def test_get_max_tokens_with_explicit_value(self):
        """Test get_max_tokens with explicit value."""
        request = QueryRequest(query="test", max_tokens=500)
        builder = LLMRequestBuilder(request)

        max_tokens = builder.get_max_tokens()

        assert max_tokens == 500

    def test_get_max_tokens_with_config_default(self):
        """Test get_max_tokens falls back to config."""
        request = QueryRequest(query="test")
        builder = LLMRequestBuilder(request)

        max_tokens = builder.get_max_tokens()

        assert max_tokens > 0  # Uses config default

    def test_get_temperature_with_explicit_value(self):
        """Test get_temperature with explicit value."""
        request = QueryRequest(query="test", temperature=0.7)
        builder = LLMRequestBuilder(request)

        temperature = builder.get_temperature()

        assert temperature == 0.7

    def test_get_temperature_with_zero(self):
        """Test get_temperature handles zero correctly."""
        request = QueryRequest(query="test", temperature=0.0)
        builder = LLMRequestBuilder(request)

        temperature = builder.get_temperature()

        assert temperature == 0.0

    def test_get_temperature_with_config_default(self):
        """Test get_temperature falls back to config."""
        request = QueryRequest(query="test")
        builder = LLMRequestBuilder(request)

        temperature = builder.get_temperature()

        assert temperature >= 0.0  # Uses config default

    def test_build_openai_params(self):
        """Test building OpenAI API parameters."""
        request = QueryRequest(
            query="Hello", model="gpt-4", max_tokens=100, temperature=0.5
        )
        builder = LLMRequestBuilder(request)

        params = builder.build_openai_params()

        assert params["model"] == "gpt-4"
        assert params["max_tokens"] == 100
        assert params["temperature"] == 0.5
        assert len(params["messages"]) == 1
        assert params["messages"][0]["content"] == "Hello"

    def test_build_openai_params_with_overrides(self):
        """Test OpenAI params with overrides."""
        request = QueryRequest(query="test")
        builder = LLMRequestBuilder(request)

        params = builder.build_openai_params(stream=True, n=2)

        assert params["stream"] is True
        assert params["n"] == 2
        assert "model" in params
        assert "messages" in params

    def test_build_anthropic_params(self):
        """Test building Anthropic API parameters."""
        request = QueryRequest(
            query="Hello", model="claude-3-opus", max_tokens=100, temperature=0.5
        )
        builder = LLMRequestBuilder(request)

        params = builder.build_anthropic_params()

        assert params["model"] == "claude-3-opus"
        assert params["max_tokens"] == 100
        assert params["temperature"] == 0.5
        assert len(params["messages"]) == 1
        assert params["messages"][0]["content"] == "Hello"

    def test_build_anthropic_params_with_default_model(self):
        """Test Anthropic params use provider default when no model specified."""
        request = QueryRequest(query="test")
        builder = LLMRequestBuilder(request)

        params = builder.build_anthropic_params()

        # Should use Anthropic-specific default
        assert "claude" in params["model"].lower()

    def test_build_anthropic_params_with_overrides(self):
        """Test Anthropic params with overrides."""
        request = QueryRequest(query="test")
        builder = LLMRequestBuilder(request)

        params = builder.build_anthropic_params(stream=True, top_k=10)

        assert params["stream"] is True
        assert params["top_k"] == 10
        assert "model" in params
        assert "messages" in params

    def test_get_query_text(self):
        """Test getting query text."""
        request = QueryRequest(query="What is AI?")
        builder = LLMRequestBuilder(request)

        query_text = builder.get_query_text()

        assert query_text == "What is AI?"

    def test_should_use_cache_true(self):
        """Test should_use_cache when enabled."""
        request = QueryRequest(query="test", use_cache=True)
        builder = LLMRequestBuilder(request)

        assert builder.should_use_cache() is True

    def test_should_use_cache_false(self):
        """Test should_use_cache when disabled."""
        request = QueryRequest(query="test", use_cache=False)
        builder = LLMRequestBuilder(request)

        assert builder.should_use_cache() is False

    def test_should_use_semantic_cache_true(self):
        """Test should_use_semantic_cache when enabled."""
        request = QueryRequest(query="test", use_semantic_cache=True)
        builder = LLMRequestBuilder(request)

        assert builder.should_use_semantic_cache() is True

    def test_should_use_semantic_cache_false(self):
        """Test should_use_semantic_cache when disabled."""
        request = QueryRequest(query="test", use_semantic_cache=False)
        builder = LLMRequestBuilder(request)

        assert builder.should_use_semantic_cache() is False

    def test_messages_format_consistent(self):
        """Test that messages format is consistent across builds."""
        request = QueryRequest(query="Consistent test")
        builder = LLMRequestBuilder(request)

        messages1 = builder.build_messages()
        messages2 = builder.build_messages()

        assert messages1 == messages2
        assert messages1[0]["role"] == "user"
        assert messages1[0]["content"] == "Consistent test"
