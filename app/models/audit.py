"""
Audit logging models.

Sandi Metz Principles:
- Small classes with clear purpose
- Immutable audit records
- Clear naming conventions
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """Audit event types."""

    QUERY = "query"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_WRITE = "cache_write"
    CACHE_CLEAR = "cache_clear"
    ERROR = "error"
    RATE_LIMIT = "rate_limit"
    HEALTH_CHECK = "health_check"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"


class AuditLogEntry(BaseModel):
    """Audit log entry for tracking API usage and events."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp (UTC)",
    )
    event_type: EventType = Field(..., description="Type of event")
    request_id: str = Field(..., description="Unique request identifier")
    user_id: Optional[str] = Field(
        None, description="User identifier (if authenticated)"
    )
    query_hash: Optional[str] = Field(None, description="Query hash (for query events)")
    provider: Optional[str] = Field(None, description="LLM provider used")
    latency_ms: float = Field(
        ..., ge=0.0, description="Request latency in milliseconds"
    )
    success: bool = Field(..., description="Whether the operation succeeded")
    error_code: Optional[str] = Field(None, description="Error code (if failed)")
    error_message: Optional[str] = Field(None, description="Error message (if failed)")

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, v: str) -> str:
        """Validate request ID is not empty."""
        if not v or v.strip() == "":
            raise ValueError("Request ID cannot be empty")
        return v.strip()

    @classmethod
    def query_event(
        cls,
        request_id: str,
        query_hash: str,
        provider: str,
        latency_ms: float,
        success: bool = True,
        user_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> "AuditLogEntry":
        """
        Create query event log entry.

        Args:
            request_id: Unique request identifier
            query_hash: Hash of the query
            provider: LLM provider
            latency_ms: Request latency
            success: Whether query succeeded
            user_id: User identifier
            error_code: Error code if failed
            error_message: Error message if failed

        Returns:
            AuditLogEntry instance
        """
        return cls(
            event_type=EventType.QUERY,
            request_id=request_id,
            user_id=user_id,
            query_hash=query_hash,
            provider=provider,
            latency_ms=latency_ms,
            success=success,
            error_code=error_code,
            error_message=error_message,
        )

    @classmethod
    def cache_hit_event(
        cls,
        request_id: str,
        query_hash: str,
        latency_ms: float,
        user_id: Optional[str] = None,
    ) -> "AuditLogEntry":
        """Create cache hit event log entry."""
        return cls(
            event_type=EventType.CACHE_HIT,
            request_id=request_id,
            user_id=user_id,
            query_hash=query_hash,
            provider=None,
            latency_ms=latency_ms,
            success=True,
        )

    @classmethod
    def cache_miss_event(
        cls,
        request_id: str,
        query_hash: str,
        latency_ms: float,
        user_id: Optional[str] = None,
    ) -> "AuditLogEntry":
        """Create cache miss event log entry."""
        return cls(
            event_type=EventType.CACHE_MISS,
            request_id=request_id,
            user_id=user_id,
            query_hash=query_hash,
            provider=None,
            latency_ms=latency_ms,
            success=True,
        )

    @classmethod
    def error_event(
        cls,
        request_id: str,
        error_code: str,
        error_message: str,
        latency_ms: float,
        user_id: Optional[str] = None,
        query_hash: Optional[str] = None,
    ) -> "AuditLogEntry":
        """Create error event log entry."""
        return cls(
            event_type=EventType.ERROR,
            request_id=request_id,
            user_id=user_id,
            query_hash=query_hash,
            provider=None,
            latency_ms=latency_ms,
            success=False,
            error_code=error_code,
            error_message=error_message,
        )

    @classmethod
    def rate_limit_event(
        cls,
        request_id: str,
        latency_ms: float,
        user_id: Optional[str] = None,
    ) -> "AuditLogEntry":
        """Create rate limit exceeded event log entry."""
        return cls(
            event_type=EventType.RATE_LIMIT,
            request_id=request_id,
            user_id=user_id,
            query_hash=None,
            provider=None,
            latency_ms=latency_ms,
            success=False,
            error_code="RATE_LIMIT_EXCEEDED",
        )

    @classmethod
    def system_event(
        cls,
        event_type: EventType,
        request_id: str = "system",
    ) -> "AuditLogEntry":
        """
        Create system event log entry.

        Args:
            event_type: Must be SYSTEM_START or SYSTEM_STOP
            request_id: Request identifier (defaults to "system")

        Returns:
            AuditLogEntry instance

        Raises:
            ValueError: If event_type is not a system event
        """
        if event_type not in (EventType.SYSTEM_START, EventType.SYSTEM_STOP):
            raise ValueError(f"Invalid system event type: {event_type}")

        return cls(
            event_type=event_type,
            request_id=request_id,
            user_id=None,
            query_hash=None,
            provider=None,
            latency_ms=0.0,
            success=True,
        )

    @property
    def is_query_event(self) -> bool:
        """Check if this is a query event."""
        return self.event_type == EventType.QUERY

    @property
    def is_cache_event(self) -> bool:
        """Check if this is a cache-related event."""
        return self.event_type in (
            EventType.CACHE_HIT,
            EventType.CACHE_MISS,
            EventType.CACHE_WRITE,
            EventType.CACHE_CLEAR,
        )

    @property
    def is_error_event(self) -> bool:
        """Check if this is an error event."""
        return self.event_type == EventType.ERROR

    @property
    def is_system_event(self) -> bool:
        """Check if this is a system event."""
        return self.event_type in (EventType.SYSTEM_START, EventType.SYSTEM_STOP)

    @property
    def has_error(self) -> bool:
        """Check if this entry represents a failure."""
        return not self.success or self.error_code is not None


class AuditLogSummary(BaseModel):
    """Summary of audit log entries for reporting."""

    total_events: int = Field(..., ge=0, description="Total events logged")
    successful_events: int = Field(..., ge=0, description="Successful events")
    failed_events: int = Field(..., ge=0, description="Failed events")
    query_events: int = Field(..., ge=0, description="Query events")
    cache_hit_events: int = Field(..., ge=0, description="Cache hit events")
    cache_miss_events: int = Field(..., ge=0, description="Cache miss events")
    error_events: int = Field(..., ge=0, description="Error events")
    avg_latency_ms: float = Field(..., ge=0.0, description="Average latency")
    start_time: datetime = Field(..., description="Summary start time (UTC)")
    end_time: datetime = Field(..., description="Summary end time (UTC)")

    @classmethod
    def from_entries(
        cls,
        entries: list[AuditLogEntry],
        start_time: datetime,
        end_time: datetime,
    ) -> "AuditLogSummary":
        """
        Create summary from audit log entries.

        Args:
            entries: List of audit log entries
            start_time: Summary period start
            end_time: Summary period end

        Returns:
            AuditLogSummary instance
        """
        # Consolidate into single loop for efficiency
        total = len(entries)
        successful = 0
        query_events = 0
        cache_hit_events = 0
        cache_miss_events = 0
        error_events = 0
        total_latency = 0.0

        for entry in entries:
            if entry.success:
                successful += 1
            if entry.event_type == EventType.QUERY:
                query_events += 1
            elif entry.event_type == EventType.CACHE_HIT:
                cache_hit_events += 1
            elif entry.event_type == EventType.CACHE_MISS:
                cache_miss_events += 1
            elif entry.event_type == EventType.ERROR:
                error_events += 1
            total_latency += entry.latency_ms

        failed = total - successful
        avg_latency = total_latency / total if total > 0 else 0.0

        return cls(
            total_events=total,
            successful_events=successful,
            failed_events=failed,
            query_events=query_events,
            cache_hit_events=cache_hit_events,
            cache_miss_events=cache_miss_events,
            error_events=error_events,
            avg_latency_ms=round(avg_latency, 2),
            start_time=start_time,
            end_time=end_time,
        )

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage (0.0-100.0)."""
        if self.total_events == 0:
            return 0.0
        return (self.successful_events / self.total_events) * 100.0

    @property
    def cache_hit_rate(self) -> float:
        """Get cache hit rate as percentage (0.0-100.0)."""
        total_cache_events = self.cache_hit_events + self.cache_miss_events
        if total_cache_events == 0:
            return 0.0
        return (self.cache_hit_events / total_cache_events) * 100.0

    @property
    def duration_seconds(self) -> int:
        """Get summary duration in seconds."""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds())
