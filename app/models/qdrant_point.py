"""
Qdrant point models for vector storage.

Sandi Metz Principles:
- Single Responsibility: Point data modeling
- Small class: Focused on point representation
- Clear naming: Descriptive field names
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError
from qdrant_client.models import PointStruct

from app.models.cache_entry import CacheEntry


class QdrantPoint(BaseModel):
    """
    Represents a point (vector + payload) in Qdrant.

    Combines embedding vector with metadata.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Point ID")
    vector: List[float] = Field(..., description="Embedding vector")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Metadata")

    @classmethod
    def from_cache_entry(
        cls, entry: CacheEntry, embedding: List[float]
    ) -> "QdrantPoint":
        """
        Create point from cache entry.

        Args:
            entry: Cache entry with query and response
            embedding: Vector embedding of query

        Returns:
            QdrantPoint instance
        """
        payload = {
            "query_hash": entry.query_hash,
            "original_query": entry.original_query,
            "response": entry.response,
            "provider": entry.provider,
            "model": entry.model,
            "prompt_tokens": entry.prompt_tokens,
            "completion_tokens": entry.completion_tokens,
            "created_at": entry.created_at.timestamp(),
            "cached_at": time.time(),
        }

        # Add optional fields
        if entry.embedding is not None:
            payload["has_embedding"] = True

        return cls(vector=embedding, payload=payload)

    def to_qdrant_point(self) -> PointStruct:
        """
        Convert to Qdrant PointStruct.

        Returns:
            PointStruct for Qdrant API
        """
        return PointStruct(id=self.id, vector=self.vector, payload=self.payload)

    @classmethod
    def from_qdrant_point(
        cls, point_id: str, vector: List[float], payload: Dict
    ) -> "QdrantPoint":
        """
        Create from Qdrant point data.

        Args:
            point_id: Point ID
            vector: Embedding vector
            payload: Metadata dict

        Returns:
            QdrantPoint instance
        """
        return cls(id=point_id, vector=vector, payload=payload)


class SearchResult(BaseModel):
    """
    Result from vector similarity search.

    Contains matched point and similarity score.
    """

    point_id: str = Field(..., description="Matched point ID")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    vector: Optional[List[float]] = Field(None, description="Embedding vector")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Metadata")

    @property
    def query_hash(self) -> Optional[str]:
        """Get query hash from payload."""
        return self.payload.get("query_hash")

    @property
    def original_query(self) -> Optional[str]:
        """Get original query from payload."""
        return self.payload.get("original_query")

    @property
    def response(self) -> Optional[str]:
        """Get response from payload."""
        return self.payload.get("response")

    @property
    def provider(self) -> Optional[str]:
        """Get provider from payload."""
        return self.payload.get("provider")

    @property
    def model(self) -> Optional[str]:
        """Get model from payload."""
        return self.payload.get("model")

    def to_cache_entry(self) -> Optional[CacheEntry]:
        """
        Convert to cache entry.

        Returns:
            CacheEntry if payload is valid, None otherwise
        """
        try:
            # Convert timestamp back to datetime if present
            created_at = None
            if "created_at" in self.payload:
                created_at = datetime.fromtimestamp(self.payload["created_at"])

            return CacheEntry(
                query_hash=self.payload["query_hash"],
                original_query=self.payload["original_query"],
                response=self.payload["response"],
                provider=self.payload["provider"],
                model=self.payload["model"],
                prompt_tokens=self.payload.get("prompt_tokens", 0),
                completion_tokens=self.payload.get("completion_tokens", 0),
                embedding=self.vector,
                created_at=created_at,
            )
        except (KeyError, ValidationError, ValueError):
            # KeyError: missing required field
            # ValidationError: pydantic validation failed
            # ValueError: invalid timestamp
            return None


class BatchUploadResult(BaseModel):
    """
    Result from batch upload operation.

    Tracks success and failure counts.
    """

    total: int = Field(..., ge=0, description="Total points")
    successful: int = Field(..., ge=0, description="Successfully uploaded")
    failed: int = Field(..., ge=0, description="Failed uploads")
    point_ids: List[str] = Field(default_factory=list, description="Uploaded IDs")
    errors: List[str] = Field(default_factory=list, description="Error messages")

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total == 0:
            return 0.0
        return self.successful / self.total

    @property
    def has_failures(self) -> bool:
        """Check if there were any failures."""
        return self.failed > 0


class DeleteResult(BaseModel):
    """
    Result from delete operation.

    Tracks deletion status.
    """

    deleted_count: int = Field(..., ge=0, description="Number deleted")
    success: bool = Field(..., description="Operation success")
    message: Optional[str] = Field(None, description="Status message")
