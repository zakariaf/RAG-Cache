"""
LLM provider base class and interface.

Sandi Metz Principles:
- Single Responsibility: Provider abstraction
- Interface Segregation: Minimal provider interface
- Dependency Inversion: Depend on abstraction, not concrete classes
"""

from abc import ABC, abstractmethod

from app.models.llm import LLMResponse
from app.models.query import QueryRequest


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Defines interface that all providers must implement.
    """

    @abstractmethod
    async def complete(self, request: QueryRequest) -> LLMResponse:
        """
        Generate completion for query.

        Args:
            request: Query request

        Returns:
            LLM response

        Raises:
            LLMProviderError: If completion fails
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get provider name.

        Returns:
            Provider name (e.g., "openai", "anthropic")
        """
        pass

    def _build_error_message(self, error: Exception, context: str) -> str:
        """
        Build error message with context.

        Args:
            error: The exception that occurred
            context: Context description

        Returns:
            Formatted error message
        """
        return f"{context}: {type(error).__name__} - {str(error)}"
