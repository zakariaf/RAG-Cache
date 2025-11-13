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
from app.models.statistics import RedisMetrics
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

    async def invalidate_by_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern.

        Args:
            pattern: Key pattern (e.g., "cache:*")

        Returns:
            Number of entries invalidated
        """
        count = await self._repository.delete_by_pattern(pattern)
        logger.info("Cache invalidated by pattern", pattern=pattern, count=count)
        return count

    async def invalidate_all(self) -> bool:
        """
        Invalidate all cache entries.

        Returns:
            True if successful
        """
        success = await self._repository.clear_all()
        if success:
            logger.info("All cache entries invalidated")
        return success

    async def get_cached_queries(self, pattern: str = "*") -> list[str]:
        """
        Get list of cached query keys.

        Args:
            pattern: Key pattern to match

        Returns:
            List of cache keys
        """
        return await self._repository.get_keys_by_pattern(pattern)

    async def get_metrics(self) -> Optional[RedisMetrics]:
        """
        Collect Redis metrics.

        Returns:
            Redis metrics if successful
        """
        metrics = await self._repository.get_metrics()
        if metrics:
            logger.info("Metrics collected", total_keys=metrics.total_keys)
        return metrics

    async def get_cache_size(self) -> int:
        """
        Get total number of cached entries.

        Returns:
            Number of cache entries
        """
        return await self._repository.get_key_count()

    async def get_entry_memory(self, query: str) -> int:
        """
        Get memory usage of cached entry.

        Args:
            query: Query text

        Returns:
            Memory usage in bytes
        """
        key = generate_cache_key(query)
        return await self._repository.get_memory_usage(key)

    async def batch_set(self, entries: list[CacheEntry]) -> int:
        """
        Store multiple cache entries in batch.

        Args:
            entries: List of cache entries to store

        Returns:
            Number of entries stored successfully
        """
        if not entries:
            return 0

        entry_dict = {entry.query_hash: entry for entry in entries}
        count = await self._repository.batch_store(entry_dict, self._ttl)
        logger.info("Batch set completed", count=count)
        return count

    async def batch_get(self, queries: list[str]) -> dict[str, Optional[CacheEntry]]:
        """
        Get multiple cache entries in batch.

        Args:
            queries: List of query texts

        Returns:
            Dictionary of query -> CacheEntry (None if not found)
        """
        if not queries:
            return {}

        keys = [generate_cache_key(query) for query in queries]
        results = await self._repository.batch_fetch(keys)

        # Map back to original queries
        query_results = {}
        for query, key in zip(queries, keys):
            entry = results.get(key)
            query_results[query] = entry
            if entry:
                log_cache_hit(query, source="exact")
            else:
                log_cache_miss(query)

        return query_results

    async def batch_delete(self, queries: list[str]) -> int:
        """
        Delete multiple cache entries in batch.

        Args:
            queries: List of query texts

        Returns:
            Number of entries deleted
        """
        if not queries:
            return 0

        keys = [generate_cache_key(query) for query in queries]
        count = await self._repository.batch_delete(keys)
        logger.info("Batch delete completed", count=count)
        return count

    async def batch_exists(self, queries: list[str]) -> dict[str, bool]:
        """
        Check existence of multiple queries in batch.

        Args:
            queries: List of query texts

        Returns:
            Dictionary of query -> exists status
        """
        if not queries:
            return {}

        keys = [generate_cache_key(query) for query in queries]
        results = await self._repository.batch_exists(keys)

        # Map back to original queries
        return {query: results[key] for query, key in zip(queries, keys)}
