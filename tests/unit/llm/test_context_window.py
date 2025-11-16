"""Tests for LLM context window management."""

from unittest.mock import Mock

import pytest

from app.exceptions import LLMProviderError
from app.llm.context_window import ContextWindowConfig, ContextWindowManager


class TestContextWindowManager:
    """Test context window manager."""

    def test_validate_request_within_window(self):
        """Test validation passes for request within window."""
        manager = ContextWindowManager()

        # Should not raise for small text
        manager.validate_request(
            "Hello world", "gpt-3.5-turbo", max_completion_tokens=100
        )

    def test_validate_request_exceeds_window(self):
        """Test validation fails for request exceeding window."""
        mock_counter = Mock()
        mock_counter.count.return_value = 20000  # Exceed gpt-4 8k window

        manager = ContextWindowManager(token_counter=mock_counter)

        with pytest.raises(LLMProviderError) as exc_info:
            manager.validate_request("large text", "gpt-4", max_completion_tokens=4000)

        assert "exceeds context window" in str(exc_info.value).lower()
        assert "gpt-4" in str(exc_info.value)

    def test_get_max_completion_tokens(self):
        """Test calculating max completion tokens."""
        mock_counter = Mock()
        mock_counter.count.return_value = 1000

        manager = ContextWindowManager(token_counter=mock_counter)

        max_tokens = manager.get_max_completion_tokens("test text", "gpt-3.5-turbo")

        # gpt-3.5-turbo has 16385 window
        # Input: 1000, Reserve: 100 (default)
        # Max: 16385 - 1000 - 100 = 15285
        assert max_tokens == 15285

    def test_get_max_completion_tokens_with_custom_reserve(self):
        """Test max completion tokens with custom reserve."""
        mock_counter = Mock()
        mock_counter.count.return_value = 1000

        manager = ContextWindowManager(token_counter=mock_counter)

        max_tokens = manager.get_max_completion_tokens(
            "test text", "gpt-3.5-turbo", reserve_tokens=500
        )

        # Max: 16385 - 1000 - 500 = 14885
        assert max_tokens == 14885

    def test_get_max_completion_tokens_returns_zero_when_full(self):
        """Test max completion returns 0 when input fills window."""
        mock_counter = Mock()
        mock_counter.count.return_value = 20000  # More than gpt-4 window

        manager = ContextWindowManager(token_counter=mock_counter)

        max_tokens = manager.get_max_completion_tokens("large text", "gpt-4")

        assert max_tokens == 0

    def test_get_window_size_gpt4(self):
        """Test getting window size for GPT-4."""
        manager = ContextWindowManager()

        assert manager.get_window_size("gpt-4") == 8192
        assert manager.get_window_size("gpt-4-32k") == 32768
        assert manager.get_window_size("gpt-4-turbo") == 128000

    def test_get_window_size_gpt35(self):
        """Test getting window size for GPT-3.5."""
        manager = ContextWindowManager()

        assert manager.get_window_size("gpt-3.5-turbo") == 16385
        assert manager.get_window_size("gpt-3.5-turbo-16k") == 16385

    def test_get_window_size_gpt4o(self):
        """Test getting window size for GPT-4o."""
        manager = ContextWindowManager()

        assert manager.get_window_size("gpt-4o") == 128000
        assert manager.get_window_size("gpt-4o-mini") == 128000

    def test_get_window_size_claude(self):
        """Test getting window size for Claude models."""
        manager = ContextWindowManager()

        assert manager.get_window_size("claude-3-5-sonnet-20241022") == 200000
        assert manager.get_window_size("claude-3-opus-20240229") == 200000
        assert manager.get_window_size("claude-3-haiku-20240307") == 200000

    def test_get_window_size_unknown_model(self):
        """Test getting window size for unknown model returns default."""
        manager = ContextWindowManager()

        window_size = manager.get_window_size("unknown-model")

        assert window_size == 4096  # Default fallback

    def test_can_fit_returns_true_when_fits(self):
        """Test can_fit returns True when request fits."""
        manager = ContextWindowManager()

        assert manager.can_fit(
            "Hello world", "gpt-3.5-turbo", max_completion_tokens=100
        )

    def test_can_fit_returns_false_when_exceeds(self):
        """Test can_fit returns False when request exceeds window."""
        mock_counter = Mock()
        mock_counter.count.return_value = 20000

        manager = ContextWindowManager(token_counter=mock_counter)

        assert not manager.can_fit("large text", "gpt-4", max_completion_tokens=4000)

    def test_validate_request_error_includes_details(self):
        """Test validation error includes helpful details."""
        mock_counter = Mock()
        mock_counter.count.return_value = 10000

        manager = ContextWindowManager(token_counter=mock_counter)

        with pytest.raises(LLMProviderError) as exc_info:
            manager.validate_request("text", "gpt-4", max_completion_tokens=5000)

        error_msg = str(exc_info.value)
        assert "10000" in error_msg  # Input tokens
        assert "5000" in error_msg  # Completion tokens
        assert "15000" in error_msg  # Total
        assert "8192" in error_msg  # Window size

    def test_window_size_with_model_version(self):
        """Test window size detection with model versions."""
        manager = ContextWindowManager()

        # Should match prefix
        assert manager.get_window_size("gpt-3.5-turbo-0613") == 16385
        assert manager.get_window_size("gpt-4-0613") == 8192
        assert manager.get_window_size("gpt-4o-2024-05-13") == 128000

    def test_custom_config(self):
        """Test using custom configuration."""
        config = ContextWindowConfig()
        config.OPENAI_WINDOWS["custom-model"] = 50000

        manager = ContextWindowManager(config=config)

        assert manager.get_window_size("custom-model") == 50000

    def test_validate_with_exact_window_size(self):
        """Test validation at exact window size boundary."""
        mock_counter = Mock()
        mock_counter.count.return_value = 4192  # Just under window

        manager = ContextWindowManager(token_counter=mock_counter)

        # Should not raise (4192 + 4000 = 8192, exactly at window)
        manager.validate_request("text", "gpt-4", max_completion_tokens=4000)

    def test_validate_one_token_over_window(self):
        """Test validation fails when one token over window."""
        mock_counter = Mock()
        mock_counter.count.return_value = 4193  # One over

        manager = ContextWindowManager(token_counter=mock_counter)

        # Should raise (4193 + 4000 = 8193, exceeds 8192)
        with pytest.raises(LLMProviderError):
            manager.validate_request("text", "gpt-4", max_completion_tokens=4000)

    def test_get_max_completion_with_small_window(self):
        """Test max completion with very small remaining window."""
        mock_counter = Mock()
        mock_counter.count.return_value = 8100  # Near gpt-4 limit

        manager = ContextWindowManager(token_counter=mock_counter)

        max_tokens = manager.get_max_completion_tokens(
            "text", "gpt-4", reserve_tokens=10
        )

        # 8192 - 8100 - 10 = 82
        assert max_tokens == 82

    def test_model_name_case_sensitivity(self):
        """Test that model names are case-sensitive."""
        manager = ContextWindowManager()

        # Lowercase should not match
        assert manager.get_window_size("GPT-4") == 4096  # Default fallback

    def test_validate_with_zero_completion_tokens(self):
        """Test validation with zero completion tokens."""
        manager = ContextWindowManager()

        # Should not raise even with large input if completion is 0
        manager.validate_request("test", "gpt-4", max_completion_tokens=0)

    def test_can_fit_with_edge_cases(self):
        """Test can_fit with various edge cases."""
        manager = ContextWindowManager()

        # Empty text
        assert manager.can_fit("", "gpt-4", max_completion_tokens=4000)

        # Zero completion
        assert manager.can_fit("test", "gpt-4", max_completion_tokens=0)

    def test_large_claude_window(self):
        """Test Claude's large 200k context window."""
        mock_counter = Mock()
        mock_counter.count.return_value = 150000

        manager = ContextWindowManager(token_counter=mock_counter)

        # Should fit in Claude's 200k window
        assert manager.can_fit(
            "large text",
            "claude-3-5-sonnet-20241022",
            max_completion_tokens=40000,
        )

    def test_get_max_completion_for_claude(self):
        """Test max completion calculation for Claude models."""
        mock_counter = Mock()
        mock_counter.count.return_value = 50000

        manager = ContextWindowManager(token_counter=mock_counter)

        max_tokens = manager.get_max_completion_tokens(
            "text", "claude-3-5-sonnet-20241022", reserve_tokens=1000
        )

        # 200000 - 50000 - 1000 = 149000
        assert max_tokens == 149000
