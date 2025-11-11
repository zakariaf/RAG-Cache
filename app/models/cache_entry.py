"""
Cache entry models.

Sandi Metz Principles:
- Single Responsibility: Cache data structure
- Clear naming: Descriptive fields
- Immutable data: All fields are read-only after creation
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    """Cache entry for storing query results."""

    query_hash: str = Field(..., description="Hash of the normalized query")
    original_query: str = Field(..., description="Original query text")
    response: str = Field(..., description="Cached response")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used")
    prompt_tokens: int = Field(..., ge=0, description="Prompt tokens")
    completion_tokens: int = Field(..., ge=0, description="Completion tokens")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Cache entry creation time"
    )
    hit_count: int = Field(default=0, ge=0, description="Number of cache hits")
    embedding: Optional[list[float]] = Field(None, description="Query embedding vector")

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used."""
        return self.prompt_tokens + self.completion_tokens

    @property
    def age_seconds(self) -> float:
        """Calculate entry age in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()

    def increment_hit_count(self) -> None:
        """Increment cache hit counter."""
        self.hit_count += 1


class SemanticMatch(BaseModel):
    """Semantic similarity match result."""

    entry: CacheEntry = Field(..., description="Matched cache entry")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    query_hash: str = Field(..., description="Matched query hash")

    @property
    def is_strong_match(self) -> bool:
        """Check if similarity score indicates strong match."""
        return self.similarity_score >= 0.90

    @property
    def is_moderate_match(self) -> bool:
        """Check if similarity score indicates moderate match."""
        return 0.80 <= self.similarity_score < 0.90

    @property
    def is_weak_match(self) -> bool:
        """Check if similarity score indicates weak match."""
        return self.similarity_score < 0.80
