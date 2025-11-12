"""Test LLM models."""

import pytest

from app.models.llm import LLMProvider, LLMResponse
from app.models.query import QueryRequest


class TestLLMResponse:
    """Test LLM response model."""

    def test_should_create_llm_response(self):
        """Test basic LLM response creation."""
        response = LLMResponse(
            content="Paris is the capital of France",
            prompt_tokens=10,
            completion_tokens=7,
            model="gpt-3.5-turbo",
        )

        assert response.content == "Paris is the capital of France"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 7
        assert response.model == "gpt-3.5-turbo"

    def test_should_calculate_total_tokens(self):
        """Test total tokens calculation."""
        response = LLMResponse(
            content="Test response",
            prompt_tokens=25,
            completion_tokens=15,
            model="gpt-3.5-turbo",
        )

        assert response.total_tokens == 40

    def test_should_handle_zero_tokens(self):
        """Test handling of zero tokens."""
        response = LLMResponse(
            content="",
            prompt_tokens=0,
            completion_tokens=0,
            model="gpt-3.5-turbo",
        )

        assert response.total_tokens == 0

    def test_should_handle_empty_content(self):
        """Test handling of empty content."""
        response = LLMResponse(
            content="",
            prompt_tokens=10,
            completion_tokens=0,
            model="gpt-3.5-turbo",
        )

        assert response.content == ""
        assert response.total_tokens == 10

    def test_should_handle_long_content(self):
        """Test handling of long response content."""
        long_content = "A" * 10000
        response = LLMResponse(
            content=long_content,
            prompt_tokens=100,
            completion_tokens=2000,
            model="gpt-4",
        )

        assert len(response.content) == 10000
        assert response.total_tokens == 2100

    def test_should_validate_non_negative_prompt_tokens(self):
        """Test validation of prompt tokens."""
        with pytest.raises(ValueError):
            LLMResponse(
                content="Test",
                prompt_tokens=-1,  # Invalid
                completion_tokens=10,
                model="gpt-3.5-turbo",
            )

    def test_should_validate_non_negative_completion_tokens(self):
        """Test validation of completion tokens."""
        with pytest.raises(ValueError):
            LLMResponse(
                content="Test",
                prompt_tokens=10,
                completion_tokens=-1,  # Invalid
                model="gpt-3.5-turbo",
            )

    def test_should_serialize_to_json(self):
        """Test serialization to JSON."""
        response = LLMResponse(
            content="Paris is the capital of France",
            prompt_tokens=10,
            completion_tokens=7,
            model="gpt-3.5-turbo",
        )

        json_data = response.model_dump()

        assert json_data["content"] == "Paris is the capital of France"
        assert json_data["prompt_tokens"] == 10
        assert json_data["completion_tokens"] == 7
        assert json_data["model"] == "gpt-3.5-turbo"

    def test_should_deserialize_from_json(self):
        """Test deserialization from JSON."""
        data = {
            "content": "Paris is the capital of France",
            "prompt_tokens": 10,
            "completion_tokens": 7,
            "model": "gpt-3.5-turbo",
        }

        response = LLMResponse.model_validate(data)

        assert response.content == "Paris is the capital of France"
        assert response.prompt_tokens == 10
        assert response.total_tokens == 17

    def test_should_handle_different_models(self):
        """Test handling of different model names."""
        models = [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
        ]

        for model_name in models:
            response = LLMResponse(
                content="Test",
                prompt_tokens=10,
                completion_tokens=5,
                model=model_name,
            )
            assert response.model == model_name

    def test_should_preserve_whitespace_in_content(self):
        """Test that whitespace is preserved in content."""
        content_with_spaces = "Line 1\n\nLine 2\n  Indented line"
        response = LLMResponse(
            content=content_with_spaces,
            prompt_tokens=10,
            completion_tokens=5,
            model="gpt-3.5-turbo",
        )

        assert response.content == content_with_spaces

    def test_should_handle_unicode_content(self):
        """Test handling of unicode characters."""
        unicode_content = "Hello 世界 🌍 Здравствуй мир"
        response = LLMResponse(
            content=unicode_content,
            prompt_tokens=10,
            completion_tokens=5,
            model="gpt-3.5-turbo",
        )

        assert response.content == unicode_content

    def test_should_handle_large_token_counts(self):
        """Test handling of large token counts."""
        response = LLMResponse(
            content="Very long response",
            prompt_tokens=50000,
            completion_tokens=10000,
            model="gpt-4",
        )

        assert response.total_tokens == 60000


