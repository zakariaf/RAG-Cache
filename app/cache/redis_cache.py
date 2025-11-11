"""
Redis cache service.

Sandi Metz Principles:
- Single Responsibility: Cache operations orchestration
- Small methods: Each operation < 10 lines
- Dependency Injection: Repository injected
"""

from typing import Optional

from app.config import config
from app.models.cache_entry import CacheEntry
from app.repositories.redis_repository import RedisRepository
from app.utils.hasher import generate_cache_key
from app.utils.logger import get_logger, log_cache_hit, log_cache_miss

logger = get_logger(__name__)


class RedisCache:
    """
    Redis cache service.

    Provides high-level cache operations.
    """

    def __init__(self, repository: RedisRepository):
        """
        Initialize cache service.

        Args:
            repository: Redis repository
        """
        self._repository = repository
        self._ttl = config.cache_ttl_seconds

    async def get(self, query: str) -> Optional[CacheEntry]:
        """
        Get cached entry for query.

        Args:
            query: Query text

        Returns:
            Cache entry if found, None otherwise
        """
        key = generate_cache_key(query)
        entry = await self._repository.fetch(key)

        if entry:
            log_cache_hit(query, source="exact")
            return entry

        log_cache_miss(query)
        return None

    async def set(self, entry: CacheEntry) -> bool:
        """
        Store cache entry.

        Args:
            entry: Cache entry to store

        Returns:
            True if stored successfully
        """
        key = entry.query_hash
        success = await self._repository.store(key, entry, self._ttl)

        if success:
            logger.info("Cache stored", key=key)
        else:
            logger.error("Cache store failed", key=key)

        return success

    async def delete(self, query: str) -> bool:
        """
        Delete cache entry.

        Args:
            query: Query text

        Returns:
            True if deleted successfully
        """
        key = generate_cache_key(query)
        return await self._repository.delete(key)

    async def exists(self, query: str) -> bool:
        """
        Check if query is cached.

        Args:
            query: Query text

        Returns:
            True if cached, False otherwise
        """
        key = generate_cache_key(query)
        return await self._repository.exists(key)

    async def health_check(self) -> bool:
        """
        Check Redis health.

        Returns:
            True if healthy, False otherwise
        """
        return await self._repository.ping()
