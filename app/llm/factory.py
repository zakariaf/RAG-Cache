"""
LLM provider factory.

Sandi Metz Principles:
- Single Responsibility: Create provider instances
- Open/Closed: Easy to add new providers
- Dependency Inversion: Returns interface, not concrete class
"""

from app.config import config
from app.exceptions import ConfigurationError
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import BaseLLMProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.

    Creates appropriate provider based on provider name.
    """

    @staticmethod
    def create(provider_name: str | None = None) -> BaseLLMProvider:
        """
        Create LLM provider instance.

        Args:
            provider_name: Provider name ("openai" or "anthropic")
                          If None, uses default from config

        Returns:
            LLM provider instance

        Raises:
            ConfigurationError: If provider name is invalid or API key missing
        """
        name = provider_name or config.default_llm_provider
        creator = LLMProviderFactory._get_creator(name)

        try:
            provider = creator()
            logger.info(f"Created {name} provider")
            return provider
        except Exception as e:
            error_msg = f"Failed to create {name} provider: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e

    @staticmethod
    def _get_creator(provider_name: str):
        """
        Get provider creator function.

        Args:
            provider_name: Provider name

        Returns:
            Creator function

        Raises:
            ConfigurationError: If provider name is invalid
        """
        creators = {
            "openai": LLMProviderFactory._create_openai,
            "anthropic": LLMProviderFactory._create_anthropic,
        }

        creator = creators.get(provider_name.lower())
        if not creator:
            valid_providers = ", ".join(creators.keys())
            raise ConfigurationError(
                f"Invalid provider: {provider_name}. "
                f"Valid providers: {valid_providers}"
            )

        return creator

    @staticmethod
    def _create_openai() -> OpenAIProvider:
        """
        Create OpenAI provider.

        Returns:
            OpenAI provider instance

        Raises:
            ConfigurationError: If API key is missing
        """
        api_key = config.openai_api_key
        if not api_key:
            raise ConfigurationError("OpenAI API key not configured")

        return OpenAIProvider(api_key=api_key)

    @staticmethod
    def _create_anthropic() -> AnthropicProvider:
        """
        Create Anthropic provider.

        Returns:
            Anthropic provider instance

        Raises:
            ConfigurationError: If API key is missing
        """
        api_key = config.anthropic_api_key
        if not api_key:
            raise ConfigurationError("Anthropic API key not configured")

        return AnthropicProvider(api_key=api_key)
