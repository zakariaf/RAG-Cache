"""
Tests for token counter.
"""

import pytest

from app.llm.token_counter import TokenCounter


class TestTokenCounter:
    """Test token counter functionality."""

    @pytest.fixture
    def counter(self) -> TokenCounter:
        """Create token counter instance."""
        return TokenCounter()

    def test_count_openai_model(self, counter: TokenCounter) -> None:
        """Test counting tokens for OpenAI models."""
        text = "Hello, how are you doing today?"
        count = counter.count(text, model="gpt-3.5-turbo")

        # Should return reasonable count (not exact due to tiktoken)
        assert count > 0
        assert count < len(text)  # tokens < characters

    def test_count_gpt4_model(self, counter: TokenCounter) -> None:
        """Test counting tokens for GPT-4 models."""
        text = "The quick brown fox jumps over the lazy dog"
        count = counter.count(text, model="gpt-4")

        assert count > 0
        assert count < len(text.split()) * 2  # reasonable upper bound

    def test_count_anthropic_model(self, counter: TokenCounter) -> None:
        """Test counting tokens for Anthropic models."""
        text = "Hello world! " * 10  # 130 chars
        count = counter.count(text, model="claude-3-5-sonnet-20241022")

        # Anthropic uses ~4 chars per token
        expected = len(text) // 4
        assert count == expected

    def test_is_openai_model(self, counter: TokenCounter) -> None:
        """Test OpenAI model detection."""
        assert counter._is_openai_model("gpt-3.5-turbo")
        assert counter._is_openai_model("gpt-4")
        assert counter._is_openai_model("gpt-4-turbo")
        assert not counter._is_openai_model("claude-3-5-sonnet")

    def test_count_empty_string(self, counter: TokenCounter) -> None:
        """Test counting empty string."""
        count = counter.count("", model="gpt-3.5-turbo")
        assert count == 0

    def test_count_long_text(self, counter: TokenCounter) -> None:
        """Test counting long text."""
        text = "word " * 1000  # 5000 characters
        count = counter.count(text, model="gpt-3.5-turbo")

        # Should handle long text
        assert count > 100
        assert count < 5000

    def test_count_with_special_characters(self, counter: TokenCounter) -> None:
        """Test counting text with special characters."""
        text = "Hello! @#$%^&*() 你好 مرحبا"
        count = counter.count(text, model="gpt-3.5-turbo")

        assert count > 0

    def test_get_encoding_name(self, counter: TokenCounter) -> None:
        """Test getting encoding name for models."""
        assert counter._get_encoding_name("gpt-3.5-turbo") == "cl100k_base"
        assert counter._get_encoding_name("gpt-4") == "cl100k_base"
        assert counter._get_encoding_name("unknown-model") == "cl100k_base"

    def test_approximate_count(self, counter: TokenCounter) -> None:
        """Test approximate counting fallback."""
        text = "one two three four five"
        count = counter._approximate_count(text)

        # 5 words / 0.75 = ~6.67 = 6 tokens
        assert count > 0
        assert count < 10

    def test_count_anthropic_tokens(self, counter: TokenCounter) -> None:
        """Test Anthropic token counting."""
        text = "a" * 100  # 100 characters
        count = counter._count_anthropic_tokens(text)

        # 100 / 4 = 25 tokens
        assert count == 25

    def test_count_single_word(self, counter: TokenCounter) -> None:
        """Test counting single word."""
        text = "hello"
        count = counter.count(text, model="gpt-3.5-turbo")

        assert count >= 1
        assert count <= 2  # Should be 1, but allow 2 for safety
