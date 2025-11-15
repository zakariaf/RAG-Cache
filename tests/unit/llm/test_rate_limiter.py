"""
Tests for rate limiter.
"""

import asyncio
from time import time

import pytest

from app.llm.rate_limiter import RateLimiter, RateLimitConfig


class TestRateLimiter:
    """Test rate limiter functionality."""

    @pytest.fixture
    def config(self) -> RateLimitConfig:
        """Create test rate limit config."""
        return RateLimitConfig(requests_per_minute=60)

    @pytest.fixture
    def rate_limiter(self, config: RateLimitConfig) -> RateLimiter:
        """Create rate limiter instance."""
        return RateLimiter(config)

    @pytest.mark.asyncio
    async def test_acquire_allows_request(self, rate_limiter: RateLimiter) -> None:
        """Test that acquire allows requests under limit."""
        # Should not raise and should complete quickly
        start = time()
        await rate_limiter.acquire()
        elapsed = time() - start
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_multiple_requests_under_limit(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test multiple requests under rate limit."""
        # Make 5 requests (well under 60 RPM limit)
        for _ in range(5):
            await rate_limiter.acquire()

        # All should complete quickly
        assert rate_limiter.get_remaining_requests() > 50

    @pytest.mark.asyncio
    async def test_get_remaining_requests(self, rate_limiter: RateLimiter) -> None:
        """Test remaining requests calculation."""
        initial = rate_limiter.get_remaining_requests()
        assert initial == 60

        await rate_limiter.acquire()
        assert rate_limiter.get_remaining_requests() == 59

        await rate_limiter.acquire()
        assert rate_limiter.get_remaining_requests() == 58

    @pytest.mark.asyncio
    async def test_cleanup_old_requests(self) -> None:
        """Test that old requests are cleaned up."""
        config = RateLimitConfig(requests_per_minute=60)
        limiter = RateLimiter(config)

        # Make a request
        await limiter.acquire()
        assert limiter.get_remaining_requests() == 59

        # Manually set old timestamp to simulate time passing
        limiter._requests[0] = time() - 61  # 61 seconds ago

        # Should be cleaned up
        assert limiter.get_remaining_requests() == 60

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_when_exceeded(self) -> None:
        """Test that rate limiter blocks when limit exceeded."""
        # Very low limit for testing
        config = RateLimitConfig(requests_per_minute=2)
        limiter = RateLimiter(config)

        # First two requests should be fast
        await limiter.acquire()
        await limiter.acquire()

        # Third request should block
        start = time()
        await limiter.acquire()
        elapsed = time() - start

        # Should have waited close to 60 seconds
        # (or at least a significant amount of time)
        assert elapsed > 0.5  # At least some delay

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, rate_limiter: RateLimiter) -> None:
        """Test concurrent request handling."""
        # Launch multiple concurrent requests
        tasks = [rate_limiter.acquire() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Should have processed all requests
        assert rate_limiter.get_remaining_requests() == 50

    def test_calculate_wait_time_no_requests(self, rate_limiter: RateLimiter) -> None:
        """Test wait time calculation with no requests."""
        wait_time = rate_limiter._calculate_wait_time()
        assert wait_time == 0.0

    def test_calculate_wait_time_with_requests(self, rate_limiter: RateLimiter) -> None:
        """Test wait time calculation with existing requests."""
        # Add old request
        rate_limiter._requests.append(time() - 30)  # 30 seconds ago

        wait_time = rate_limiter._calculate_wait_time()
        # Should wait approximately 30 more seconds
        assert 29 < wait_time < 31
