"""
LLM provider registry.

Sandi Metz Principles:
- Single Responsibility: Manage provider instances
- Open/Closed: Easy to add/remove providers
- Dependency Inversion: Depends on provider interface
"""

from typing import Dict, List

from app.exceptions import ConfigurationError
from app.llm.provider import BaseLLMProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMProviderRegistry:
    """
    Registry for managing LLM provider instances.

    Maintains a collection of provider instances and provides
    access to them by name.
    """

    def __init__(self):
        """Initialize empty provider registry."""
        self._providers: Dict[str, BaseLLMProvider] = {}

    def register(self, provider: BaseLLMProvider) -> None:
        """
        Register a provider instance.

        Args:
            provider: Provider instance to register

        Raises:
            ConfigurationError: If provider with same name already registered
        """
        name = provider.get_name()
        if name in self._providers:
            raise ConfigurationError(f"Provider '{name}' is already registered")

        self._providers[name] = provider
        logger.info(f"Registered provider: {name}")

    def get(self, name: str) -> BaseLLMProvider:
        """
        Get provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance

        Raises:
            ConfigurationError: If provider not found
        """
        provider = self._providers.get(name)
        if not provider:
            available = ", ".join(self.list_providers())
            raise ConfigurationError(
                f"Provider '{name}' not found. " f"Available providers: {available}"
            )

        return provider

    def unregister(self, name: str) -> None:
        """
        Remove provider from registry.

        Args:
            name: Provider name to remove

        Raises:
            ConfigurationError: If provider not found
        """
        if name not in self._providers:
            raise ConfigurationError(f"Provider '{name}' not registered")

        del self._providers[name]
        logger.info(f"Unregistered provider: {name}")

    def list_providers(self) -> List[str]:
        """
        List all registered provider names.

        Returns:
            List of provider names
        """
        return list(self._providers.keys())

    def has_provider(self, name: str) -> bool:
        """
        Check if provider is registered.

        Args:
            name: Provider name

        Returns:
            True if provider is registered
        """
        return name in self._providers

    def clear(self) -> None:
        """Remove all providers from registry."""
        self._providers.clear()
        logger.info("Cleared all providers from registry")
