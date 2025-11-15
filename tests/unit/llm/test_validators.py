"""
Tests for LLM validators.
"""

import pytest

from app.exceptions import ConfigurationError
from app.llm.validators import TemperatureValidator, ModelValidator


class TestTemperatureValidator:
    """Test temperature validator."""

    def test_validate_valid_temperature(self) -> None:
        """Test validating valid temperature."""
        assert TemperatureValidator.validate(0.7, "openai") == 0.7
        assert TemperatureValidator.validate(1.0, "openai") == 1.0
        assert TemperatureValidator.validate(0.0, "openai") == 0.0

    def test_validate_max_temperature_openai(self) -> None:
        """Test maximum temperature for OpenAI."""
        assert TemperatureValidator.validate(2.0, "openai") == 2.0

    def test_validate_max_temperature_anthropic(self) -> None:
        """Test maximum temperature for Anthropic."""
        assert TemperatureValidator.validate(1.0, "anthropic") == 1.0

    def test_validate_temperature_too_low(self) -> None:
        """Test error when temperature is too low."""
        with pytest.raises(ConfigurationError) as exc_info:
            TemperatureValidator.validate(-0.1, "openai")

        assert "must be >=" in str(exc_info.value)

    def test_validate_temperature_too_high_openai(self) -> None:
        """Test error when temperature is too high for OpenAI."""
        with pytest.raises(ConfigurationError) as exc_info:
            TemperatureValidator.validate(2.1, "openai")

        assert "must be <=" in str(exc_info.value)

    def test_validate_temperature_too_high_anthropic(self) -> None:
        """Test error when temperature is too high for Anthropic."""
        with pytest.raises(ConfigurationError) as exc_info:
            TemperatureValidator.validate(1.1, "anthropic")

        assert "must be <=" in str(exc_info.value)
        assert "anthropic" in str(exc_info.value).lower()

    def test_validate_edge_cases(self) -> None:
        """Test edge case temperatures."""
        assert TemperatureValidator.validate(0.0, "openai") == 0.0
        assert TemperatureValidator.validate(2.0, "openai") == 2.0
        assert TemperatureValidator.validate(1.0, "anthropic") == 1.0


class TestModelValidator:
    """Test model validator."""

    def test_validate_valid_openai_models(self) -> None:
        """Test validating valid OpenAI models."""
        assert ModelValidator.validate("gpt-3.5-turbo", "openai") == "gpt-3.5-turbo"
        assert ModelValidator.validate("gpt-4", "openai") == "gpt-4"
        assert ModelValidator.validate("gpt-4o", "openai") == "gpt-4o"

    def test_validate_valid_anthropic_models(self) -> None:
        """Test validating valid Anthropic models."""
        model = "claude-3-5-sonnet-20241022"
        assert ModelValidator.validate(model, "anthropic") == model

    def test_validate_model_with_version_suffix(self) -> None:
        """Test validating model with version suffix."""
        # Should accept models with version numbers
        assert ModelValidator.validate("gpt-4-0613", "openai") == "gpt-4-0613"

    def test_validate_invalid_model(self) -> None:
        """Test error when model is invalid."""
        with pytest.raises(ConfigurationError) as exc_info:
            ModelValidator.validate("invalid-model", "openai")

        assert "not supported" in str(exc_info.value)
        assert "invalid-model" in str(exc_info.value)

    def test_validate_wrong_provider_model(self) -> None:
        """Test error when using model from wrong provider."""
        with pytest.raises(ConfigurationError) as exc_info:
            ModelValidator.validate("claude-3-5-sonnet-20241022", "openai")

        assert "not supported" in str(exc_info.value)

    def test_is_valid_model_true(self) -> None:
        """Test is_valid_model returns True for valid models."""
        assert ModelValidator.is_valid_model("gpt-3.5-turbo", "openai")
        assert ModelValidator.is_valid_model("gpt-4", "openai")
        assert ModelValidator.is_valid_model("claude-3-5-sonnet-20241022", "anthropic")

    def test_is_valid_model_false(self) -> None:
        """Test is_valid_model returns False for invalid models."""
        assert not ModelValidator.is_valid_model("invalid-model", "openai")
        assert not ModelValidator.is_valid_model("gpt-3.5-turbo", "anthropic")

    def test_get_valid_models_openai(self) -> None:
        """Test getting valid models for OpenAI."""
        models = ModelValidator._get_valid_models("openai")
        assert "gpt-3.5-turbo" in models
        assert "gpt-4" in models
        assert "gpt-4o" in models

    def test_get_valid_models_anthropic(self) -> None:
        """Test getting valid models for Anthropic."""
        models = ModelValidator._get_valid_models("anthropic")
        assert "claude-3-5-sonnet-20241022" in models
        assert "claude-3-opus-20240229" in models

    def test_validate_case_sensitivity(self) -> None:
        """Test that provider names are case-insensitive."""
        assert ModelValidator.validate("gpt-3.5-turbo", "OpenAI") == "gpt-3.5-turbo"
        model = "claude-3-5-sonnet-20241022"
        assert ModelValidator.validate(model, "Anthropic") == model
