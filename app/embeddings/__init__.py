"""
Embedding generation module.

Provides text embedding generation using SentenceTransformers.
"""

from app.embeddings.embedding_cache import EmbeddingCache
from app.embeddings.embedding_generator import EmbeddingGenerator

__all__ = [
    "EmbeddingGenerator",
    "EmbeddingCache",
]
