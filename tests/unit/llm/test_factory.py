"""
Tests for LLM provider factory.
"""

import pytest
from unittest.mock import patch

from app.exceptions import ConfigurationError
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.factory import LLMProviderFactory
from app.llm.openai_provider import OpenAIProvider


class TestLLMProviderFactory:
    """Test LLM provider factory functionality."""

    @patch("app.llm.factory.config")
    def test_create_openai_provider(self, mock_config) -> None:
        """Test creating OpenAI provider."""
        mock_config.openai_api_key = "test-openai-key"
        mock_config.default_llm_provider = "openai"

        provider = LLMProviderFactory.create("openai")

        assert isinstance(provider, OpenAIProvider)
        assert provider.get_name() == "openai"

    @patch("app.llm.factory.config")
    def test_create_anthropic_provider(self, mock_config) -> None:
        """Test creating Anthropic provider."""
        mock_config.anthropic_api_key = "test-anthropic-key"
        mock_config.default_llm_provider = "anthropic"

        provider = LLMProviderFactory.create("anthropic")

        assert isinstance(provider, AnthropicProvider)
        assert provider.get_name() == "anthropic"

    @patch("app.llm.factory.config")
    def test_create_default_provider(self, mock_config) -> None:
        """Test creating provider with default from config."""
        mock_config.openai_api_key = "test-openai-key"
        mock_config.default_llm_provider = "openai"

        provider = LLMProviderFactory.create()

        assert isinstance(provider, OpenAIProvider)

    @patch("app.llm.factory.config")
    def test_create_case_insensitive(self, mock_config) -> None:
        """Test provider name is case insensitive."""
        mock_config.openai_api_key = "test-openai-key"

        provider = LLMProviderFactory.create("OpenAI")

        assert isinstance(provider, OpenAIProvider)

    def test_create_invalid_provider(self) -> None:
        """Test error on invalid provider name."""
        with pytest.raises(ConfigurationError) as exc_info:
            LLMProviderFactory.create("invalid_provider")

        assert "Invalid provider" in str(exc_info.value)
        assert "invalid_provider" in str(exc_info.value)

    @patch("app.llm.factory.config")
    def test_create_openai_without_api_key(self, mock_config) -> None:
        """Test error when OpenAI API key is missing."""
        mock_config.openai_api_key = ""

        with pytest.raises(ConfigurationError) as exc_info:
            LLMProviderFactory.create("openai")

        assert "OpenAI API key not configured" in str(exc_info.value)

    @patch("app.llm.factory.config")
    def test_create_anthropic_without_api_key(self, mock_config) -> None:
        """Test error when Anthropic API key is missing."""
        mock_config.anthropic_api_key = ""

        with pytest.raises(ConfigurationError) as exc_info:
            LLMProviderFactory.create("anthropic")

        assert "Anthropic API key not configured" in str(exc_info.value)

    @patch("app.llm.factory.config")
    def test_get_creator_valid_providers(self, mock_config) -> None:
        """Test _get_creator returns valid creator functions."""
        mock_config.openai_api_key = "test-key"

        openai_creator = LLMProviderFactory._get_creator("openai")
        assert openai_creator is not None
        assert callable(openai_creator)

        mock_config.anthropic_api_key = "test-key"
        anthropic_creator = LLMProviderFactory._get_creator("anthropic")
        assert anthropic_creator is not None
        assert callable(anthropic_creator)
