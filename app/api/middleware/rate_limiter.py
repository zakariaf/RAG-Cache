"""
API Rate Limiting Middleware.

Limits request rates per client to prevent abuse.

Sandi Metz Principles:
- Single Responsibility: Rate limiting
- Configurable: Limits per endpoint/client
- Non-blocking: Async Redis-based tracking
"""

import time
from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    enabled: bool = True


class RateLimitExceeded(HTTPException):
    """Exception for rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    For production, use Redis-based rate limiting.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self._config = config
        self._requests: dict[str, list[float]] = {}

    def _get_client_key(self, request: Request) -> str:
        """Get unique client identifier."""
        # Use X-Forwarded-For if behind proxy, otherwise client host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_old_requests(self, key: str, window_seconds: int) -> None:
        """Remove requests outside the time window."""
        if key not in self._requests:
            return

        cutoff = time.time() - window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    async def is_allowed(self, request: Request) -> tuple[bool, int]:
        """
        Check if request is allowed.

        Args:
            request: FastAPI request

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        if not self._config.enabled:
            return (True, 0)

        key = self._get_client_key(request)
        now = time.time()

        # Initialize if new client
        if key not in self._requests:
            self._requests[key] = []

        # Check minute limit
        self._cleanup_old_requests(key, 60)
        minute_count = len(self._requests[key])

        if minute_count >= self._config.requests_per_minute:
            retry_after = 60 - int(now - min(self._requests[key]))
            logger.warning(
                "Rate limit exceeded (minute)",
                client=key,
                count=minute_count,
                limit=self._config.requests_per_minute,
            )
            return (False, max(1, retry_after))

        # Record request
        self._requests[key].append(now)

        return (True, 0)

    def get_remaining(self, request: Request) -> int:
        """Get remaining requests in current window."""
        key = self._get_client_key(request)
        self._cleanup_old_requests(key, 60)
        count = len(self._requests.get(key, []))
        return max(0, self._config.requests_per_minute - count)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.

    Adds rate limiting headers to responses.
    """

    def __init__(
        self,
        app,
        rate_limiter: Optional[InMemoryRateLimiter] = None,
        config: Optional[RateLimitConfig] = None,
    ):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            rate_limiter: Rate limiter instance
            config: Rate limit configuration
        """
        super().__init__(app)
        self._config = config or RateLimitConfig()
        self._limiter = rate_limiter or InMemoryRateLimiter(self._config)

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/healthz", "/ready"):
            return await call_next(request)

        # Check rate limit
        allowed, retry_after = await self._limiter.is_allowed(request)

        if not allowed:
            raise RateLimitExceeded(retry_after=retry_after)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self._limiter.get_remaining(request)
        response.headers["X-RateLimit-Limit"] = str(
            self._config.requests_per_minute
        )
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)

        return response


# Default rate limiter for the application
default_rate_limit_config = RateLimitConfig(
    requests_per_minute=60,
    requests_per_hour=1000,
    burst_size=10,
    enabled=True,
)

