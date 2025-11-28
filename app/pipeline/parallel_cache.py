"""
Parallel Cache Checking.

Checks exact and semantic caches in parallel.

Sandi Metz Principles:
- Single Responsibility: Parallel cache lookups
- Performance: Concurrent operations
- First-wins: Return first successful result
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from app.cache.redis_cache import RedisCache
from app.models.cache_entry import CacheEntry
from app.pipeline.semantic_matcher import SemanticMatch, SemanticMatcher
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CacheSource(str, Enum):
    """Source of cache hit."""

    EXACT = "exact"
    SEMANTIC = "semantic"
    NONE = "none"


@dataclass
class CacheResult:
    """Result of cache lookup."""

    source: CacheSource
    exact_entry: Optional[CacheEntry] = None
    semantic_match: Optional[SemanticMatch] = None

    @property
    def is_hit(self) -> bool:
        """Check if any cache was hit."""
        return self.source != CacheSource.NONE

    @classmethod
    def miss(cls) -> "CacheResult":
        """Create cache miss result."""
        return cls(source=CacheSource.NONE)

    @classmethod
    def from_exact(cls, entry: CacheEntry) -> "CacheResult":
        """Create result from exact cache hit."""
        return cls(source=CacheSource.EXACT, exact_entry=entry)

    @classmethod
    def from_semantic(cls, match: SemanticMatch) -> "CacheResult":
        """Create result from semantic cache hit."""
        return cls(source=CacheSource.SEMANTIC, semantic_match=match)


class ParallelCacheChecker:
    """
    Checks caches in parallel.

    Returns first successful result.
    """

    def __init__(
        self,
        redis_cache: Optional[RedisCache] = None,
        semantic_matcher: Optional[SemanticMatcher] = None,
        prefer_exact: bool = True,
    ):
        """
        Initialize checker.

        Args:
            redis_cache: Redis cache for exact matching
            semantic_matcher: Semantic matcher for similarity
            prefer_exact: Prefer exact over semantic if both hit
        """
        self._redis = redis_cache
        self._semantic = semantic_matcher
        self._prefer_exact = prefer_exact

    async def check(self, query: str) -> CacheResult:
        """
        Check all caches in parallel.

        Args:
            query: Query string

        Returns:
            CacheResult with best match
        """
        tasks = []

        if self._redis:
            tasks.append(self._check_exact(query))
        if self._semantic:
            tasks.append(self._check_semantic(query))

        if not tasks:
            return CacheResult.miss()

        # Run checks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        exact_result = None
        semantic_result = None

        for result in results:
            if isinstance(result, Exception):
                logger.warning("Cache check failed", error=str(result))
                continue

            source, data = result
            if source == CacheSource.EXACT and data:
                exact_result = data
            elif source == CacheSource.SEMANTIC and data:
                semantic_result = data

        # Choose best result
        if self._prefer_exact and exact_result:
            logger.info("Parallel cache hit: exact")
            return CacheResult.from_exact(exact_result)

        if semantic_result:
            logger.info(
                "Parallel cache hit: semantic",
                score=semantic_result.similarity_score,
            )
            return CacheResult.from_semantic(semantic_result)

        if exact_result:
            logger.info("Parallel cache hit: exact (after semantic miss)")
            return CacheResult.from_exact(exact_result)

        logger.info("Parallel cache miss")
        return CacheResult.miss()

    async def _check_exact(
        self, query: str
    ) -> Tuple[CacheSource, Optional[CacheEntry]]:
        """Check exact cache."""
        try:
            entry = await self._redis.get(query)
            return (CacheSource.EXACT, entry)
        except Exception as e:
            logger.error("Exact cache check failed", error=str(e))
            return (CacheSource.EXACT, None)

    async def _check_semantic(
        self, query: str
    ) -> Tuple[CacheSource, Optional[SemanticMatch]]:
        """Check semantic cache."""
        try:
            match = await self._semantic.find_match(query)
            return (CacheSource.SEMANTIC, match)
        except Exception as e:
            logger.error("Semantic cache check failed", error=str(e))
            return (CacheSource.SEMANTIC, None)

    async def check_batch(self, queries: List[str]) -> List[CacheResult]:
        """
        Check caches for multiple queries in parallel.

        Args:
            queries: List of queries

        Returns:
            List of CacheResults
        """
        tasks = [self.check(query) for query in queries]
        return await asyncio.gather(*tasks)


async def check_caches_parallel(
    query: str,
    redis_cache: Optional[RedisCache] = None,
    semantic_matcher: Optional[SemanticMatcher] = None,
) -> CacheResult:
    """
    Convenience function to check caches in parallel.

    Args:
        query: Query string
        redis_cache: Redis cache instance
        semantic_matcher: Semantic matcher instance

    Returns:
        CacheResult
    """
    checker = ParallelCacheChecker(
        redis_cache=redis_cache,
        semantic_matcher=semantic_matcher,
    )
    return await checker.check(query)
