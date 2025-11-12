"""Test audit logging models."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.audit import AuditLogEntry, AuditLogSummary, EventType


class TestEventType:
    """Test event type enum."""

    def test_should_have_all_event_types(self):
        """Test all event types exist."""
        assert EventType.QUERY == "query"
        assert EventType.CACHE_HIT == "cache_hit"
        assert EventType.CACHE_MISS == "cache_miss"
        assert EventType.CACHE_WRITE == "cache_write"
        assert EventType.CACHE_CLEAR == "cache_clear"
        assert EventType.ERROR == "error"
        assert EventType.RATE_LIMIT == "rate_limit"
        assert EventType.HEALTH_CHECK == "health_check"
        assert EventType.SYSTEM_START == "system_start"
        assert EventType.SYSTEM_STOP == "system_stop"


class TestAuditLogEntry:
    """Test audit log entry model."""

    def test_should_create_audit_log_entry(self):
        """Test basic audit log entry creation."""
        entry = AuditLogEntry(
            event_type=EventType.QUERY,
            request_id="req-123",
            user_id="user-1",
            query_hash="hash-abc",
            provider="openai",
            latency_ms=150.5,
            success=True,
        )

        assert entry.event_type == EventType.QUERY
        assert entry.request_id == "req-123"
        assert entry.user_id == "user-1"
        assert entry.query_hash == "hash-abc"
        assert entry.provider == "openai"
        assert entry.latency_ms == 150.5
        assert entry.success is True
        assert isinstance(entry.timestamp, datetime)

    def test_should_validate_empty_request_id(self):
        """Test validation of empty request ID."""
        with pytest.raises(ValueError, match="Request ID cannot be empty"):
            AuditLogEntry(
                event_type=EventType.QUERY,
                request_id="",
                latency_ms=100.0,
                success=True,
            )

    def test_should_create_query_event(self):
        """Test query event factory method."""
        entry = AuditLogEntry.query_event(
            request_id="req-123",
            query_hash="hash-abc",
            provider="openai",
            latency_ms=150.0,
        )

        assert entry.event_type == EventType.QUERY
        assert entry.request_id == "req-123"
        assert entry.query_hash == "hash-abc"
        assert entry.provider == "openai"
        assert entry.success is True

    def test_should_create_failed_query_event(self):
        """Test failed query event."""
        entry = AuditLogEntry.query_event(
            request_id="req-123",
            query_hash="hash-abc",
            provider="openai",
            latency_ms=150.0,
            success=False,
            error_code="LLM_ERROR",
            error_message="Timeout",
        )

        assert entry.success is False
        assert entry.error_code == "LLM_ERROR"
        assert entry.error_message == "Timeout"

    def test_should_create_cache_hit_event(self):
        """Test cache hit event factory method."""
        entry = AuditLogEntry.cache_hit_event(
            request_id="req-123",
            query_hash="hash-abc",
            latency_ms=10.0,
        )

        assert entry.event_type == EventType.CACHE_HIT
        assert entry.query_hash == "hash-abc"
        assert entry.success is True
        assert entry.latency_ms == 10.0

    def test_should_create_cache_miss_event(self):
        """Test cache miss event factory method."""
        entry = AuditLogEntry.cache_miss_event(
            request_id="req-123",
            query_hash="hash-abc",
            latency_ms=5.0,
        )

        assert entry.event_type == EventType.CACHE_MISS
        assert entry.query_hash == "hash-abc"
        assert entry.success is True

    def test_should_create_error_event(self):
        """Test error event factory method."""
        entry = AuditLogEntry.error_event(
            request_id="req-123",
            error_code="INVALID_QUERY",
            error_message="Query is empty",
            latency_ms=2.0,
        )

        assert entry.event_type == EventType.ERROR
        assert entry.error_code == "INVALID_QUERY"
        assert entry.error_message == "Query is empty"
        assert entry.success is False

    def test_should_create_rate_limit_event(self):
        """Test rate limit event factory method."""
        entry = AuditLogEntry.rate_limit_event(
            request_id="req-123",
            latency_ms=1.0,
            user_id="user-1",
        )

        assert entry.event_type == EventType.RATE_LIMIT
        assert entry.user_id == "user-1"
        assert entry.success is False
        assert entry.error_code == "RATE_LIMIT_EXCEEDED"

    def test_should_create_system_start_event(self):
        """Test system start event factory method."""
        entry = AuditLogEntry.system_event(EventType.SYSTEM_START)

        assert entry.event_type == EventType.SYSTEM_START
        assert entry.request_id == "system"
        assert entry.success is True

    def test_should_create_system_stop_event(self):
        """Test system stop event factory method."""
        entry = AuditLogEntry.system_event(EventType.SYSTEM_STOP)

        assert entry.event_type == EventType.SYSTEM_STOP
        assert entry.success is True

    def test_should_reject_invalid_system_event_type(self):
        """Test validation of system event type."""
        with pytest.raises(ValueError, match="Invalid system event type"):
            AuditLogEntry.system_event(EventType.QUERY)

    def test_should_identify_query_event(self):
        """Test is_query_event property."""
        entry = AuditLogEntry.query_event(
            request_id="req-123",
            query_hash="hash-abc",
            provider="openai",
            latency_ms=100.0,
        )

        assert entry.is_query_event is True
        assert entry.is_cache_event is False

    def test_should_identify_cache_event(self):
        """Test is_cache_event property."""
        hit = AuditLogEntry.cache_hit_event(
            request_id="req-123",
            query_hash="hash-abc",
            latency_ms=10.0,
        )

        assert hit.is_cache_event is True
        assert hit.is_query_event is False

        miss = AuditLogEntry.cache_miss_event(
            request_id="req-123",
            query_hash="hash-abc",
            latency_ms=5.0,
        )

        assert miss.is_cache_event is True

    def test_should_identify_error_event(self):
        """Test is_error_event property."""
        entry = AuditLogEntry.error_event(
            request_id="req-123",
            error_code="TEST_ERROR",
            error_message="Test",
            latency_ms=1.0,
        )

        assert entry.is_error_event is True
        assert entry.is_query_event is False

    def test_should_identify_system_event(self):
        """Test is_system_event property."""
        entry = AuditLogEntry.system_event(EventType.SYSTEM_START)

        assert entry.is_system_event is True
        assert entry.is_query_event is False

    def test_should_detect_error(self):
        """Test has_error property."""
        # Successful event
        success = AuditLogEntry.query_event(
            request_id="req-123",
            query_hash="hash-abc",
            provider="openai",
            latency_ms=100.0,
        )
        assert success.has_error is False

        # Failed event
        failed = AuditLogEntry.query_event(
            request_id="req-123",
            query_hash="hash-abc",
            provider="openai",
            latency_ms=100.0,
            success=False,
            error_code="ERROR",
        )
        assert failed.has_error is True

    def test_should_serialize_to_json(self):
        """Test serialization."""
        entry = AuditLogEntry.query_event(
            request_id="req-123",
            query_hash="hash-abc",
            provider="openai",
            latency_ms=150.0,
        )

        json_data = entry.model_dump()

        assert json_data["event_type"] == "query"
        assert json_data["request_id"] == "req-123"
        assert json_data["query_hash"] == "hash-abc"

    def test_should_deserialize_from_json(self):
        """Test deserialization."""
        data = {
            "timestamp": "2025-11-12T10:30:00Z",
            "event_type": "query",
            "request_id": "req-123",
            "query_hash": "hash-abc",
            "provider": "openai",
            "latency_ms": 150.0,
            "success": True,
        }

        entry = AuditLogEntry.model_validate(data)

        assert entry.event_type == EventType.QUERY
        assert entry.request_id == "req-123"


class TestAuditLogSummary:
    """Test audit log summary model."""

    def test_should_create_summary_from_entries(self):
        """Test creating summary from entries."""
        entries = [
            AuditLogEntry.query_event("req-1", "hash-1", "openai", 100.0),
            AuditLogEntry.cache_hit_event("req-2", "hash-2", 10.0),
            AuditLogEntry.cache_miss_event("req-3", "hash-3", 5.0),
        ]

        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        summary = AuditLogSummary.from_entries(entries, start, end)

        assert summary.total_events == 3
        assert summary.successful_events == 3
        assert summary.failed_events == 0
        assert summary.query_events == 1
        assert summary.cache_hit_events == 1
        assert summary.cache_miss_events == 1

    def test_should_calculate_average_latency(self):
        """Test average latency calculation."""
        entries = [
            AuditLogEntry.query_event("req-1", "hash-1", "openai", 100.0),
            AuditLogEntry.query_event("req-2", "hash-2", "openai", 200.0),
            AuditLogEntry.query_event("req-3", "hash-3", "openai", 300.0),
        ]

        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        summary = AuditLogSummary.from_entries(entries, start, end)

        # (100 + 200 + 300) / 3 = 200
        assert summary.avg_latency_ms == 200.0

    def test_should_handle_empty_entries(self):
        """Test summary with no entries."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        summary = AuditLogSummary.from_entries([], start, end)

        assert summary.total_events == 0
        assert summary.avg_latency_ms == 0.0

    def test_should_count_successful_and_failed(self):
        """Test counting successful and failed events."""
        entries = [
            AuditLogEntry.query_event("req-1", "hash-1", "openai", 100.0, success=True),
            AuditLogEntry.query_event(
                "req-2", "hash-2", "openai", 100.0, success=False
            ),
            AuditLogEntry.error_event("req-3", "ERROR", "Test", 10.0),
        ]

        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        summary = AuditLogSummary.from_entries(entries, start, end)

        assert summary.successful_events == 1
        assert summary.failed_events == 2

    def test_should_calculate_success_rate(self):
        """Test success rate calculation."""
        entries = [
            AuditLogEntry.query_event("req-1", "hash-1", "openai", 100.0, success=True),
            AuditLogEntry.query_event("req-2", "hash-2", "openai", 100.0, success=True),
            AuditLogEntry.query_event("req-3", "hash-3", "openai", 100.0, success=True),
            AuditLogEntry.query_event(
                "req-4", "hash-4", "openai", 100.0, success=False
            ),
        ]

        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        summary = AuditLogSummary.from_entries(entries, start, end)

        # 3 successful out of 4 = 75%
        assert summary.success_rate == 75.0

    def test_should_handle_zero_events_for_success_rate(self):
        """Test success rate with no events."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        summary = AuditLogSummary.from_entries([], start, end)

        assert summary.success_rate == 0.0

    def test_should_calculate_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        entries = [
            AuditLogEntry.cache_hit_event("req-1", "hash-1", 10.0),
            AuditLogEntry.cache_hit_event("req-2", "hash-2", 10.0),
            AuditLogEntry.cache_hit_event("req-3", "hash-3", 10.0),
            AuditLogEntry.cache_miss_event("req-4", "hash-4", 5.0),
        ]

        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        summary = AuditLogSummary.from_entries(entries, start, end)

        # 3 hits out of 4 cache events = 75%
        assert summary.cache_hit_rate == 75.0

    def test_should_handle_no_cache_events_for_hit_rate(self):
        """Test cache hit rate with no cache events."""
        entries = [
            AuditLogEntry.query_event("req-1", "hash-1", "openai", 100.0),
        ]

        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        summary = AuditLogSummary.from_entries(entries, start, end)

        assert summary.cache_hit_rate == 0.0

    def test_should_calculate_duration(self):
        """Test duration calculation."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=2, minutes=30)

        summary = AuditLogSummary.from_entries([], start, end)

        # 2.5 hours = 9000 seconds
        assert summary.duration_seconds == 9000

    def test_should_serialize_to_json(self):
        """Test serialization."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        summary = AuditLogSummary.from_entries([], start, end)

        json_data = summary.model_dump()

        assert json_data["total_events"] == 0
        assert "start_time" in json_data
        assert "end_time" in json_data

    def test_should_deserialize_from_json(self):
        """Test deserialization."""
        data = {
            "total_events": 100,
            "successful_events": 95,
            "failed_events": 5,
            "query_events": 80,
            "cache_hit_events": 60,
            "cache_miss_events": 20,
            "error_events": 5,
            "avg_latency_ms": 125.5,
            "start_time": "2025-11-12T10:00:00Z",
            "end_time": "2025-11-12T11:00:00Z",
        }

        summary = AuditLogSummary.model_validate(data)

        assert summary.total_events == 100
        assert summary.successful_events == 95
        assert summary.avg_latency_ms == 125.5
