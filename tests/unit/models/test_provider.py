"""Test provider configuration models."""

import pytest

from app.models.provider import ProviderConfig, ProviderRegistry


class TestProviderConfig:
    """Test provider configuration model."""

    def test_should_create_provider_config(self):
        """Test basic provider config creation."""
        config = ProviderConfig(
            provider="openai",
            api_key="sk-test123",
            model="gpt-3.5-turbo",
            max_tokens=1000,
            temperature=0.7,
        )

        assert config.provider == "openai"
        assert config.api_key == "sk-test123"
        assert config.model == "gpt-3.5-turbo"
        assert config.max_tokens == 1000
        assert config.temperature == 0.7
        assert config.timeout_seconds == 30  # default
        assert config.retry_attempts == 3  # default

    def test_should_create_openai_config(self):
        """Test OpenAI factory method."""
        config = ProviderConfig.openai(api_key="sk-test123")

        assert config.provider == "openai"
        assert config.api_key == "sk-test123"
        assert config.model == "gpt-3.5-turbo"  # default
        assert config.max_tokens == 1000
        assert config.temperature == 0.7

    def test_should_create_openai_config_with_custom_params(self):
        """Test OpenAI factory with custom parameters."""
        config = ProviderConfig.openai(
            api_key="sk-test123",
            model="gpt-4",
            max_tokens=2000,
            temperature=0.9,
            timeout_seconds=60,
        )

        assert config.model == "gpt-4"
        assert config.max_tokens == 2000
        assert config.temperature == 0.9
        assert config.timeout_seconds == 60

    def test_should_create_anthropic_config(self):
        """Test Anthropic factory method."""
        config = ProviderConfig.anthropic(api_key="sk-ant-test123")

        assert config.provider == "anthropic"
        assert config.api_key == "sk-ant-test123"
        assert config.model == "claude-3-sonnet-20240229"  # default
        assert config.max_tokens == 1000
        assert config.temperature == 0.7

    def test_should_create_anthropic_config_with_custom_params(self):
        """Test Anthropic factory with custom parameters."""
        config = ProviderConfig.anthropic(
            api_key="sk-ant-test123",
            model="claude-3-opus-20240229",
            max_tokens=4000,
            temperature=0.5,
            timeout_seconds=90,
        )

        assert config.model == "claude-3-opus-20240229"
        assert config.max_tokens == 4000
        assert config.temperature == 0.5
        assert config.timeout_seconds == 90

    def test_should_validate_empty_api_key(self):
        """Test API key validation."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            ProviderConfig(
                provider="openai",
                api_key="",
                model="gpt-3.5-turbo",
                max_tokens=1000,
                temperature=0.7,
            )

        with pytest.raises(ValueError, match="API key cannot be empty"):
            ProviderConfig(
                provider="openai",
                api_key="   ",  # whitespace only
                model="gpt-3.5-turbo",
                max_tokens=1000,
                temperature=0.7,
            )

    def test_should_validate_empty_model(self):
        """Test model name validation."""
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            ProviderConfig(
                provider="openai",
                api_key="sk-test123",
                model="",
                max_tokens=1000,
                temperature=0.7,
            )

    def test_should_validate_max_tokens_range(self):
        """Test max tokens validation."""
        # Too low
        with pytest.raises(ValueError):
            ProviderConfig(
                provider="openai",
                api_key="sk-test123",
                model="gpt-3.5-turbo",
                max_tokens=0,
                temperature=0.7,
            )

        # Too high
        with pytest.raises(ValueError):
            ProviderConfig(
                provider="openai",
                api_key="sk-test123",
                model="gpt-3.5-turbo",
                max_tokens=100001,
                temperature=0.7,
            )

    def test_should_validate_temperature_range(self):
        """Test temperature validation."""
        # Too low
        with pytest.raises(ValueError):
            ProviderConfig(
                provider="openai",
                api_key="sk-test123",
                model="gpt-3.5-turbo",
                max_tokens=1000,
                temperature=-0.1,
            )

        # Too high
        with pytest.raises(ValueError):
            ProviderConfig(
                provider="openai",
                api_key="sk-test123",
                model="gpt-3.5-turbo",
                max_tokens=1000,
                temperature=2.1,
            )

    def test_should_create_config_with_different_model(self):
        """Test creating config copy with different model."""
        config = ProviderConfig.openai(api_key="sk-test123")
        new_config = config.with_model("gpt-4")

        assert new_config.model == "gpt-4"
        assert new_config.api_key == config.api_key
        assert new_config.provider == config.provider
        # Original unchanged
        assert config.model == "gpt-3.5-turbo"

    def test_should_create_config_with_different_temperature(self):
        """Test creating config copy with different temperature."""
        config = ProviderConfig.openai(api_key="sk-test123")
        new_config = config.with_temperature(0.9)

        assert new_config.temperature == 0.9
        assert config.temperature == 0.7  # Original unchanged

    def test_should_create_config_with_different_max_tokens(self):
        """Test creating config copy with different max tokens."""
        config = ProviderConfig.openai(api_key="sk-test123")
        new_config = config.with_max_tokens(2000)

        assert new_config.max_tokens == 2000
        assert config.max_tokens == 1000  # Original unchanged

    def test_should_identify_openai_provider(self):
        """Test OpenAI provider check."""
        config = ProviderConfig.openai(api_key="sk-test123")
        assert config.is_openai is True
        assert config.is_anthropic is False

    def test_should_identify_anthropic_provider(self):
        """Test Anthropic provider check."""
        config = ProviderConfig.anthropic(api_key="sk-ant-test123")
        assert config.is_anthropic is True
        assert config.is_openai is False


class TestProviderRegistry:
    """Test provider registry model."""

    def test_should_create_empty_registry(self):
        """Test empty registry creation."""
        registry = ProviderRegistry()

        assert registry.has_providers is False
        assert registry.provider_count == 0
        assert registry.default_provider is None

    def test_should_register_provider(self):
        """Test registering a provider."""
        registry = ProviderRegistry()
        config = ProviderConfig.openai(api_key="sk-test123")

        registry.register("main-openai", config)

        assert registry.has_providers is True
        assert registry.provider_count == 1
        assert "main-openai" in registry.list_providers()

    def test_should_register_multiple_providers(self):
        """Test registering multiple providers."""
        registry = ProviderRegistry()
        openai_config = ProviderConfig.openai(api_key="sk-test123")
        anthropic_config = ProviderConfig.anthropic(api_key="sk-ant-test123")

        registry.register("openai-main", openai_config)
        registry.register("anthropic-main", anthropic_config)

        assert registry.provider_count == 2
        assert "openai-main" in registry.list_providers()
        assert "anthropic-main" in registry.list_providers()

    def test_should_reject_empty_provider_name(self):
        """Test validation of empty provider name."""
        registry = ProviderRegistry()
        config = ProviderConfig.openai(api_key="sk-test123")

        with pytest.raises(ValueError, match="Provider name cannot be empty"):
            registry.register("", config)

    def test_should_get_provider_by_name(self):
        """Test retrieving provider by name."""
        registry = ProviderRegistry()
        config = ProviderConfig.openai(api_key="sk-test123")
        registry.register("main", config)

        retrieved = registry.get("main")

        assert retrieved is not None
        assert retrieved.provider == "openai"
        assert retrieved.api_key == "sk-test123"

    def test_should_return_none_for_unknown_provider(self):
        """Test getting unknown provider."""
        registry = ProviderRegistry()

        result = registry.get("unknown")

        assert result is None

    def test_should_get_or_raise_provider(self):
        """Test get_or_raise method."""
        registry = ProviderRegistry()
        config = ProviderConfig.openai(api_key="sk-test123")
        registry.register("main", config)

        # Should succeed
        retrieved = registry.get_or_raise("main")
        assert retrieved is not None

        # Should raise
        with pytest.raises(ValueError, match="Provider not found: unknown"):
            registry.get_or_raise("unknown")

    def test_should_set_default_provider(self):
        """Test setting default provider."""
        registry = ProviderRegistry()
        config = ProviderConfig.openai(api_key="sk-test123")
        registry.register("main", config)

        registry.set_default("main")

        assert registry.default_provider == "main"

    def test_should_reject_setting_unregistered_default(self):
        """Test validation when setting unregistered provider as default."""
        registry = ProviderRegistry()

        with pytest.raises(
            ValueError, match="Cannot set default: provider not registered"
        ):
            registry.set_default("unknown")

    def test_should_get_default_provider(self):
        """Test getting default provider without name."""
        registry = ProviderRegistry()
        config = ProviderConfig.openai(api_key="sk-test123")
        registry.register("main", config)
        registry.set_default("main")

        # Get without specifying name
        retrieved = registry.get()

        assert retrieved is not None
        assert retrieved.provider == "openai"

    def test_should_return_none_when_no_default_set(self):
        """Test getting provider when no default is set."""
        registry = ProviderRegistry()
        config = ProviderConfig.openai(api_key="sk-test123")
        registry.register("main", config)

        # No default set, no name provided
        result = registry.get()

        assert result is None

    def test_should_list_all_providers(self):
        """Test listing all provider names."""
        registry = ProviderRegistry()
        registry.register("openai-1", ProviderConfig.openai(api_key="sk-1"))
        registry.register("openai-2", ProviderConfig.openai(api_key="sk-2"))
        registry.register("anthropic-1", ProviderConfig.anthropic(api_key="sk-ant-1"))

        providers = registry.list_providers()

        assert len(providers) == 3
        assert "openai-1" in providers
        assert "openai-2" in providers
        assert "anthropic-1" in providers

    def test_should_override_existing_provider(self):
        """Test overriding an existing provider registration."""
        registry = ProviderRegistry()
        config1 = ProviderConfig.openai(api_key="sk-old", model="gpt-3.5-turbo")
        config2 = ProviderConfig.openai(api_key="sk-new", model="gpt-4")

        registry.register("main", config1)
        registry.register("main", config2)  # Override

        retrieved = registry.get("main")
        assert retrieved is not None
        assert retrieved.api_key == "sk-new"
        assert retrieved.model == "gpt-4"
        assert registry.provider_count == 1  # Still only 1 provider
