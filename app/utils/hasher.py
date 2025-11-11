"""
Cache key generation utilities.

Sandi Metz Principles:
- Single Responsibility: Hash generation
- Small functions: Each does one thing
- Pure functions: No side effects
"""

import hashlib


def normalize_query(query: str) -> str:
    """
    Normalize query for comparison.

    Args:
        query: Query text

    Returns:
        Normalized query (lowercase, trimmed)
    """
    return query.strip().lower()


def generate_cache_key(query: str) -> str:
    """
    Generate cache key for query.

    Args:
        query: Query text

    Returns:
        Cache key (query:sha256hash)
    """
    normalized = normalize_query(query)
    hash_value = hashlib.sha256(normalized.encode()).hexdigest()
    return f"query:{hash_value}"


def generate_embedding_key(query_hash: str) -> str:
    """
    Generate key for storing embeddings.

    Args:
        query_hash: Query hash

    Returns:
        Embedding key
    """
    return f"embedding:{query_hash}"
