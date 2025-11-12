"""
Error response models.

Sandi Metz Principles:
- Small classes with clear purpose
- Consistent error handling
- Clear naming conventions
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    INVALID_QUERY = "INVALID_QUERY"
    INVALID_THRESHOLD = "INVALID_THRESHOLD"
    INVALID_PROVIDER = "INVALID_PROVIDER"
    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"
    CACHE_ERROR = "CACHE_ERROR"
    LLM_ERROR = "LLM_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorResponse(BaseModel):
    """Standard error response format."""

    detail: str = Field(..., description="Error message describing what went wrong")
    error_code: ErrorCode = Field(..., description="Standard error code")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Error timestamp (ISO 8601)",
    )

    @classmethod
    def invalid_query(cls, detail: str = "Query text is empty or invalid") -> "ErrorResponse":
        """Create invalid query error."""
        return cls(detail=detail, error_code=ErrorCode.INVALID_QUERY)

    @classmethod
    def invalid_threshold(
        cls, detail: str = "Semantic threshold must be between 0.0 and 1.0"
    ) -> "ErrorResponse":
        """Create invalid threshold error."""
        return cls(detail=detail, error_code=ErrorCode.INVALID_THRESHOLD)

    @classmethod
    def invalid_provider(cls, provider: str) -> "ErrorResponse":
        """Create invalid provider error."""
        return cls(
            detail=f"Invalid LLM provider: {provider}",
            error_code=ErrorCode.INVALID_PROVIDER,
        )

    @classmethod
    def provider_not_found(cls, provider: str) -> "ErrorResponse":
        """Create provider not found error."""
        return cls(
            detail=f"LLM provider not found: {provider}",
            error_code=ErrorCode.PROVIDER_NOT_FOUND,
        )

    @classmethod
    def cache_error(cls, detail: Optional[str] = None) -> "ErrorResponse":
        """Create cache error."""
        return cls(
            detail=detail or "Cache service error",
            error_code=ErrorCode.CACHE_ERROR,
        )

    @classmethod
    def llm_error(cls, detail: Optional[str] = None) -> "ErrorResponse":
        """Create LLM provider error."""
        return cls(
            detail=detail or "LLM provider error",
            error_code=ErrorCode.LLM_ERROR,
        )

    @classmethod
    def service_unavailable(cls, service: str) -> "ErrorResponse":
        """Create service unavailable error."""
        return cls(
            detail=f"Required service unavailable: {service}",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    @classmethod
    def rate_limit_exceeded(cls, retry_after: int) -> "ErrorResponse":
        """Create rate limit exceeded error."""
        return cls(
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        )

    @classmethod
    def validation_error(cls, detail: str) -> "ErrorResponse":
        """Create validation error."""
        return cls(detail=detail, error_code=ErrorCode.VALIDATION_ERROR)

    @classmethod
    def internal_error(cls, detail: Optional[str] = None) -> "ErrorResponse":
        """Create internal server error."""
        return cls(
            detail=detail or "Internal server error",
            error_code=ErrorCode.INTERNAL_ERROR,
        )
