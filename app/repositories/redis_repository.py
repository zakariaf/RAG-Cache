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
from app.models.statistics import RedisMetrics
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

    async def get_metrics(self) -> Optional[RedisMetrics]:
        """
        Collect Redis metrics.

        Returns:
            Redis metrics if successful, None otherwise
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                info = await client.info()
                stats = await client.info("stats")
                memory = await client.info("memory")
                keyspace = await client.info("keyspace")

                # Get total keys from keyspace info
                total_keys = 0
                for db_key, db_info in keyspace.items():
                    if db_key.startswith("db"):
                        total_keys += db_info.get("keys", 0)

                return RedisMetrics(
                    total_keys=total_keys,
                    memory_used_bytes=memory.get("used_memory", 0),
                    memory_peak_bytes=memory.get("used_memory_peak", 0),
                    total_connections=stats.get("total_connections_received", 0),
                    connected_clients=info.get("connected_clients", 0),
                    total_commands_processed=stats.get("total_commands_processed", 0),
                    uptime_seconds=info.get("uptime_in_seconds", 0),
                    hits=stats.get("keyspace_hits", 0),
                    misses=stats.get("keyspace_misses", 0),
                    evicted_keys=stats.get("evicted_keys", 0),
                    expired_keys=stats.get("expired_keys", 0),
                )
        except Exception as e:
            logger.error("Metrics collection failed", error=str(e))
            return None

    async def get_key_count(self) -> int:
        """
        Get total number of keys.

        Returns:
            Number of keys in database
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                return await client.dbsize()
        except Exception as e:
            logger.error("Key count failed", error=str(e))
            return 0

    async def get_memory_usage(self, key: str) -> int:
        """
        Get memory usage of specific key.

        Args:
            key: Cache key

        Returns:
            Memory usage in bytes, 0 if error
        """
        try:
            async with Redis(connection_pool=self._pool) as client:
                usage = await client.memory_usage(key)
                return usage if usage else 0
        except Exception as e:
            logger.error("Memory usage check failed", key=key, error=str(e))
            return 0

    async def batch_store(
        self, entries: dict[str, CacheEntry], ttl_seconds: Optional[int] = None
    ) -> int:
        """
        Store multiple cache entries in batch.

        Args:
            entries: Dictionary of key -> CacheEntry
            ttl_seconds: Time-to-live in seconds

        Returns:
            Number of entries stored successfully
        """
        if not entries:
            return 0

        try:
            async with Redis(connection_pool=self._pool) as client:
                async with client.pipeline() as pipe:
                    for key, entry in entries.items():
                        data = entry.model_dump_json()
                        if ttl_seconds:
                            pipe.setex(key, ttl_seconds, data)
                        else:
                            pipe.set(key, data)
                    results = await pipe.execute()
                    success_count = sum(1 for r in results if r)
                    logger.info("Batch store completed", count=success_count)
                    return success_count
        except Exception as e:
            logger.error("Batch store failed", error=str(e))
            return 0

    async def batch_fetch(self, keys: list[str]) -> dict[str, Optional[CacheEntry]]:
        """
        Fetch multiple cache entries in batch.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of key -> CacheEntry (None if not found)
        """
        if not keys:
            return {}

        try:
            async with Redis(connection_pool=self._pool) as client:
                values = await client.mget(keys)
                results = {}
                for key, value in zip(keys, values):
                    if value:
                        try:
                            results[key] = CacheEntry(**json.loads(value))
                        except Exception as parse_error:
                            logger.error(
                                "Entry parse failed", key=key, error=str(parse_error)
                            )
                            results[key] = None
                    else:
                        results[key] = None
                return results
        except Exception as e:
            logger.error("Batch fetch failed", error=str(e))
            return {key: None for key in keys}

    async def batch_delete(self, keys: list[str]) -> int:
        """
        Delete multiple cache entries in batch.

        Args:
            keys: List of cache keys

        Returns:
            Number of entries deleted
        """
        if not keys:
            return 0

        try:
            async with Redis(connection_pool=self._pool) as client:
                count = await client.delete(*keys)
                logger.info("Batch delete completed", count=count)
                return count
        except Exception as e:
            logger.error("Batch delete failed", error=str(e))
            return 0

    async def batch_exists(self, keys: list[str]) -> dict[str, bool]:
        """
        Check existence of multiple keys in batch.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of key -> exists status
        """
        if not keys:
            return {}

        try:
            async with Redis(connection_pool=self._pool) as client:
                async with client.pipeline() as pipe:
                    for key in keys:
                        pipe.exists(key)
                    results = await pipe.execute()
                    return {key: bool(result) for key, result in zip(keys, results)}
        except Exception as e:
            logger.error("Batch exists check failed", error=str(e))
            return {key: False for key in keys}
