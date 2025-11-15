"""
Rate limiting for LLM providers.

Sandi Metz Principles:
- Single Responsibility: Manage rate limits
- Small methods: Each method < 10 lines
- Dependency Injection: Configuration injected
"""

import asyncio
from collections import deque
from dataclasses import dataclass
from time import time
from typing import Deque

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_minute: int
    tokens_per_minute: int | None = None


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Tracks requests and enforces rate limits.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self._config = config
        self._requests: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission to make request.

        Blocks until rate limit allows request.
        """
        async with self._lock:
            await self._wait_if_needed()
            self._record_request()

    async def _wait_if_needed(self) -> None:
        """Wait if rate limit is exceeded."""
        self._cleanup_old_requests()

        if len(self._requests) >= self._config.requests_per_minute:
            wait_time = self._calculate_wait_time()
            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            self._cleanup_old_requests()

    def _cleanup_old_requests(self) -> None:
        """Remove requests older than 1 minute."""
        cutoff = time() - 60
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

    def _calculate_wait_time(self) -> float:
        """
        Calculate time to wait before next request.

        Returns:
            Wait time in seconds
        """
        if not self._requests:
            return 0.0
        oldest = self._requests[0]
        elapsed = time() - oldest
        return max(0, 60 - elapsed)

    def _record_request(self) -> None:
        """Record current request timestamp."""
        self._requests.append(time())

    def get_remaining_requests(self) -> int:
        """
        Get remaining requests in current window.

        Returns:
            Number of remaining requests
        """
        self._cleanup_old_requests()
        return max(0, self._config.requests_per_minute - len(self._requests))
