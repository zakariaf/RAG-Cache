"""
Query request and validation models.

Sandi Metz Principles:
- Small classes focused on data validation
- Clear property names
- Single responsibility per model
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    """Incoming query request with validation."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User query text",
        examples=["What is the capital of France?"],
    )

    provider: Optional[Literal["openai", "anthropic"]] = Field(
        None, description="LLM provider to use (defaults to config)"
    )

    model: Optional[str] = Field(
        None,
        description="Specific model name",
        examples=["gpt-3.5-turbo", "claude-3-sonnet-20240229"],
    )

    max_tokens: Optional[int] = Field(
        None, ge=1, le=4000, description="Maximum tokens in response"
    )

    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Response randomness (0=deterministic, 2=creative)",
    )

    use_cache: bool = Field(default=True, description="Enable cache lookup")

    use_semantic_cache: bool = Field(
        default=True, description="Enable semantic similarity search"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and normalize query."""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v

    def get_provider(self, default: str) -> str:
        """Get provider with fallback to default."""
        return self.provider or default

    def get_model(self, default: str) -> str:
        """Get model with fallback to default."""
        return self.model or default

    def get_max_tokens(self, default: int) -> int:
        """Get max_tokens with fallback to default."""
        return self.max_tokens or default

    def get_temperature(self, default: float) -> float:
        """Get temperature with fallback to default."""
        return self.temperature if self.temperature is not None else default
