"""
Qdrant collection schema definitions.

Sandi Metz Principles:
- Single Responsibility: Schema configuration
- Small class: Clear schema structure
- Dependency Injection: Configuration injected
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from qdrant_client.models import Distance


class QdrantDistanceMetric(str, Enum):
    """
    Distance metrics for vector similarity.

    COSINE: Cosine similarity (default for most text embeddings)
    EUCLID: Euclidean distance
    DOT: Dot product similarity
    """

    COSINE = "Cosine"
    EUCLID = "Euclid"
    DOT = "Dot"

    def to_qdrant_distance(self) -> Distance:
        """Convert to Qdrant Distance enum."""
        mapping = {
            self.COSINE: Distance.COSINE,
            self.EUCLID: Distance.EUCLID,
            self.DOT: Distance.DOT,
        }
        return mapping[self]


class VectorPayloadSchema(BaseModel):
    """
    Schema for vector point payload.

    Defines metadata stored with each vector.
    """

    # Required fields
    query_hash: str = Field(..., description="Hash of the original query")
    original_query: str = Field(..., description="Original query text")
    response: str = Field(..., description="Cached response")

    # Provider info
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="LLM model used")

    # Token usage
    prompt_tokens: int = Field(..., ge=0, description="Tokens in prompt")
    completion_tokens: int = Field(..., ge=0, description="Tokens in completion")

    # Timestamps
    created_at: Optional[float] = Field(None, description="Creation timestamp")
    cached_at: Optional[float] = Field(None, description="Cache timestamp")

    # Additional metadata
    tags: Optional[List[str]] = Field(None, description="Optional tags")
    metadata: Optional[Dict[str, str]] = Field(None, description="Extra metadata")


class CollectionConfig(BaseModel):
    """
    Configuration for Qdrant collection.

    Defines collection parameters.
    """

    name: str = Field(..., description="Collection name")
    vector_size: int = Field(..., ge=1, description="Vector dimension size")
    distance: QdrantDistanceMetric = Field(
        default=QdrantDistanceMetric.COSINE, description="Distance metric"
    )
    on_disk_payload: bool = Field(default=False, description="Store payload on disk")
    hnsw_config: Optional[Dict[str, int]] = Field(
        None, description="HNSW index configuration"
    )

    @property
    def qdrant_distance(self) -> Distance:
        """Get Qdrant Distance enum."""
        return self.distance.to_qdrant_distance()


class SearchConfig(BaseModel):
    """
    Configuration for vector search.

    Defines search parameters.
    """

    limit: int = Field(default=5, ge=1, le=100, description="Max results")
    score_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Minimum similarity score"
    )
    exact: bool = Field(default=False, description="Exact search (no HNSW)")
    with_payload: bool = Field(default=True, description="Include payload")
    with_vectors: bool = Field(default=False, description="Include vectors")


class PointMetadata(BaseModel):
    """
    Metadata for a vector point.

    Minimal info for identification.
    """

    point_id: str = Field(..., description="Unique point ID")
    query_hash: str = Field(..., description="Query hash")
    score: Optional[float] = Field(None, description="Similarity score")
    created_at: Optional[float] = Field(None, description="Creation timestamp")


class IndexConfig(BaseModel):
    """
    HNSW index configuration.

    Controls index performance and accuracy.
    """

    m: int = Field(default=16, ge=4, le=64, description="Links per node")
    ef_construct: int = Field(
        default=100, ge=4, description="Construction time accuracy"
    )
    full_scan_threshold: int = Field(
        default=10000, ge=0, description="Threshold for full scan"
    )
    on_disk: bool = Field(default=False, description="Store index on disk")


class QdrantSchema:
    """
    Central schema configuration.

    Provides schema constants and defaults.
    """

    # Payload field names
    FIELD_QUERY_HASH = "query_hash"
    FIELD_ORIGINAL_QUERY = "original_query"
    FIELD_RESPONSE = "response"
    FIELD_PROVIDER = "provider"
    FIELD_MODEL = "model"
    FIELD_PROMPT_TOKENS = "prompt_tokens"
    FIELD_COMPLETION_TOKENS = "completion_tokens"
    FIELD_CREATED_AT = "created_at"
    FIELD_CACHED_AT = "cached_at"
    FIELD_TAGS = "tags"
    FIELD_METADATA = "metadata"

    # Default configurations
    DEFAULT_DISTANCE = QdrantDistanceMetric.COSINE
    DEFAULT_VECTOR_SIZE = 384  # sentence-transformers/all-MiniLM-L6-v2
    DEFAULT_SEARCH_LIMIT = 5
    DEFAULT_SCORE_THRESHOLD = 0.85

    @staticmethod
    def get_indexed_fields() -> List[str]:
        """
        Get fields that should be indexed for filtering.

        Returns:
            List of field names to index
        """
        return [
            QdrantSchema.FIELD_QUERY_HASH,
            QdrantSchema.FIELD_PROVIDER,
            QdrantSchema.FIELD_MODEL,
            QdrantSchema.FIELD_CREATED_AT,
        ]

    @staticmethod
    def get_required_fields() -> List[str]:
        """
        Get required payload fields.

        Returns:
            List of required field names
        """
        return [
            QdrantSchema.FIELD_QUERY_HASH,
            QdrantSchema.FIELD_ORIGINAL_QUERY,
            QdrantSchema.FIELD_RESPONSE,
            QdrantSchema.FIELD_PROVIDER,
            QdrantSchema.FIELD_MODEL,
            QdrantSchema.FIELD_PROMPT_TOKENS,
            QdrantSchema.FIELD_COMPLETION_TOKENS,
        ]
