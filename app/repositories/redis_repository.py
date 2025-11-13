"""
Redis repository for data access.

Sandi Metz Principles:
- Single Responsibility: Redis data access
- Small methods: Each operation isolated
- Dependency Injection: Redis pool injected
"""

import json
from typing import Optional

from redis.asyncio import ConnectionPool, Redis

from app.config import config
from app.models.cache_entry import CacheEntry
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_redis_pool() -> ConnectionPool:
    """
    Create Redis connection pool.

    Returns:
        Redis connection pool
    """
    return ConnectionPool.from_url(
        config.redis_url,
        max_connections=config.redis_max_connections,
        decode_responses=True,
    )


class RedisRepository:
    """
    Repository for Redis operations.

    Handles low-level Redis interactions.
    """

    def __init__(self, pool: ConnectionPool):
        """
        Initialize repository.

        Args:
            pool: Redis connection pool
        """
        self._pool = pool

    async def fetch(self, key: str) -> Optional[CacheEntry]:
        """
        Fetch cache entry by key.

        Args:
            key: Cache key

        Returns:
            Cache entry if found, None otherwise
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                data = await client.get(key)
                if data:
                    return CacheEntry(**json.loads(data))
                return None
        except Exception as e:
            logger.error("Redis fetch failed", key=key, error=str(e))
            return None

    async def store(
        self, key: str, entry: CacheEntry, ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Store cache entry.

        Args:
            key: Cache key
            entry: Cache entry to store
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                data = entry.model_dump_json()
                if ttl_seconds:
                    await client.setex(key, ttl_seconds, data)
                else:
                    await client.set(key, data)
                return True
        except Exception as e:
            logger.error("Redis store failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete cache entry.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                result = await client.delete(key)
                return result > 0
        except Exception as e:
            logger.error("Redis delete failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                result = await client.exists(key)
                return result > 0
        except Exception as e:
            logger.error("Redis exists check failed", key=key, error=str(e))
            return False

    async def ping(self) -> bool:
        """
        Ping Redis server.

        Returns:
            True if connected, False otherwise
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                await client.ping()
                return True
        except Exception as e:
            logger.error("Redis ping failed", error=str(e))
            return False

    async def delete_by_pattern(self, pattern: str) -> int:
        """
        Delete keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                keys = []
                async for key in client.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    return await client.delete(*keys)
                return 0
        except Exception as e:
            logger.error("Pattern delete failed", pattern=pattern, error=str(e))
            return 0

    async def clear_all(self) -> bool:
        """
        Clear all keys in database.

        Returns:
            True if cleared successfully
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                await client.flushdb()
                logger.info("Redis database cleared")
                return True
        except Exception as e:
            logger.error("Clear all failed", error=str(e))
            return False

    async def get_keys_by_pattern(self, pattern: str) -> list[str]:
        """
        Get all keys matching pattern.

        Args:
            pattern: Key pattern

        Returns:
            List of matching keys
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                keys = []
                async for key in client.scan_iter(match=pattern):
                    keys.append(key)
                return keys
        except Exception as e:
            logger.error("Pattern scan failed", pattern=pattern, error=str(e))
            return []
