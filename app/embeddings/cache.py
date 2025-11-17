"""
Embedding cache for storing generated embeddings.

Caches embeddings to avoid regenerating for the same text.

Sandi Metz Principles:
- Single Responsibility: Cache embedding results
- Small class: Focused caching logic
- Dependency Injection: Generator injected
"""

import hashlib
from typing import Dict, Optional

from app.embeddings.generator import EmbeddingGenerator
from app.models.embedding import EmbeddingResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """
    In-memory cache for embedding results.

    Uses LRU-style eviction when cache size exceeds maximum.
    Keyed by hash of input text for efficient lookups.
    """

    def __init__(
        self,
        generator: EmbeddingGenerator,
        max_size: int = 1000,
    ):
        """
        Initialize embedding cache.

        Args:
            generator: Embedding generator to use for cache misses
            max_size: Maximum number of cached embeddings
        """
        self._generator = generator
        self._max_size = max_size
        self._cache: Dict[str, EmbeddingResult] = {}
        self._access_order: list[str] = []  # Track access order for LRU
        self._hits = 0
        self._misses = 0

    async def get_or_generate(
        self, text: str, normalize: bool = True
    ) -> EmbeddingResult:
        """
        Get embedding from cache or generate if not cached.

        Args:
            text: Text to embed
            normalize: Whether to normalize embedding

        Returns:
            Cached or newly generated embedding result

        Raises:
            EmbeddingGeneratorError: If generation fails
            ValueError: If text is empty
        """
        # Generate cache key
        cache_key = self._get_cache_key(text, normalize)

        # Check cache
        if cache_key in self._cache:
            self._hits += 1
            self._update_access_order(cache_key)
            logger.debug(
                "Embedding cache hit",
                text_length=len(text),
                cache_size=len(self._cache),
                hit_rate=self.hit_rate,
            )
            return self._cache[cache_key]

        # Cache miss - generate embedding
        self._misses += 1
        logger.debug(
            "Embedding cache miss",
            text_length=len(text),
            cache_size=len(self._cache),
        )

        embedding = await self._generator.generate(text, normalize=normalize)

        # Store in cache
        self._put(cache_key, embedding)

        return embedding

    def _get_cache_key(self, text: str, normalize: bool) -> str:
        """
        Generate cache key for text and normalization setting.

        Args:
            text: Input text
            normalize: Normalization flag

        Returns:
            Cache key string
        """
        # Hash text and normalize flag together
        content = f"{text}|{normalize}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _put(self, key: str, value: EmbeddingResult) -> None:
        """
        Put embedding in cache with LRU eviction.

        Args:
            key: Cache key
            value: Embedding result to cache
        """
        # If cache is full, evict least recently used
        if len(self._cache) >= self._max_size and key not in self._cache:
            self._evict_lru()

        # Add to cache
        self._cache[key] = value
        self._update_access_order(key)

        logger.debug(
            "Cached embedding",
            cache_size=len(self._cache),
            max_size=self._max_size,
        )

    def _evict_lru(self) -> None:
        """Evict least recently used item from cache."""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]
                logger.debug(
                    "Evicted LRU embedding",
                    cache_size=len(self._cache),
                )

    def _update_access_order(self, key: str) -> None:
        """
        Update access order for LRU tracking.

        Args:
            key: Cache key that was accessed
        """
        # Remove key if already in access order
        if key in self._access_order:
            self._access_order.remove(key)

        # Add to end (most recently used)
        self._access_order.append(key)

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._cache.clear()
        self._access_order.clear()
        logger.info("Cleared embedding cache")

    def invalidate(self, text: str, normalize: bool = True) -> bool:
        """
        Invalidate specific cache entry.

        Args:
            text: Text to invalidate
            normalize: Normalization flag used when cached

        Returns:
            True if entry was found and removed
        """
        cache_key = self._get_cache_key(text, normalize)

        if cache_key in self._cache:
            del self._cache[cache_key]
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            logger.debug("Invalidated cache entry", text_length=len(text))
            return True

        return False

    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    @property
    def max_size(self) -> int:
        """Get maximum cache size."""
        return self._max_size

    @property
    def hits(self) -> int:
        """Get cache hit count."""
        return self._hits

    @property
    def misses(self) -> int:
        """Get cache miss count."""
        return self._misses

    @property
    def hit_rate(self) -> float:
        """
        Get cache hit rate.

        Returns:
            Hit rate as percentage (0.0 to 1.0)
        """
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 4),
            "total_requests": self.hits + self.misses,
        }

    def reset_stats(self) -> None:
        """Reset cache statistics counters."""
        self._hits = 0
        self._misses = 0
        logger.info("Reset embedding cache statistics")

    def is_cached(self, text: str, normalize: bool = True) -> bool:
        """
        Check if text embedding is cached.

        Args:
            text: Text to check
            normalize: Normalization flag

        Returns:
            True if embedding is cached
        """
        cache_key = self._get_cache_key(text, normalize)
        return cache_key in self._cache

    def peek(self, text: str, normalize: bool = True) -> Optional[EmbeddingResult]:
        """
        Peek at cached embedding without updating access order.

        Args:
            text: Text to peek
            normalize: Normalization flag

        Returns:
            Cached embedding or None if not found
        """
        cache_key = self._get_cache_key(text, normalize)
        return self._cache.get(cache_key)

    def set_max_size(self, max_size: int) -> None:
        """
        Update maximum cache size.

        If new size is smaller than current size, evicts LRU entries.

        Args:
            max_size: New maximum cache size
        """
        if max_size < 1:
            raise ValueError("Max size must be at least 1")

        self._max_size = max_size

        # Evict entries if cache is now too large
        while len(self._cache) > self._max_size:
            self._evict_lru()

        logger.info("Updated cache max size", max_size=max_size, current_size=self.size)