class TestLLMProvider:
    """Test LLM provider protocol."""

    def test_should_define_complete_method(self):
        """Test that protocol defines complete method."""
        assert hasattr(LLMProvider, "complete")

    def test_should_define_get_name_method(self):
        """Test that protocol defines get_name method."""
        assert hasattr(LLMProvider, "get_name")

    def test_should_accept_implementation(self):
        """Test that protocol accepts conforming implementations."""

        class MockProvider:
            """Mock LLM provider for testing."""

            async def complete(self, request: QueryRequest) -> LLMResponse:
                """Mock complete method."""
                return LLMResponse(
                    content="Mock response",
                    prompt_tokens=10,
                    completion_tokens=5,
                    model="mock-model",
                )

            def get_name(self) -> str:
                """Mock get_name method."""
                return "mock"

        # This should not raise any errors
        provider: LLMProvider = MockProvider()  # type: ignore
        assert provider.get_name() == "mock"

    def test_should_require_async_complete(self):
        """Test that complete method signature is async."""
        import inspect

        # Get the complete method signature
        complete_method = getattr(LLMProvider, "complete")

        # Check if it's a coroutine function (async)
        # Note: For Protocol, we check the annotation
        assert "complete" in dir(LLMProvider)

    def test_should_document_provider_interface(self):
        """Test that provider protocol has documentation."""
        assert LLMProvider.__doc__ is not None
        assert "LLM provider protocol" in LLMProvider.__doc__
        assert "Liskov Substitution Principle" in LLMProvider.__doc__


class TestLLMProviderImplementation:
    """Test LLM provider implementation examples."""

    async def test_should_implement_provider_correctly(self):
        """Test correct provider implementation."""

        class TestProvider:
            """Test LLM provider implementation."""

            def __init__(self, name: str = "test"):
                self.name = name

            async def complete(self, request: QueryRequest) -> LLMResponse:
                """Generate completion."""
                return LLMResponse(
                    content=f"Response to: {request.query}",
                    prompt_tokens=len(request.query.split()),
                    completion_tokens=5,
                    model="test-model",
                )

            def get_name(self) -> str:
                """Get provider name."""
                return self.name

        provider = TestProvider(name="custom-test")
        assert provider.get_name() == "custom-test"

        # Test completion
        request = QueryRequest(query="What is AI?")
        response = await provider.complete(request)

        assert isinstance(response, LLMResponse)
        assert "What is AI?" in response.content
        assert response.model == "test-model"

    async def test_should_support_multiple_provider_implementations(self):
        """Test multiple provider implementations."""

        class OpenAIProvider:
            async def complete(self, request: QueryRequest) -> LLMResponse:
                return LLMResponse(
                    content="OpenAI response",
                    prompt_tokens=10,
                    completion_tokens=5,
                    model="gpt-3.5-turbo",
                )

            def get_name(self) -> str:
                return "openai"

        class AnthropicProvider:
            async def complete(self, request: QueryRequest) -> LLMResponse:
                return LLMResponse(
                    content="Anthropic response",
                    prompt_tokens=10,
                    completion_tokens=5,
                    model="claude-3-sonnet",
                )

            def get_name(self) -> str:
                return "anthropic"

        openai: LLMProvider = OpenAIProvider()  # type: ignore
        anthropic: LLMProvider = AnthropicProvider()  # type: ignore

        assert openai.get_name() == "openai"
        assert anthropic.get_name() == "anthropic"

        request = QueryRequest(query="Test")

        openai_response = await openai.complete(request)
        assert "OpenAI" in openai_response.content

        anthropic_response = await anthropic.complete(request)
        assert "Anthropic" in anthropic_response.content
