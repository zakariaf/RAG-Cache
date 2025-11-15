"""
Validators for LLM parameters.

Sandi Metz Principles:
- Single Responsibility: Each validator validates one thing
- Small methods: Each method < 10 lines
- Clear naming: Descriptive validator names
"""

from typing import List

from app.exceptions import ConfigurationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TemperatureValidator:
    """
    Validate temperature parameter for LLM requests.

    Temperature controls randomness in responses.
    Valid range: 0.0 to 2.0 (OpenAI), 0.0 to 1.0 (Anthropic)
    """

    MIN_TEMP = 0.0
    MAX_TEMP_OPENAI = 2.0
    MAX_TEMP_ANTHROPIC = 1.0

    @staticmethod
    def validate(temperature: float, provider: str = "openai") -> float:
        """
        Validate and return temperature value.

        Args:
            temperature: Temperature value
            provider: Provider name ("openai" or "anthropic")

        Returns:
            Validated temperature

        Raises:
            ConfigurationError: If temperature is invalid
        """
        max_temp = TemperatureValidator._get_max_temp(provider)

        if temperature < TemperatureValidator.MIN_TEMP:
            raise ConfigurationError(
                f"Temperature must be >= {TemperatureValidator.MIN_TEMP}, "
                f"got {temperature}"
            )

        if temperature > max_temp:
            raise ConfigurationError(
                f"Temperature must be <= {max_temp} for {provider}, "
                f"got {temperature}"
            )

        return temperature

    @staticmethod
    def _get_max_temp(provider: str) -> float:
        """Get maximum temperature for provider."""
        if provider.lower() == "anthropic":
            return TemperatureValidator.MAX_TEMP_ANTHROPIC
        return TemperatureValidator.MAX_TEMP_OPENAI


class ModelValidator:
    """
    Validate model name for LLM requests.

    Ensures model is supported by the selected provider.
    """

    OPENAI_MODELS: List[str] = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-4-32k",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ]

    ANTHROPIC_MODELS: List[str] = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    @staticmethod
    def validate(model: str, provider: str = "openai") -> str:
        """
        Validate model name for provider.

        Args:
            model: Model name
            provider: Provider name

        Returns:
            Validated model name

        Raises:
            ConfigurationError: If model is invalid for provider
        """
        valid_models = ModelValidator._get_valid_models(provider)

        # Check if model starts with any valid model prefix
        is_valid = any(model.startswith(valid) for valid in valid_models)

        if not is_valid:
            raise ConfigurationError(
                f"Model '{model}' not supported by {provider}. "
                f"Valid models: {', '.join(valid_models)}"
            )

        return model

    @staticmethod
    def _get_valid_models(provider: str) -> List[str]:
        """Get valid models for provider."""
        if provider.lower() == "anthropic":
            return ModelValidator.ANTHROPIC_MODELS
        return ModelValidator.OPENAI_MODELS

    @staticmethod
    def is_valid_model(model: str, provider: str = "openai") -> bool:
        """
        Check if model is valid without raising exception.

        Args:
            model: Model name
            provider: Provider name

        Returns:
            True if valid, False otherwise
        """
        try:
            ModelValidator.validate(model, provider)
            return True
        except ConfigurationError:
            return False
