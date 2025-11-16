"""
LLM request builder.

Sandi Metz Principles:
- Single Responsibility: Build standardized LLM requests
- Small methods: Each method < 10 lines
- Clear naming: Self-documenting code
"""

from typing import Any, Dict, List

from app.config import config
from app.models.query import QueryRequest


class LLMRequestBuilder:
    """
    Builder for standardized LLM API requests.

    Converts QueryRequest into provider-specific request formats.
    """

    def __init__(self, request: QueryRequest):
        """
        Initialize request builder.

        Args:
            request: Query request to build from
        """
        self._request = request

    def build_messages(self) -> List[Dict[str, str]]:
        """
        Build messages array for LLM request.

        Returns:
            List of message dicts with role and content
        """
        return [{"role": "user", "content": self._request.query}]

    def get_model(self, provider_default: str | None = None) -> str:
        """
        Get model name with fallback logic.

        Args:
            provider_default: Provider-specific default model

        Returns:
            Model name to use
        """
        if self._request.model:
            return self._request.model

        if provider_default:
            return provider_default

        return self._request.get_model(config.default_model)

    def get_max_tokens(self) -> int:
        """
        Get max tokens with config fallback.

        Returns:
            Maximum tokens for response
        """
        return self._request.get_max_tokens(config.default_max_tokens)

    def get_temperature(self) -> float:
        """
        Get temperature with config fallback.

        Returns:
            Temperature value (0.0-2.0)
        """
        return self._request.get_temperature(config.default_temperature)

    def build_openai_params(self, **overrides: Any) -> Dict[str, Any]:
        """
        Build parameters for OpenAI API.

        Args:
            **overrides: Additional or override parameters

        Returns:
            Dict of OpenAI API parameters
        """
        params = {
            "model": self.get_model(),
            "messages": self.build_messages(),
            "max_tokens": self.get_max_tokens(),
            "temperature": self.get_temperature(),
        }
        params.update(overrides)
        return params

    def build_anthropic_params(self, **overrides: Any) -> Dict[str, Any]:
        """
        Build parameters for Anthropic API.

        Args:
            **overrides: Additional or override parameters

        Returns:
            Dict of Anthropic API parameters
        """
        model = self.get_model(provider_default="claude-3-5-sonnet-20241022")

        params = {
            "model": model,
            "messages": self.build_messages(),
            "max_tokens": self.get_max_tokens(),
            "temperature": self.get_temperature(),
        }
        params.update(overrides)
        return params

    def get_query_text(self) -> str:
        """
        Get the query text.

        Returns:
            Query text string
        """
        return self._request.query

    def should_use_cache(self) -> bool:
        """
        Check if cache should be used.

        Returns:
            True if cache is enabled
        """
        return self._request.use_cache

    def should_use_semantic_cache(self) -> bool:
        """
        Check if semantic cache should be used.

        Returns:
            True if semantic cache is enabled
        """
        return self._request.use_semantic_cache
