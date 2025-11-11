"""
LLM request and response models.

Sandi Metz Principles:
- Small classes focused on LLM interaction
- Clear separation of request and response
- Immutable data structures
"""

from typing import Protocol

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """LLM response model."""

    content: str = Field(..., description="Response content")
    prompt_tokens: int = Field(..., description="Prompt tokens", ge=0)
    completion_tokens: int = Field(..., description="Completion tokens", ge=0)
    model: str = Field(..., description="Model used")

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens."""
        return self.prompt_tokens + self.completion_tokens


class LLMProvider(Protocol):
    """
    LLM provider protocol.

    Defines interface for LLM providers.
    Follows Liskov Substitution Principle.
    """

    async def complete(
        self, request: "QueryRequest"  # type: ignore  # noqa: F821
    ) -> LLMResponse:
        """
        Generate completion for query.

        Args:
            request: Query request

        Returns:
            LLM response

        Raises:
            LLMProviderError: If completion fails
        """
        ...

    def get_name(self) -> str:
        """
        Get provider name.

        Returns:
            Provider name (e.g., "openai", "anthropic")
        """
        ...
