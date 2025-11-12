"""
LLM provider configuration models.

Sandi Metz Principles:
- Small classes with clear purpose
- Immutable configuration data
- Clear naming conventions
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ProviderConfig(BaseModel):
    """LLM provider configuration."""

    provider: Literal["openai", "anthropic"] = Field(..., description="LLM provider name")
    api_key: str = Field(..., description="API key for the provider")
    model: str = Field(..., description="Model name/identifier")
    max_tokens: int = Field(..., ge=1, le=100000, description="Maximum tokens per request")
    temperature: float = Field(..., ge=0.0, le=2.0, description="Sampling temperature")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Number of retry attempts")
    retry_delay_seconds: int = Field(
        default=1, ge=0, le=60, description="Delay between retries"
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key is not empty."""
        if not v or v.strip() == "":
            raise ValueError("API key cannot be empty")
        return v.strip()

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model name is not empty."""
        if not v or v.strip() == "":
            raise ValueError("Model name cannot be empty")
        return v.strip()

    @classmethod
    def openai(
        cls,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout_seconds: int = 30,
    ) -> "ProviderConfig":
        """Create OpenAI provider configuration."""
        return cls(
            provider="openai",
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )

    @classmethod
    def anthropic(
        cls,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout_seconds: int = 30,
    ) -> "ProviderConfig":
        """Create Anthropic provider configuration."""
        return cls(
            provider="anthropic",
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )

    def with_model(self, model: str) -> "ProviderConfig":
        """Create new config with different model."""
        return self.model_copy(update={"model": model})

    def with_temperature(self, temperature: float) -> "ProviderConfig":
        """Create new config with different temperature."""
        return self.model_copy(update={"temperature": temperature})

    def with_max_tokens(self, max_tokens: int) -> "ProviderConfig":
        """Create new config with different max tokens."""
        return self.model_copy(update={"max_tokens": max_tokens})

    @property
    def is_openai(self) -> bool:
        """Check if provider is OpenAI."""
        return self.provider == "openai"

    @property
    def is_anthropic(self) -> bool:
        """Check if provider is Anthropic."""
        return self.provider == "anthropic"


class ProviderRegistry(BaseModel):
    """Registry of available LLM provider configurations."""

    providers: Dict[str, ProviderConfig] = Field(
        default_factory=dict, description="Provider configurations by name"
    )
    default_provider: Optional[str] = Field(
        None, description="Default provider name to use"
    )

    def register(self, name: str, config: ProviderConfig) -> None:
        """
        Register a provider configuration.

        Args:
            name: Unique name for this provider config
            config: Provider configuration

        Raises:
            ValueError: If name is empty or config is invalid
        """
        if not name or name.strip() == "":
            raise ValueError("Provider name cannot be empty")

        # Create a mutable copy of providers dict
        new_providers = dict(self.providers)
        new_providers[name] = config

        # Update the model with new dict
        object.__setattr__(self, "providers", new_providers)

    def get(self, name: Optional[str] = None) -> Optional[ProviderConfig]:
        """
        Get provider configuration by name.

        Args:
            name: Provider name (uses default if None)

        Returns:
            Provider configuration or None if not found
        """
        provider_name = name or self.default_provider
        if provider_name is None:
            return None
        return self.providers.get(provider_name)

    def get_or_raise(self, name: Optional[str] = None) -> ProviderConfig:
        """
        Get provider configuration or raise error.

        Args:
            name: Provider name (uses default if None)

        Returns:
            Provider configuration

        Raises:
            ValueError: If provider not found
        """
        config = self.get(name)
        if config is None:
            provider_name = name or self.default_provider or "default"
            raise ValueError(f"Provider not found: {provider_name}")
        return config

    def set_default(self, name: str) -> None:
        """
        Set default provider.

        Args:
            name: Provider name to set as default

        Raises:
            ValueError: If provider not registered
        """
        if name not in self.providers:
            raise ValueError(f"Cannot set default: provider not registered: {name}")
        object.__setattr__(self, "default_provider", name)

    def list_providers(self) -> List[str]:
        """Get list of registered provider names."""
        return list(self.providers.keys())

    @property
    def has_providers(self) -> bool:
        """Check if any providers are registered."""
        return len(self.providers) > 0

    @property
    def provider_count(self) -> int:
        """Get number of registered providers."""
        return len(self.providers)
