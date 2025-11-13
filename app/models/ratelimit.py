"""
Rate limiting models.

Sandi Metz Principles:
- Small classes with clear purpose
- Immutable rate limit data
- Clear naming conventions
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class RateLimitInfo(BaseModel):
    """Rate limit information for API responses."""

    requests_remaining: int = Field(
        ..., ge=0, description="Requests remaining in window"
    )
    reset_at: datetime = Field(..., description="When the limit resets (UTC)")
    limit: int = Field(..., ge=1, description="Total requests allowed per window")
    window_seconds: int = Field(..., ge=1, description="Time window in seconds")

    @model_validator(mode="after")
    def validate_requests_remaining(self) -> "RateLimitInfo":
        """Validate requests_remaining doesn't exceed limit."""
        if self.requests_remaining > self.limit:
            raise ValueError(
                f"requests_remaining ({self.requests_remaining}) cannot exceed "
                f"limit ({self.limit})"
            )
        return self

    @classmethod
    def create(
        cls,
        requests_remaining: int,
        reset_at: datetime,
        limit: int,
        window_seconds: int,
    ) -> "RateLimitInfo":
        """
        Create rate limit info with validation.

        Args:
            requests_remaining: Requests remaining
            reset_at: Reset timestamp
            limit: Request limit
            window_seconds: Time window

        Returns:
            RateLimitInfo instance

        Raises:
            ValueError: If validation fails (via model_validator)
        """
        # Validation happens in model_validator
        return cls(
            requests_remaining=requests_remaining,
            reset_at=reset_at,
            limit=limit,
            window_seconds=window_seconds,
        )

    @classmethod
    def from_limit(
        cls,
        limit: int,
        window_seconds: int,
        requests_used: int = 0,
        start_time: Optional[datetime] = None,
    ) -> "RateLimitInfo":
        """
        Create rate limit info from limit configuration.

        Args:
            limit: Request limit
            window_seconds: Time window in seconds
            requests_used: Requests already used
            start_time: Window start time (defaults to now)

        Returns:
            RateLimitInfo instance
        """
        if start_time is None:
            start_time = datetime.now(timezone.utc)

        reset_at = start_time + timedelta(seconds=window_seconds)
        requests_remaining = max(0, limit - requests_used)

        return cls.create(
            requests_remaining=requests_remaining,
            reset_at=reset_at,
            limit=limit,
            window_seconds=window_seconds,
        )

    @property
    def is_exceeded(self) -> bool:
        """Check if rate limit is exceeded."""
        return self.requests_remaining == 0

    @property
    def requests_used(self) -> int:
        """Get number of requests used."""
        return self.limit - self.requests_remaining

    @property
    def usage_percentage(self) -> float:
        """Get usage as percentage (0.0-100.0)."""
        return (self.requests_used / self.limit) * 100.0

    @property
    def seconds_until_reset(self) -> int:
        """
        Get seconds until reset.

        Returns:
            Seconds until reset (0 if already reset)
        """
        now = datetime.now(timezone.utc)
        if now >= self.reset_at:
            return 0

        delta = self.reset_at - now
        return int(delta.total_seconds())

    def with_request_used(self) -> "RateLimitInfo":
        """
        Create new info with one request used.

        Returns:
            New RateLimitInfo with decremented remaining

        Raises:
            ValueError: If no requests remaining
        """
        if self.is_exceeded:
            raise ValueError("Rate limit already exceeded, cannot use request")

        return self.model_copy(
            update={"requests_remaining": self.requests_remaining - 1}
        )


class RateLimitExceeded(BaseModel):
    """Rate limit exceeded error details."""

    retry_after: int = Field(..., ge=0, description="Seconds to wait before retry")
    limit: int = Field(..., ge=1, description="Request limit per window")
    window_seconds: int = Field(..., ge=1, description="Time window in seconds")
    reset_at: datetime = Field(..., description="When the limit resets (UTC)")

    @classmethod
    def from_info(cls, info: RateLimitInfo) -> "RateLimitExceeded":
        """
        Create from rate limit info.

        Args:
            info: Rate limit info

        Returns:
            RateLimitExceeded instance
        """
        return cls(
            retry_after=info.seconds_until_reset,
            limit=info.limit,
            window_seconds=info.window_seconds,
            reset_at=info.reset_at,
        )

    @property
    def retry_after_minutes(self) -> int:
        """Get retry_after in minutes (rounded up)."""
        return (self.retry_after + 59) // 60  # Round up

    @property
    def is_immediate_retry(self) -> bool:
        """Check if retry can be immediate (reset already happened)."""
        return self.retry_after == 0


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    limit: int = Field(..., ge=1, description="Requests allowed per window")
    window_seconds: int = Field(..., ge=1, description="Time window in seconds")
    enabled: bool = Field(default=True, description="Whether rate limiting is enabled")

    @classmethod
    def per_minute(cls, limit: int, enabled: bool = True) -> "RateLimitConfig":
        """Create per-minute rate limit."""
        return cls(limit=limit, window_seconds=60, enabled=enabled)

    @classmethod
    def per_hour(cls, limit: int, enabled: bool = True) -> "RateLimitConfig":
        """Create per-hour rate limit."""
        return cls(limit=limit, window_seconds=3600, enabled=enabled)

    @classmethod
    def per_day(cls, limit: int, enabled: bool = True) -> "RateLimitConfig":
        """Create per-day rate limit."""
        return cls(limit=limit, window_seconds=86400, enabled=enabled)

    @classmethod
    def disabled(cls) -> "RateLimitConfig":
        """Create disabled rate limit config."""
        return cls(limit=1, window_seconds=1, enabled=False)

    @property
    def window_minutes(self) -> int:
        """Get window size in minutes."""
        return self.window_seconds // 60

    @property
    def window_hours(self) -> int:
        """Get window size in hours."""
        return self.window_seconds // 3600

    @property
    def is_per_minute(self) -> bool:
        """Check if this is a per-minute limit."""
        return self.window_seconds == 60

    @property
    def is_per_hour(self) -> bool:
        """Check if this is a per-hour limit."""
        return self.window_seconds == 3600

    @property
    def is_per_day(self) -> bool:
        """Check if this is a per-day limit."""
        return self.window_seconds == 86400
