"""
Query response models.

Sandi Metz Principles:
- Small classes with clear purpose
- Immutable response data
- Clear naming conventions
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class UsageMetrics(BaseModel):
    """Token usage metrics."""

    prompt_tokens: int = Field(..., ge=0, description="Tokens in prompt")
    completion_tokens: int = Field(..., ge=0, description="Tokens in completion")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")

    @classmethod
    def create(cls, prompt_tokens: int, completion_tokens: int) -> "UsageMetrics":
        """Create usage metrics with calculated total."""
        return cls(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )


class CacheInfo(BaseModel):
    """Cache hit information."""

    cache_hit: bool = Field(..., description="Whether cache was hit")
    cache_type: Optional[Literal["exact", "semantic"]] = Field(
        None,
        description="Type of cache hit"
    )
    similarity_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Semantic similarity score"
    )

    @classmethod
    def miss(cls) -> "CacheInfo":
        """Create cache miss info."""
        return cls(cache_hit=False)

    @classmethod
    def exact_hit(cls) -> "CacheInfo":
        """Create exact cache hit info."""
        return cls(cache_hit=True, cache_type="exact")

    @classmethod
    def semantic_hit(cls, similarity_score: float) -> "CacheInfo":
        """Create semantic cache hit info."""
        return cls(
            cache_hit=True,
            cache_type="semantic",
            similarity_score=similarity_score
        )


class QueryResponse(BaseModel):
    """Query processing response."""

    response: str = Field(..., description="LLM response text")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used")
    usage: UsageMetrics = Field(..., description="Token usage metrics")
    cache_info: CacheInfo = Field(..., description="Cache information")
    latency_ms: float = Field(..., ge=0, description="Request latency in milliseconds")

    @property
    def from_cache(self) -> bool:
        """Check if response came from cache."""
        return self.cache_info.cache_hit

    @property
    def is_exact_match(self) -> bool:
        """Check if response was exact cache match."""
        return (
            self.cache_info.cache_hit
            and self.cache_info.cache_type == "exact"
        )

    @property
    def is_semantic_match(self) -> bool:
        """Check if response was semantic cache match."""
        return (
            self.cache_info.cache_hit
            and self.cache_info.cache_type == "semantic"
        )


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"] = Field(..., description="Service status")
    environment: str = Field(..., description="Environment name")
    version: str = Field(..., description="Application version")
