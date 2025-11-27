"""
Query Deduplication.

Prevents duplicate query processing within a time window.

Sandi Metz Principles:
- Single Responsibility: Query deduplication
- Thread-safe: Async-safe operations
- Memory-bounded: Configurable limits
"""

import asyncio
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, Optional, Any

from app.models.response import QueryResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PendingQuery:
    """A query currently being processed."""

    query_hash: str
    created_at: float
    future: asyncio.Future


@dataclass
class DeduplicationStats:
    """Statistics for deduplication."""

    total_queries: int = 0
    deduplicated: int = 0
    unique: int = 0

    @property
    def dedup_rate(self) -> float:
        """Get deduplication rate."""
        if self.total_queries == 0:
            return 0.0
        return self.deduplicated / self.total_queries


class QueryDeduplicator:
    """
    Deduplicates concurrent identical queries.

    If same query is submitted while processing, returns same result.
    """

    def __init__(
        self,
        window_seconds: float = 5.0,
        max_pending: int = 1000,
    ):
        """
        Initialize deduplicator.

        Args:
            window_seconds: Time window for deduplication
            max_pending: Maximum pending queries
        """
        self._window = window_seconds
        self._max_pending = max_pending
        self._pending: Dict[str, PendingQuery] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = DeduplicationStats()

    async def get_or_create(
        self, query: str
    ) -> tuple[bool, asyncio.Future]:
        """
        Get existing pending query or create new.

        Args:
            query: Query string

        Returns:
            Tuple of (is_duplicate, future)
        """
        query_hash = self._hash_query(query)

        async with self._lock:
            self._stats.total_queries += 1

            # Cleanup old entries
            await self._cleanup_expired()

            # Check for existing
            if query_hash in self._pending:
                pending = self._pending[query_hash]
                if time.time() - pending.created_at < self._window:
                    self._stats.deduplicated += 1
                    logger.debug("Query deduplicated", query_hash=query_hash[:8])
                    return (True, pending.future)

            # Create new pending query
            self._stats.unique += 1
            future: asyncio.Future = asyncio.get_event_loop().create_future()
            self._pending[query_hash] = PendingQuery(
                query_hash=query_hash,
                created_at=time.time(),
                future=future,
            )

            # Enforce max pending
            while len(self._pending) > self._max_pending:
                oldest = next(iter(self._pending))
                del self._pending[oldest]

            return (False, future)

    async def complete(
        self, query: str, result: Optional[QueryResponse] = None, error: Optional[Exception] = None
    ):
        """
        Complete a pending query.

        Args:
            query: Query string
            result: Query result
            error: Error if failed
        """
        query_hash = self._hash_query(query)

        async with self._lock:
            if query_hash in self._pending:
                pending = self._pending[query_hash]

                if error:
                    pending.future.set_exception(error)
                else:
                    pending.future.set_result(result)

                del self._pending[query_hash]

    async def _cleanup_expired(self):
        """Remove expired pending queries."""
        current_time = time.time()
        expired = [
            h
            for h, p in self._pending.items()
            if current_time - p.created_at >= self._window
        ]

        for query_hash in expired:
            pending = self._pending[query_hash]
            if not pending.future.done():
                pending.future.cancel()
            del self._pending[query_hash]

    @staticmethod
    def _hash_query(query: str) -> str:
        """Generate hash for query."""
        return hashlib.sha256(query.encode()).hexdigest()

    @property
    def pending_count(self) -> int:
        """Get number of pending queries."""
        return len(self._pending)

    @property
    def stats(self) -> DeduplicationStats:
        """Get deduplication statistics."""
        return self._stats

    def reset_stats(self):
        """Reset statistics."""
        self._stats = DeduplicationStats()


class DeduplicatingProcessor:
    """
    Query processor with deduplication.

    Wraps a query service with deduplication.
    """

    def __init__(
        self,
        query_service,
        window_seconds: float = 5.0,
    ):
        """
        Initialize processor.

        Args:
            query_service: Underlying query service
            window_seconds: Deduplication window
        """
        self._service = query_service
        self._dedup = QueryDeduplicator(window_seconds=window_seconds)

    async def process(self, request) -> QueryResponse:
        """
        Process query with deduplication.

        Args:
            request: Query request

        Returns:
            Query response
        """
        is_dup, future = await self._dedup.get_or_create(request.query)

        if is_dup:
            # Wait for original to complete
            logger.debug("Waiting for duplicate result")
            return await future

        # Process original query
        try:
            result = await self._service.process(request)
            await self._dedup.complete(request.query, result=result)
            return result
        except Exception as e:
            await self._dedup.complete(request.query, error=e)
            raise

    @property
    def stats(self) -> DeduplicationStats:
        """Get deduplication stats."""
        return self._dedup.stats

