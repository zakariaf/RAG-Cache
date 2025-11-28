"""Unit tests for Rate Limiting Middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.middleware.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    RateLimitMiddleware,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RateLimitConfig()

        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_size == 10
        assert config.enabled is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=500,
            enabled=False,
        )

        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 500
        assert config.enabled is False


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""

    def test_default_retry_after(self):
        """Test default retry after value."""
        exc = RateLimitExceeded()

        assert exc.status_code == 429
        assert exc.headers["Retry-After"] == "60"

    def test_custom_retry_after(self):
        """Test custom retry after value."""
        exc = RateLimitExceeded(retry_after=120)

        assert exc.headers["Retry-After"] == "120"


class TestInMemoryRateLimiter:
    """Tests for InMemoryRateLimiter."""

    @pytest.fixture
    def config(self):
        return RateLimitConfig(requests_per_minute=5, enabled=True)

    @pytest.fixture
    def limiter(self, config):
        return InMemoryRateLimiter(config)

    @pytest.fixture
    def mock_request(self):
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers.get.return_value = None
        return request

    @pytest.mark.asyncio
    async def test_first_request_allowed(self, limiter, mock_request):
        """Test first request is allowed."""
        allowed, _ = await limiter.is_allowed(mock_request)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_within_limit_allowed(self, limiter, mock_request):
        """Test requests within limit are allowed."""
        for _ in range(4):
            allowed, _ = await limiter.is_allowed(mock_request)
            assert allowed is True

    @pytest.mark.asyncio
    async def test_exceeds_limit_blocked(self, limiter, mock_request):
        """Test requests exceeding limit are blocked."""
        # Make 5 requests (the limit)
        for _ in range(5):
            await limiter.is_allowed(mock_request)

        # 6th request should be blocked
        allowed, retry_after = await limiter.is_allowed(mock_request)
        assert allowed is False
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_disabled_always_allows(self, mock_request):
        """Test disabled rate limiter allows all requests."""
        config = RateLimitConfig(enabled=False)
        limiter = InMemoryRateLimiter(config)

        for _ in range(100):
            allowed, _ = await limiter.is_allowed(mock_request)
            assert allowed is True

    def test_get_remaining(self, limiter, mock_request):
        """Test get_remaining returns correct count."""
        remaining = limiter.get_remaining(mock_request)
        assert remaining == 5  # No requests yet

    @pytest.mark.asyncio
    async def test_get_remaining_after_requests(self, limiter, mock_request):
        """Test get_remaining decreases after requests."""
        await limiter.is_allowed(mock_request)
        await limiter.is_allowed(mock_request)

        remaining = limiter.get_remaining(mock_request)
        assert remaining == 3

    def test_client_key_from_host(self, limiter, mock_request):
        """Test client key extraction from host."""
        key = limiter._get_client_key(mock_request)
        assert key == "127.0.0.1"

    def test_client_key_from_forwarded_header(self, limiter, mock_request):
        """Test client key extraction from X-Forwarded-For."""
        mock_request.headers.get.return_value = "10.0.0.1, 10.0.0.2"

        key = limiter._get_client_key(mock_request)
        assert key == "10.0.0.1"


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def mock_app(self):
        return MagicMock()

    @pytest.fixture
    def mock_request(self):
        request = MagicMock()
        request.url.path = "/api/v1/query"
        request.client.host = "127.0.0.1"
        request.headers.get.return_value = None
        return request

    @pytest.fixture
    def mock_call_next(self):
        async def call_next(request):
            response = MagicMock()
            response.headers = {}
            return response

        return call_next

    @pytest.mark.asyncio
    async def test_adds_rate_limit_headers(
        self, mock_app, mock_request, mock_call_next
    ):
        """Test middleware adds rate limit headers."""
        config = RateLimitConfig(requests_per_minute=60)
        middleware = RateLimitMiddleware(mock_app, config=config)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_skips_health_endpoints(self, mock_app, mock_request, mock_call_next):
        """Test middleware skips health check endpoints."""
        mock_request.url.path = "/health"
        config = RateLimitConfig(requests_per_minute=1)
        middleware = RateLimitMiddleware(mock_app, config=config)

        # Should not raise even with very low limit
        for _ in range(10):
            await middleware.dispatch(mock_request, mock_call_next)

    @pytest.mark.asyncio
    async def test_raises_on_limit_exceeded(
        self, mock_app, mock_request, mock_call_next
    ):
        """Test middleware raises exception when limit exceeded."""
        config = RateLimitConfig(requests_per_minute=1)
        middleware = RateLimitMiddleware(mock_app, config=config)

        # First request succeeds
        await middleware.dispatch(mock_request, mock_call_next)

        # Second request fails
        with pytest.raises(RateLimitExceeded):
            await middleware.dispatch(mock_request, mock_call_next)
