"""Tests for LLM provider registry."""

import pytest

from app.exceptions import ConfigurationError
from app.llm.provider import BaseLLMProvider
from app.llm.registry import LLMProviderRegistry
from app.models.llm import LLMResponse
from app.models.query import QueryRequest


class MockProvider(BaseLLMProvider):
    """Mock provider for testing."""

    def __init__(self, name: str):
        """Initialize mock provider."""
        self._name = name

    async def complete(self, request: QueryRequest) -> LLMResponse:
        """Mock completion."""
        return LLMResponse(
            content="mock response",
            provider=self._name,
            model="mock-model",
            tokens_used=10,
            cost=0.01,
        )

    def get_name(self) -> str:
        """Get provider name."""
        return self._name


class TestLLMProviderRegistry:
    """Test LLM provider registry."""

    def test_register_provider(self):
        """Test registering a provider."""
        registry = LLMProviderRegistry()
        provider = MockProvider("test-provider")

        registry.register(provider)

        assert registry.has_provider("test-provider")
        assert "test-provider" in registry.list_providers()

    def test_register_duplicate_provider_raises_error(self):
        """Test registering duplicate provider raises error."""
        registry = LLMProviderRegistry()
        provider1 = MockProvider("test-provider")
        provider2 = MockProvider("test-provider")

        registry.register(provider1)

        with pytest.raises(ConfigurationError) as exc_info:
            registry.register(provider2)

        assert "already registered" in str(exc_info.value)

    def test_get_provider(self):
        """Test getting a provider."""
        registry = LLMProviderRegistry()
        provider = MockProvider("test-provider")
        registry.register(provider)

        retrieved = registry.get("test-provider")

        assert retrieved == provider
        assert retrieved.get_name() == "test-provider"

    def test_get_nonexistent_provider_raises_error(self):
        """Test getting nonexistent provider raises error."""
        registry = LLMProviderRegistry()

        with pytest.raises(ConfigurationError) as exc_info:
            registry.get("nonexistent")

        assert "not found" in str(exc_info.value)

    def test_get_provider_shows_available_providers(self):
        """Test error message shows available providers."""
        registry = LLMProviderRegistry()
        registry.register(MockProvider("provider1"))
        registry.register(MockProvider("provider2"))

        with pytest.raises(ConfigurationError) as exc_info:
            registry.get("nonexistent")

        error_msg = str(exc_info.value)
        assert "provider1" in error_msg
        assert "provider2" in error_msg

    def test_unregister_provider(self):
        """Test unregistering a provider."""
        registry = LLMProviderRegistry()
        provider = MockProvider("test-provider")
        registry.register(provider)

        registry.unregister("test-provider")

        assert not registry.has_provider("test-provider")
        assert "test-provider" not in registry.list_providers()

    def test_unregister_nonexistent_provider_raises_error(self):
        """Test unregistering nonexistent provider raises error."""
        registry = LLMProviderRegistry()

        with pytest.raises(ConfigurationError) as exc_info:
            registry.unregister("nonexistent")

        assert "not registered" in str(exc_info.value)

    def test_list_providers_empty(self):
        """Test listing providers when registry is empty."""
        registry = LLMProviderRegistry()

        providers = registry.list_providers()

        assert providers == []

    def test_list_providers_multiple(self):
        """Test listing multiple providers."""
        registry = LLMProviderRegistry()
        registry.register(MockProvider("provider1"))
        registry.register(MockProvider("provider2"))
        registry.register(MockProvider("provider3"))

        providers = registry.list_providers()

        assert len(providers) == 3
        assert "provider1" in providers
        assert "provider2" in providers
        assert "provider3" in providers

    def test_has_provider_true(self):
        """Test has_provider returns True for registered provider."""
        registry = LLMProviderRegistry()
        provider = MockProvider("test-provider")
        registry.register(provider)

        assert registry.has_provider("test-provider")

    def test_has_provider_false(self):
        """Test has_provider returns False for unregistered provider."""
        registry = LLMProviderRegistry()

        assert not registry.has_provider("test-provider")

    def test_clear_removes_all_providers(self):
        """Test clear removes all providers."""
        registry = LLMProviderRegistry()
        registry.register(MockProvider("provider1"))
        registry.register(MockProvider("provider2"))
        registry.register(MockProvider("provider3"))

        registry.clear()

        assert len(registry.list_providers()) == 0
        assert not registry.has_provider("provider1")
        assert not registry.has_provider("provider2")
        assert not registry.has_provider("provider3")

    def test_clear_empty_registry(self):
        """Test clear on empty registry doesn't raise error."""
        registry = LLMProviderRegistry()

        registry.clear()  # Should not raise error

        assert len(registry.list_providers()) == 0
