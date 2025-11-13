"""Test error models."""

from datetime import datetime, timezone

from app.models.error import ErrorCode, ErrorResponse


class TestErrorCode:
    """Test error code enum."""

    def test_should_have_all_error_codes(self):
        """Test all error codes exist."""
        assert ErrorCode.INVALID_QUERY == "INVALID_QUERY"
        assert ErrorCode.INVALID_THRESHOLD == "INVALID_THRESHOLD"
        assert ErrorCode.INVALID_PROVIDER == "INVALID_PROVIDER"
        assert ErrorCode.PROVIDER_NOT_FOUND == "PROVIDER_NOT_FOUND"
        assert ErrorCode.CACHE_ERROR == "CACHE_ERROR"
        assert ErrorCode.LLM_ERROR == "LLM_ERROR"
        assert ErrorCode.SERVICE_UNAVAILABLE == "SERVICE_UNAVAILABLE"
        assert ErrorCode.RATE_LIMIT_EXCEEDED == "RATE_LIMIT_EXCEEDED"
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"

    def test_should_be_string_enum(self):
        """Test error codes are string enums."""
        assert isinstance(ErrorCode.INVALID_QUERY.value, str)
        assert ErrorCode.CACHE_ERROR.value == "CACHE_ERROR"


class TestErrorResponse:
    """Test error response model."""

    def test_should_create_error_response(self):
        """Test basic error response creation."""
        error = ErrorResponse(
            detail="Test error",
            error_code=ErrorCode.INTERNAL_ERROR,
        )
        assert error.detail == "Test error"
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert isinstance(error.timestamp, datetime)

    def test_should_have_utc_timestamp(self):
        """Test timestamp is in UTC."""
        error = ErrorResponse(
            detail="Test error",
            error_code=ErrorCode.INTERNAL_ERROR,
        )
        # Check that timestamp is recent (within last 5 seconds)
        now = datetime.now(timezone.utc)
        time_diff = (now - error.timestamp).total_seconds()
        assert 0 <= time_diff < 5

    def test_should_create_invalid_query_error(self):
        """Test invalid query error factory method."""
        error = ErrorResponse.invalid_query()
        assert error.error_code == ErrorCode.INVALID_QUERY
        assert "empty or invalid" in error.detail.lower()

        # With custom message
        error = ErrorResponse.invalid_query("Custom message")
        assert error.detail == "Custom message"
        assert error.error_code == ErrorCode.INVALID_QUERY

    def test_should_create_invalid_threshold_error(self):
        """Test invalid threshold error factory method."""
        error = ErrorResponse.invalid_threshold()
        assert error.error_code == ErrorCode.INVALID_THRESHOLD
        assert "0.0 and 1.0" in error.detail

        # With custom message
        error = ErrorResponse.invalid_threshold("Threshold too high")
        assert error.detail == "Threshold too high"

    def test_should_create_invalid_provider_error(self):
        """Test invalid provider error factory method."""
        error = ErrorResponse.invalid_provider("unknown_provider")
        assert error.error_code == ErrorCode.INVALID_PROVIDER
        assert "unknown_provider" in error.detail

    def test_should_create_provider_not_found_error(self):
        """Test provider not found error factory method."""
        error = ErrorResponse.provider_not_found("openai")
        assert error.error_code == ErrorCode.PROVIDER_NOT_FOUND
        assert "openai" in error.detail
        assert "not found" in error.detail.lower()

    def test_should_create_cache_error(self):
        """Test cache error factory method."""
        # Default message
        error = ErrorResponse.cache_error()
        assert error.error_code == ErrorCode.CACHE_ERROR
        assert "cache service error" in error.detail.lower()

        # Custom message
        error = ErrorResponse.cache_error("Redis connection failed")
        assert error.detail == "Redis connection failed"
        assert error.error_code == ErrorCode.CACHE_ERROR

    def test_should_create_llm_error(self):
        """Test LLM error factory method."""
        # Default message
        error = ErrorResponse.llm_error()
        assert error.error_code == ErrorCode.LLM_ERROR
        assert "llm provider error" in error.detail.lower()

        # Custom message
        error = ErrorResponse.llm_error("OpenAI API timeout")
        assert error.detail == "OpenAI API timeout"

    def test_should_create_service_unavailable_error(self):
        """Test service unavailable error factory method."""
        error = ErrorResponse.service_unavailable("redis")
        assert error.error_code == ErrorCode.SERVICE_UNAVAILABLE
        assert "redis" in error.detail.lower()
        assert "unavailable" in error.detail.lower()

    def test_should_create_rate_limit_exceeded_error(self):
        """Test rate limit exceeded error factory method."""
        error = ErrorResponse.rate_limit_exceeded(60)
        assert error.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert "60" in error.detail
        assert "retry" in error.detail.lower()

    def test_should_create_validation_error(self):
        """Test validation error factory method."""
        error = ErrorResponse.validation_error("Field 'query' is required")
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.detail == "Field 'query' is required"

    def test_should_create_internal_error(self):
        """Test internal error factory method."""
        # Default message
        error = ErrorResponse.internal_error()
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert "internal server error" in error.detail.lower()

        # Custom message
        error = ErrorResponse.internal_error("Database connection lost")
        assert error.detail == "Database connection lost"

    def test_should_serialize_to_json(self):
        """Test error response serialization."""
        error = ErrorResponse.invalid_query("Test error")
        json_data = error.model_dump()

        assert json_data["detail"] == "Test error"
        assert json_data["error_code"] == "INVALID_QUERY"
        assert "timestamp" in json_data

    def test_should_deserialize_from_json(self):
        """Test error response deserialization."""
        data = {
            "detail": "Test error",
            "error_code": "CACHE_ERROR",
            "timestamp": "2025-11-12T10:30:00Z",
        }
        error = ErrorResponse.model_validate(data)

        assert error.detail == "Test error"
        assert error.error_code == ErrorCode.CACHE_ERROR
