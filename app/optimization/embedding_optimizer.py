"""
Embedding generation optimization.

Sandi Metz Principles:
- Single Responsibility: Embedding optimization
- Small methods: Each optimization isolated
- Configurable: Flexible batch settings
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class EmbeddingConfig:
    """Embedding optimization configuration."""

    # Batching
    batch_size: int = 32
    max_batch_wait_ms: int = 50

    # Caching
    enable_embedding_cache: bool = True
    cache_ttl_seconds: int = 3600

    # Performance
    max_concurrent_batches: int = 4
    timeout_seconds: float = 30.0


@dataclass
class BatchRequest:
    """A request waiting for batch processing."""

    text: str
    future: asyncio.Future
    timestamp: float = field(default_factory=time.time)


class BatchEmbeddingProcessor:
    """
    Batches embedding requests for efficient processing.

    Collects requests and processes them in batches.
    """

    def __init__(
        self,
        embed_fn: Callable[[List[str]], List[List[float]]],
        config: Optional[EmbeddingConfig] = None
    ):
        """
        Initialize processor.

        Args:
            embed_fn: Function to generate embeddings for a batch
            config: Embedding configuration
        """
        self._embed_fn = embed_fn
        self._config = config or EmbeddingConfig()
        self._pending_requests: List[BatchRequest] = []
        self._lock = asyncio.Lock()
        self._processing = False
        self._stats = {
            "total_requests": 0,
            "batches_processed": 0,
            "total_texts": 0,
            "avg_batch_size": 0.0,
        }

    async def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text, using batching.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        self._stats["total_requests"] += 1

        # Create future for this request
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()

        request = BatchRequest(text=text, future=future)

        async with self._lock:
            self._pending_requests.append(request)

            # Start processing if we have a full batch
            if len(self._pending_requests) >= self._config.batch_size:
                asyncio.create_task(self._process_batch())
            elif len(self._pending_requests) == 1:
                # Start timer for partial batch
                asyncio.create_task(self._wait_and_process())

        # Wait for result
        try:
            result = await asyncio.wait_for(
                future,
                timeout=self._config.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            logger.error("Embedding request timeout")
            raise

    async def _wait_and_process(self) -> None:
        """Wait for batch timeout then process."""
        await asyncio.sleep(self._config.max_batch_wait_ms / 1000)

        async with self._lock:
            if self._pending_requests and not self._processing:
                await self._process_batch_internal()

    async def _process_batch(self) -> None:
        """Process pending batch."""
        async with self._lock:
            if not self._processing:
                await self._process_batch_internal()

    async def _process_batch_internal(self) -> None:
        """Internal batch processing."""
        if not self._pending_requests:
            return

        self._processing = True

        try:
            # Get batch of requests
            batch = self._pending_requests[:self._config.batch_size]
            self._pending_requests = self._pending_requests[self._config.batch_size:]

            # Extract texts
            texts = [req.text for req in batch]

            # Generate embeddings
            try:
                embeddings = await asyncio.to_thread(self._embed_fn, texts)

                # Resolve futures
                for req, embedding in zip(batch, embeddings):
                    if not req.future.done():
                        req.future.set_result(embedding)

                # Update stats
                self._stats["batches_processed"] += 1
                self._stats["total_texts"] += len(texts)
                self._stats["avg_batch_size"] = (
                    self._stats["total_texts"] / self._stats["batches_processed"]
                )

            except Exception as e:
                # Reject all futures on error
                for req in batch:
                    if not req.future.done():
                        req.future.set_exception(e)
                raise

        finally:
            self._processing = False

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self._stats.copy()


class EmbeddingOptimizer:
    """
    Optimizes embedding generation with caching and batching.

    Combines multiple optimization strategies.
    """

    def __init__(
        self,
        embed_fn: Callable[[str], List[float]],
        cache: Optional[Any] = None,
        config: Optional[EmbeddingConfig] = None
    ):
        """
        Initialize optimizer.

        Args:
            embed_fn: Function to generate single embedding
            cache: Optional cache for embeddings
            config: Configuration
        """
        self._embed_fn = embed_fn
        self._cache = cache
        self._config = config or EmbeddingConfig()
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "embeddings_generated": 0,
        }

    async def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding with caching.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Check cache first
        if self._config.enable_embedding_cache and self._cache:
            cached = await self._cache.get(text)
            if cached:
                self._stats["cache_hits"] += 1
                return cached

        self._stats["cache_misses"] += 1

        # Generate embedding
        embedding = await asyncio.to_thread(self._embed_fn, text)
        self._stats["embeddings_generated"] += 1

        # Store in cache
        if self._config.enable_embedding_cache and self._cache:
            await self._cache.set(
                text,
                embedding,
                ttl=self._config.cache_ttl_seconds
            )

        return embedding

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts.

        Args:
            texts: List of texts

        Returns:
            List of embeddings
        """
        results = []
        uncached_texts = []
        uncached_indices = []

        # Check cache for all texts
        if self._config.enable_embedding_cache and self._cache:
            for i, text in enumerate(texts):
                cached = await self._cache.get(text)
                if cached:
                    results.append((i, cached))
                    self._stats["cache_hits"] += 1
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
                    self._stats["cache_misses"] += 1
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))

        # Generate embeddings for uncached texts
        if uncached_texts:
            embeddings = await asyncio.to_thread(
                lambda: [self._embed_fn(t) for t in uncached_texts]
            )
            self._stats["embeddings_generated"] += len(embeddings)

            # Cache results
            if self._config.enable_embedding_cache and self._cache:
                for text, embedding in zip(uncached_texts, embeddings):
                    await self._cache.set(
                        text,
                        embedding,
                        ttl=self._config.cache_ttl_seconds
                    )

            # Add to results
            for i, embedding in zip(uncached_indices, embeddings):
                results.append((i, embedding))

        # Sort by original index and extract embeddings
        results.sort(key=lambda x: x[0])
        return [emb for _, emb in results]

    @property
    def cache_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._stats["cache_hits"] + self._stats["cache_misses"]
        if total == 0:
            return 0.0
        return self._stats["cache_hits"] / total

    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        return {
            **self._stats,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
        }

