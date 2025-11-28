"""
Async Query Processor.

Provides async query processing capabilities.

Sandi Metz Principles:
- Single Responsibility: Async processing
- Non-blocking: Fully async operations
- Composable: Works with other pipeline components
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, TypeVar

from app.models.query import QueryRequest
from app.models.response import QueryResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class AsyncResult:
    """Result of async operation."""

    success: bool
    result: Optional[Any] = None
    error: Optional[Exception] = None
    duration_ms: float = 0.0

    @classmethod
    def ok(cls, result: Any, duration_ms: float = 0.0) -> "AsyncResult":
        """Create success result."""
        return cls(success=True, result=result, duration_ms=duration_ms)

    @classmethod
    def fail(cls, error: Exception, duration_ms: float = 0.0) -> "AsyncResult":
        """Create failure result."""
        return cls(success=False, error=error, duration_ms=duration_ms)


class AsyncQueryProcessor:
    """
    Processes queries asynchronously.

    Supports batching and concurrent execution.
    """

    def __init__(
        self,
        query_service,
        max_concurrent: int = 10,
        timeout_seconds: float = 30.0,
    ):
        """
        Initialize processor.

        Args:
            query_service: Query service instance
            max_concurrent: Maximum concurrent requests
            timeout_seconds: Request timeout
        """
        self._service = query_service
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = timeout_seconds

    async def process_single(self, request: QueryRequest) -> AsyncResult:
        """
        Process a single query asynchronously.

        Args:
            request: Query request

        Returns:
            AsyncResult with response or error
        """
        import time

        start = time.time()

        async with self._semaphore:
            try:
                response = await asyncio.wait_for(
                    self._service.process(request),
                    timeout=self._timeout,
                )
                duration = (time.time() - start) * 1000
                return AsyncResult.ok(response, duration)

            except asyncio.TimeoutError:
                duration = (time.time() - start) * 1000
                logger.error("Query timeout", query=request.query[:50])
                return AsyncResult.fail(
                    TimeoutError(f"Query timed out after {self._timeout}s"),
                    duration,
                )

            except Exception as e:
                duration = (time.time() - start) * 1000
                logger.error("Query failed", query=request.query[:50], error=str(e))
                return AsyncResult.fail(e, duration)

    async def process_batch(self, requests: List[QueryRequest]) -> List[AsyncResult]:
        """
        Process multiple queries concurrently.

        Args:
            requests: List of query requests

        Returns:
            List of AsyncResults
        """
        if not requests:
            return []

        logger.info("Processing batch", count=len(requests))

        tasks = [self.process_single(req) for req in requests]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for r in results if r.success)
        logger.info(
            "Batch complete",
            total=len(results),
            success=success_count,
            failed=len(results) - success_count,
        )

        return results

    async def process_stream(
        self,
        requests: List[QueryRequest],
        callback: Optional[Callable[[int, AsyncResult], None]] = None,
    ) -> List[AsyncResult]:
        """
        Process queries with streaming results.

        Args:
            requests: List of query requests
            callback: Optional callback for each result

        Returns:
            List of all results
        """
        results = []

        for i, request in enumerate(requests):
            result = await self.process_single(request)
            results.append(result)

            if callback:
                callback(i, result)

        return results


async def run_async(
    func: Callable[[], T],
    timeout: float = 30.0,
) -> T:
    """
    Run function with timeout.

    Args:
        func: Async function to run
        timeout: Timeout in seconds

    Returns:
        Function result

    Raises:
        TimeoutError: If function times out
    """
    return await asyncio.wait_for(func(), timeout=timeout)


async def run_with_fallback(
    primary: Callable[[], T],
    fallback: Callable[[], T],
    timeout: float = 30.0,
) -> T:
    """
    Run primary function with fallback.

    Args:
        primary: Primary async function
        fallback: Fallback async function
        timeout: Timeout for primary

    Returns:
        Result from primary or fallback
    """
    try:
        return await asyncio.wait_for(primary(), timeout=timeout)
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning("Primary failed, using fallback", error=str(e))
        return await fallback()
