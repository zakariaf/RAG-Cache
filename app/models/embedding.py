"""
Embedding vector models.

Sandi Metz Principles:
- Small classes with clear purpose
- Type-safe vector representation
- Clear naming conventions
"""

import math
from typing import List

from pydantic import BaseModel, Field, field_validator, model_validator


class EmbeddingVector(BaseModel):
    """
    Embedding vector with metadata.

    Represents a high-dimensional vector embedding with associated metadata
    for semantic search and similarity matching.
    """

    vector: List[float] = Field(..., description="Embedding vector values")
    dimensions: int = Field(..., ge=1, le=10000, description="Vector dimensionality")
    model: str = Field(..., description="Embedding model used")
    normalized: bool = Field(default=False, description="Whether vector is normalized")

    @field_validator("vector")
    @classmethod
    def validate_vector_not_empty(cls, v: List[float]) -> List[float]:
        """Validate vector is not empty."""
        if not v:
            raise ValueError("Embedding vector cannot be empty")
        return v

    @field_validator("model")
    @classmethod
    def validate_model_not_empty(cls, v: str) -> str:
        """Validate model name is not empty."""
        if not v or v.strip() == "":
            raise ValueError("Model name cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_vector_dimensions(self) -> "EmbeddingVector":
        """Validate vector dimensions and values."""
        # Check dimensions match vector length
        if len(self.vector) != self.dimensions:
            raise ValueError(
                f"Vector length ({len(self.vector)}) does not match "
                f"dimensions ({self.dimensions})"
            )

        # Validate all values are valid floats
        for i, val in enumerate(self.vector):
            if not isinstance(val, (int, float)):
                raise ValueError(f"Invalid vector value at index {i}: {val}")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Vector contains NaN or Inf at index {i}")

        return self

    @classmethod
    def create(
        cls,
        vector: List[float],
        model: str,
        normalized: bool = False,
    ) -> "EmbeddingVector":
        """
        Create embedding vector with automatic dimension detection.

        Args:
            vector: Embedding vector values
            model: Embedding model name
            normalized: Whether vector is normalized

        Returns:
            EmbeddingVector instance

        Raises:
            ValueError: If vector is empty or invalid
        """
        # Validation happens in model_validator
        dimensions = len(vector)

        return cls(
            vector=vector,
            dimensions=dimensions,
            model=model,
            normalized=normalized,
        )

    def normalize(self) -> "EmbeddingVector":
        """
        Create normalized copy of this embedding.

        Returns:
            New EmbeddingVector with L2-normalized vector

        Raises:
            ValueError: If vector has zero magnitude
        """
        # Calculate L2 norm (magnitude)
        magnitude = math.sqrt(sum(x * x for x in self.vector))

        if magnitude == 0.0:
            raise ValueError("Cannot normalize zero vector")

        # Normalize vector
        normalized_vector = [x / magnitude for x in self.vector]

        return self.model_copy(
            update={
                "vector": normalized_vector,
                "normalized": True,
            }
        )

    def dot_product(self, other: "EmbeddingVector") -> float:
        """
        Calculate dot product with another embedding.

        Args:
            other: Another embedding vector

        Returns:
            Dot product value

        Raises:
            ValueError: If dimensions don't match
        """
        if self.dimensions != other.dimensions:
            raise ValueError(
                f"Dimension mismatch: {self.dimensions} vs {other.dimensions}"
            )

        return sum(a * b for a, b in zip(self.vector, other.vector))

    def cosine_similarity(self, other: "EmbeddingVector") -> float:
        """
        Calculate cosine similarity with another embedding.

        Args:
            other: Another embedding vector

        Returns:
            Cosine similarity (0.0 to 1.0)

        Raises:
            ValueError: If dimensions don't match or vectors are zero
        """
        if self.dimensions != other.dimensions:
            raise ValueError(
                f"Dimension mismatch: {self.dimensions} vs {other.dimensions}"
            )

        # If both are normalized, dot product = cosine similarity
        if self.normalized and other.normalized:
            return self.dot_product(other)

        # Calculate magnitudes
        mag_self = math.sqrt(sum(x * x for x in self.vector))
        mag_other = math.sqrt(sum(x * x for x in other.vector))

        if mag_self == 0.0 or mag_other == 0.0:
            raise ValueError("Cannot calculate cosine similarity with zero vector")

        # Calculate cosine similarity
        dot_prod = self.dot_product(other)
        return dot_prod / (mag_self * mag_other)

    @property
    def magnitude(self) -> float:
        """Get L2 norm (magnitude) of the vector."""
        return math.sqrt(sum(x * x for x in self.vector))

    @property
    def is_zero_vector(self) -> bool:
        """Check if this is a zero vector."""
        return all(x == 0.0 for x in self.vector)

    @property
    def is_unit_vector(self) -> bool:
        """Check if this is a unit vector (magnitude = 1.0)."""
        # Allow small floating point error
        return abs(self.magnitude - 1.0) < 1e-6

    def to_list(self) -> List[float]:
        """Get vector as list of floats."""
        return self.vector.copy()


class EmbeddingResult(BaseModel):
    """Result of embedding generation."""

    embedding: EmbeddingVector = Field(..., description="Generated embedding vector")
    text: str = Field(..., description="Original text that was embedded")
    tokens: int = Field(..., ge=0, description="Number of tokens in text")
    model: str = Field(..., description="Model used for embedding")

    @classmethod
    def create(
        cls,
        text: str,
        vector: List[float],
        model: str,
        tokens: int = 0,
        normalized: bool = False,
    ) -> "EmbeddingResult":
        """
        Create embedding result with automatic vector creation.

        Args:
            text: Original text
            vector: Embedding vector
            model: Model name
            tokens: Token count
            normalized: Whether vector is normalized

        Returns:
            EmbeddingResult instance
        """
        embedding = EmbeddingVector.create(
            vector=vector,
            model=model,
            normalized=normalized,
        )

        return cls(
            embedding=embedding,
            text=text,
            tokens=tokens,
            model=model,
        )

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        return self.embedding.dimensions

    @property
    def is_normalized(self) -> bool:
        """Check if embedding is normalized."""
        return self.embedding.normalized
