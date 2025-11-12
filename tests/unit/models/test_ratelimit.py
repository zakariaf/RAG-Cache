"""Test rate limiting models."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.ratelimit import RateLimitConfig, RateLimitExceeded, RateLimitInfo


class TestRateLimitInfo:
    """Test rate limit info model."""

    def test_should_create_rate_limit_info(self):
        """Test basic rate limit info creation."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        info = RateLimitInfo(
            requests_remaining=50,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )

        assert info.requests_remaining == 50
        assert info.limit == 100
        assert info.window_seconds == 60
        assert info.is_exceeded is False

    def test_should_create_with_factory_method(self):
        """Test factory method creation."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        info = RateLimitInfo.create(
            requests_remaining=75,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )

        assert info.requests_remaining == 75
        assert info.limit == 100

    def test_should_validate_remaining_not_exceed_limit(self):
        """Test validation that remaining doesn't exceed limit."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)

        with pytest.raises(ValueError, match="cannot exceed limit"):
            RateLimitInfo.create(
                requests_remaining=150,  # Exceeds limit
                reset_at=reset_at,
                limit=100,
                window_seconds=60,
            )

    def test_should_validate_remaining_not_negative(self):
        """Test validation that remaining is not negative."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)

        with pytest.raises(ValueError, match="cannot be negative"):
            RateLimitInfo.create(
                requests_remaining=-1,
                reset_at=reset_at,
                limit=100,
                window_seconds=60,
            )

    def test_should_create_from_limit_config(self):
        """Test creating from limit configuration."""
        info = RateLimitInfo.from_limit(
            limit=100,
            window_seconds=60,
            requests_used=25,
        )

        assert info.limit == 100
        assert info.requests_remaining == 75
        assert info.window_seconds == 60

    def test_should_create_from_limit_with_no_usage(self):
        """Test creating from limit with no usage."""
        info = RateLimitInfo.from_limit(limit=100, window_seconds=60)

        assert info.requests_remaining == 100
        assert info.requests_used == 0

    def test_should_handle_usage_exceeding_limit(self):
        """Test creating when usage exceeds limit."""
        info = RateLimitInfo.from_limit(
            limit=100,
            window_seconds=60,
            requests_used=150,  # More than limit
        )

        assert info.requests_remaining == 0

    def test_should_identify_exceeded_limit(self):
        """Test is_exceeded property."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)

        # Not exceeded
        info = RateLimitInfo.create(
            requests_remaining=1,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )
        assert info.is_exceeded is False

        # Exceeded
        info = RateLimitInfo.create(
            requests_remaining=0,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )
        assert info.is_exceeded is True

    def test_should_calculate_requests_used(self):
        """Test requests_used property."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        info = RateLimitInfo.create(
            requests_remaining=30,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )

        assert info.requests_used == 70

    def test_should_calculate_usage_percentage(self):
        """Test usage_percentage property."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        info = RateLimitInfo.create(
            requests_remaining=25,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )

        assert info.usage_percentage == 75.0

    def test_should_calculate_seconds_until_reset(self):
        """Test seconds_until_reset property."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=120)
        info = RateLimitInfo.create(
            requests_remaining=50,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )

        # Should be approximately 120 seconds (allow small variation)
        assert 115 <= info.seconds_until_reset <= 125

    def test_should_return_zero_if_already_reset(self):
        """Test seconds_until_reset returns 0 if already past reset time."""
        reset_at = datetime.now(timezone.utc) - timedelta(seconds=10)  # In the past
        info = RateLimitInfo.create(
            requests_remaining=0,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )

        assert info.seconds_until_reset == 0

    def test_should_create_with_request_used(self):
        """Test with_request_used method."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        info = RateLimitInfo.create(
            requests_remaining=50,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )

        new_info = info.with_request_used()

        assert new_info.requests_remaining == 49
        assert info.requests_remaining == 50  # Original unchanged

    def test_should_reject_using_request_when_exceeded(self):
        """Test that with_request_used fails when limit exceeded."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        info = RateLimitInfo.create(
            requests_remaining=0,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )

        with pytest.raises(ValueError, match="Rate limit already exceeded"):
            info.with_request_used()


class TestRateLimitExceeded:
    """Test rate limit exceeded model."""

    def test_should_create_from_info(self):
        """Test creating from rate limit info."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=120)
        info = RateLimitInfo.create(
            requests_remaining=0,
            reset_at=reset_at,
            limit=100,
            window_seconds=60,
        )

        exceeded = RateLimitExceeded.from_info(info)

        assert exceeded.limit == 100
        assert exceeded.window_seconds == 60
        assert 115 <= exceeded.retry_after <= 125

    def test_should_calculate_retry_after_minutes(self):
        """Test retry_after_minutes property."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=120)
        exceeded = RateLimitExceeded(
            retry_after=120,
            limit=100,
            window_seconds=60,
            reset_at=reset_at,
        )

        assert exceeded.retry_after_minutes == 2

    def test_should_round_up_retry_after_minutes(self):
        """Test retry_after_minutes rounds up."""
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=61)
        exceeded = RateLimitExceeded(
            retry_after=61,  # Should round up to 2 minutes
            limit=100,
            window_seconds=60,
            reset_at=reset_at,
        )

        assert exceeded.retry_after_minutes == 2

    def test_should_identify_immediate_retry(self):
        """Test is_immediate_retry property."""
        now = datetime.now(timezone.utc)

        # Can retry immediately
        exceeded = RateLimitExceeded(
            retry_after=0,
            limit=100,
            window_seconds=60,
            reset_at=now,
        )
        assert exceeded.is_immediate_retry is True

        # Must wait
        exceeded = RateLimitExceeded(
            retry_after=60,
            limit=100,
            window_seconds=60,
            reset_at=now + timedelta(seconds=60),
        )
        assert exceeded.is_immediate_retry is False


class TestRateLimitConfig:
    """Test rate limit configuration model."""

    def test_should_create_rate_limit_config(self):
        """Test basic config creation."""
        config = RateLimitConfig(
            limit=100,
            window_seconds=60,
            enabled=True,
        )

        assert config.limit == 100
        assert config.window_seconds == 60
        assert config.enabled is True

    def test_should_create_per_minute_config(self):
        """Test per-minute factory method."""
        config = RateLimitConfig.per_minute(limit=60)

        assert config.limit == 60
        assert config.window_seconds == 60
        assert config.is_per_minute is True
        assert config.enabled is True

    def test_should_create_per_hour_config(self):
        """Test per-hour factory method."""
        config = RateLimitConfig.per_hour(limit=1000)

        assert config.limit == 1000
        assert config.window_seconds == 3600
        assert config.is_per_hour is True

    def test_should_create_per_day_config(self):
        """Test per-day factory method."""
        config = RateLimitConfig.per_day(limit=10000)

        assert config.limit == 10000
        assert config.window_seconds == 86400
        assert config.is_per_day is True

    def test_should_create_disabled_config(self):
        """Test disabled factory method."""
        config = RateLimitConfig.disabled()

        assert config.enabled is False

    def test_should_calculate_window_minutes(self):
        """Test window_minutes property."""
        config = RateLimitConfig(limit=100, window_seconds=300)

        assert config.window_minutes == 5

    def test_should_calculate_window_hours(self):
        """Test window_hours property."""
        config = RateLimitConfig(limit=100, window_seconds=7200)

        assert config.window_hours == 2

    def test_should_identify_per_minute_limit(self):
        """Test is_per_minute property."""
        config = RateLimitConfig.per_minute(100)
        assert config.is_per_minute is True

        config = RateLimitConfig.per_hour(100)
        assert config.is_per_minute is False

    def test_should_identify_per_hour_limit(self):
        """Test is_per_hour property."""
        config = RateLimitConfig.per_hour(1000)
        assert config.is_per_hour is True

        config = RateLimitConfig.per_minute(100)
        assert config.is_per_hour is False

    def test_should_identify_per_day_limit(self):
        """Test is_per_day property."""
        config = RateLimitConfig.per_day(10000)
        assert config.is_per_day is True

        config = RateLimitConfig.per_hour(1000)
        assert config.is_per_day is False

    def test_should_create_disabled_per_minute(self):
        """Test creating disabled per-minute config."""
        config = RateLimitConfig.per_minute(limit=100, enabled=False)

        assert config.is_per_minute is True
        assert config.enabled is False

    def test_should_serialize_to_json(self):
        """Test serialization."""
        config = RateLimitConfig.per_minute(limit=100)

        json_data = config.model_dump()

        assert json_data["limit"] == 100
        assert json_data["window_seconds"] == 60
        assert json_data["enabled"] is True

    def test_should_deserialize_from_json(self):
        """Test deserialization."""
        data = {
            "limit": 100,
            "window_seconds": 60,
            "enabled": True,
        }

        config = RateLimitConfig.model_validate(data)

        assert config.limit == 100
        assert config.window_seconds == 60
