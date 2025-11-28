"""
Batch processing optimization.

Sandi Metz Principles:
- Single Responsibility: Batch processing
- Small methods: Each operation isolated
- Configurable: Flexible batch settings
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class BatchConfig:
    """Batch processing configuration."""

    # Batch size
    batch_size: int = 100
    min_batch_size: int = 1
    max_batch_size: int = 1000

    # Timing
    max_wait_ms: int = 100
    processing_timeout_seconds: float = 60.0

    # Concurrency
    max_concurrent_batches: int = 4

    # Error handling
    continue_on_error: bool = True
    max_retries: int = 3


@dataclass
class BatchResult(Generic[R]):
    """Result of batch processing."""

    results: List[R]
    errors: List[tuple[int, Exception]]
    total_items: int
    successful_items: int
    failed_items: int
    processing_time_ms: float

    @property
    def success_rate(self) -> float:
        """Get success rate."""
        if self.total_items == 0:
            return 0.0
        return self.successful_items / self.total_items


class BatchProcessor(Generic[T, R]):
    """
    Processes items in optimized batches.

    Collects items and processes them efficiently.
    """

    def __init__(
        self,
        process_fn: Callable[[List[T]], List[R]],
        config: Optional[BatchConfig] = None,
    ):
        """
        Initialize processor.

        Args:
            process_fn: Function to process a batch
            config: Batch configuration
        """
        self._process_fn = process_fn
        self._config = config or BatchConfig()
        self._pending: List[tuple[T, asyncio.Future]] = []
        self._lock = asyncio.Lock()
        self._processing = False
        self._semaphore = asyncio.Semaphore(self._config.max_concurrent_batches)
        self._stats = {
            "total_items": 0,
            "batches_processed": 0,
            "successful_items": 0,
            "failed_items": 0,
            "avg_batch_size": 0.0,
            "avg_processing_time_ms": 0.0,
        }

    async def process(self, item: T) -> R:
        """
        Process a single item (batched automatically).

        Args:
            item: Item to process

        Returns:
            Processing result
        """
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()

        async with self._lock:
            self._pending.append((item, future))
            self._stats["total_items"] += 1

            # Start processing if batch is full
            if len(self._pending) >= self._config.batch_size:
                asyncio.create_task(self._process_batch())
            elif len(self._pending) == 1:
                # Start timer for partial batch
                asyncio.create_task(self._wait_and_process())

        try:
            return await asyncio.wait_for(
                future, timeout=self._config.processing_timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error("Batch processing timeout")
            raise

    async def _wait_and_process(self) -> None:
        """Wait for batch timeout then process."""
        await asyncio.sleep(self._config.max_wait_ms / 1000)

        async with self._lock:
            if self._pending and not self._processing:
                asyncio.create_task(self._process_batch())

    async def _process_batch(self) -> None:
        """Process pending batch."""
        async with self._semaphore:
            async with self._lock:
                if not self._pending or self._processing:
                    return

                self._processing = True
                batch = self._pending[: self._config.batch_size]
                self._pending = self._pending[self._config.batch_size :]

            try:
                await self._process_batch_internal(batch)
            finally:
                async with self._lock:
                    self._processing = False

                    # Process remaining if any
                    if self._pending:
                        asyncio.create_task(self._process_batch())

    async def _process_batch_internal(
        self, batch: List[tuple[T, asyncio.Future]]
    ) -> None:
        """Internal batch processing."""
        if not batch:
            return

        items = [item for item, _ in batch]
        futures = [future for _, future in batch]

        start_time = time.time()

        try:
            # Process batch
            results = await asyncio.to_thread(self._process_fn, items)

            # Resolve futures
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
                    self._stats["successful_items"] += 1

            # Update stats
            processing_time = (time.time() - start_time) * 1000
            self._update_stats(len(items), processing_time)

        except Exception as e:
            if self._config.continue_on_error:
                # Reject all futures
                for future in futures:
                    if not future.done():
                        future.set_exception(e)
                        self._stats["failed_items"] += 1
            else:
                raise

    def _update_stats(self, batch_size: int, processing_time_ms: float) -> None:
        """Update processing statistics."""
        self._stats["batches_processed"] += 1
        batches = self._stats["batches_processed"]

        # Running average of batch size
        self._stats["avg_batch_size"] = (
            self._stats["avg_batch_size"] * (batches - 1) + batch_size
        ) / batches

        # Running average of processing time
        self._stats["avg_processing_time_ms"] = (
            self._stats["avg_processing_time_ms"] * (batches - 1) + processing_time_ms
        ) / batches

    async def process_many(self, items: List[T]) -> BatchResult[R]:
        """
        Process multiple items.

        Args:
            items: Items to process

        Returns:
            Batch result with all results
        """
        start_time = time.time()
        results: List[R] = []
        errors: List[tuple[int, Exception]] = []

        # Process in chunks
        for i in range(0, len(items), self._config.batch_size):
            chunk = items[i : i + self._config.batch_size]

            try:
                chunk_results = await asyncio.to_thread(self._process_fn, chunk)
                results.extend(chunk_results)
            except Exception as e:
                if self._config.continue_on_error:
                    for j in range(len(chunk)):
                        errors.append((i + j, e))
                else:
                    raise

        processing_time = (time.time() - start_time) * 1000

        return BatchResult(
            results=results,
            errors=errors,
            total_items=len(items),
            successful_items=len(results),
            failed_items=len(errors),
            processing_time_ms=processing_time,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        return {
            **self._stats,
            "pending_items": len(self._pending),
        }


class AdaptiveBatchProcessor(BatchProcessor[T, R]):
    """
    Batch processor with adaptive batch sizing.

    Adjusts batch size based on performance metrics.
    """

    def __init__(
        self,
        process_fn: Callable[[List[T]], List[R]],
        config: Optional[BatchConfig] = None,
        target_latency_ms: float = 100.0,
    ):
        """
        Initialize adaptive processor.

        Args:
            process_fn: Function to process a batch
            config: Batch configuration
            target_latency_ms: Target processing latency
        """
        super().__init__(process_fn, config)
        self._target_latency = target_latency_ms
        self._current_batch_size = config.batch_size if config else 100
        self._latency_history: List[float] = []
        self._adjustment_factor = 0.1

    def _update_stats(self, batch_size: int, processing_time_ms: float) -> None:
        """Update stats and adjust batch size."""
        super()._update_stats(batch_size, processing_time_ms)

        # Track latency
        self._latency_history.append(processing_time_ms)
        if len(self._latency_history) > 100:
            self._latency_history.pop(0)

        # Adjust batch size
        self._maybe_adjust_batch_size()

    def _maybe_adjust_batch_size(self) -> None:
        """Adjust batch size based on latency."""
        if len(self._latency_history) < 10:
            return

        avg_latency = sum(self._latency_history) / len(self._latency_history)

        if avg_latency > self._target_latency * 1.2:
            # Too slow - reduce batch size
            new_size = int(self._current_batch_size * (1 - self._adjustment_factor))
            self._current_batch_size = max(self._config.min_batch_size, new_size)
        elif avg_latency < self._target_latency * 0.8:
            # Fast enough - increase batch size
            new_size = int(self._current_batch_size * (1 + self._adjustment_factor))
            self._current_batch_size = min(self._config.max_batch_size, new_size)

    @property
    def current_batch_size(self) -> int:
        """Get current adaptive batch size."""
        return self._current_batch_size
