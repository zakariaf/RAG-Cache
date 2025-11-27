"""
Embedding Cache Service.

Caches generated embeddings to avoid redundant computation.

Sandi Metz Principles:
- Single Responsibility: Embedding caching
- Small methods: Each operation isolated
- TTL management: Configurable expiration
"""

import hashlib
from typing import List, Optional

from app.cache.redis_cache import RedisCache
from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """
    Caches embeddings in Redis for fast retrieval.

    Avoids redundant embedding generation.
    """

    # Cache key prefix for embeddings
    PREFIX = "emb:"
    DEFAULT_TTL = 86400  # 24 hours

    def __init__(
        self,
        redis_cache: RedisCache,
        ttl_seconds: Optional[int] = None,
        model_name: Optional[str] = None,
    ):
        """
        Initialize embedding cache.

        Args:
            redis_cache: Redis cache instance
            ttl_seconds: Time-to-live for cached embeddings
            model_name: Model name for cache key versioning
        """
        self._cache = redis_cache
        self._ttl = ttl_seconds or self.DEFAULT_TTL
        self._model = model_name or config.embedding_model

    async def get(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding for text.

        Args:
            text: Input text

        Returns:
            Cached embedding or None
        """
        key = self._make_key(text)
        try:
            cached = await self._cache.get_raw(key)
            if cached:
                logger.debug("Embedding cache hit", text_hash=key[-8:])
                return cached.get("embedding")
            logger.debug("Embedding cache miss", text_hash=key[-8:])
            return None
        except Exception as e:
            logger.error("Embedding cache get failed", error=str(e))
            return None

    async def set(self, text: str, embedding: List[float]) -> bool:
        """
        Cache an embedding.

        Args:
            text: Input text
            embedding: Generated embedding

        Returns:
            True if cached successfully
        """
        key = self._make_key(text)
        try:
            success = await self._cache.set_raw(
                key,
                {"embedding": embedding, "model": self._model},
                ttl=self._ttl,
            )
            if success:
                logger.debug("Embedding cached", text_hash=key[-8:])
            return success
        except Exception as e:
            logger.error("Embedding cache set failed", error=str(e))
            return False

    async def get_or_generate(
        self,
        text: str,
        generator_fn,
    ) -> List[float]:
        """
        Get cached embedding or generate new one.

        Args:
            text: Input text
            generator_fn: Async function to generate embedding

        Returns:
            Embedding vector
        """
        # Try cache first
        cached = await self.get(text)
        if cached:
            return cached

        # Generate and cache
        embedding = await generator_fn(text)
        await self.set(text, embedding)
        return embedding

    async def invalidate(self, text: str) -> bool:
        """
        Invalidate cached embedding.

        Args:
            text: Input text

        Returns:
            True if invalidated
        """
        key = self._make_key(text)
        try:
            await self._cache.delete_raw(key)
            logger.debug("Embedding invalidated", text_hash=key[-8:])
            return True
        except Exception as e:
            logger.error("Embedding invalidation failed", error=str(e))
            return False

    async def exists(self, text: str) -> bool:
        """
        Check if embedding is cached.

        Args:
            text: Input text

        Returns:
            True if cached
        """
        key = self._make_key(text)
        try:
            return await self._cache.exists_raw(key)
        except Exception:
            return False

    def _make_key(self, text: str) -> str:
        """
        Generate cache key for text.

        Args:
            text: Input text

        Returns:
            Cache key
        """
        # Include model in hash for versioning
        content = f"{self._model}:{text}"
        text_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
        return f"{self.PREFIX}{text_hash}"

    @property
    def ttl(self) -> int:
        """Get TTL in seconds."""
        return self._ttl

    def set_ttl(self, seconds: int) -> None:
        """Update TTL for new entries."""
        self._ttl = seconds
        logger.info("Embedding cache TTL updated", ttl=seconds)

