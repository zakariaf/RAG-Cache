"""
Qdrant error handling and custom exceptions.

Sandi Metz Principles:
- Single Responsibility: Error handling only
- Small classes: Each exception focused
- Clear naming: Descriptive exception names
"""

from typing import Any, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class QdrantError(Exception):
    """Base exception for all Qdrant errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        Initialize Qdrant error.

        Args:
            message: Error message
            cause: Original exception that caused this error
        """
        self.message = message
        self.cause = cause
        super().__init__(message)

    def __str__(self) -> str:
        """Get string representation."""
        if self.cause:
            return f"{self.message} (caused by: {str(self.cause)})"
        return self.message


class QdrantConnectionError(QdrantError):
    """Raised when connection to Qdrant fails."""

    pass


class QdrantCollectionError(QdrantError):
    """Raised when collection operations fail."""

    pass


class QdrantCollectionNotFoundError(QdrantCollectionError):
    """Raised when collection does not exist."""

    pass


class QdrantCollectionExistsError(QdrantCollectionError):
    """Raised when collection already exists."""

    pass


class QdrantPointError(QdrantError):
    """Raised when point operations fail."""

    pass


class QdrantPointNotFoundError(QdrantPointError):
    """Raised when point does not exist."""

    pass


class QdrantSearchError(QdrantError):
    """Raised when search operations fail."""

    pass


class QdrantValidationError(QdrantError):
    """Raised when validation fails."""

    pass


class QdrantTimeoutError(QdrantError):
    """Raised when operation times out."""

    pass


class QdrantCapacityError(QdrantError):
    """Raised when storage capacity is exceeded."""

    pass


class QdrantIndexError(QdrantError):
    """Raised when index operations fail."""

    pass


def handle_qdrant_error(error: Exception, operation: str) -> QdrantError:
    """
    Map Qdrant exceptions to custom exceptions.

    Args:
        error: Original exception
        operation: Operation that failed

    Returns:
        Custom Qdrant exception
    """
    error_msg = str(error)
    error_type = type(error).__name__

    # Connection errors
    if "connect" in error_msg.lower() or "connection" in error_msg.lower():
        logger.error(f"Connection error during {operation}", error=error_msg)
        return QdrantConnectionError(
            f"Failed to connect to Qdrant during {operation}", cause=error
        )

    # Timeout errors
    if "timeout" in error_msg.lower():
        logger.error(f"Timeout during {operation}", error=error_msg)
        return QdrantTimeoutError(
            f"Operation {operation} timeout exceeded", cause=error
        )

    # Collection errors
    if "collection" in error_msg.lower():
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            logger.error(f"Collection not found during {operation}", error=error_msg)
            return QdrantCollectionNotFoundError(
                f"Collection not found during {operation}", cause=error
            )
        if "already exists" in error_msg.lower():
            logger.error(f"Collection exists during {operation}", error=error_msg)
            return QdrantCollectionExistsError(
                f"Collection already exists during {operation}", cause=error
            )
        logger.error(f"Collection error during {operation}", error=error_msg)
        return QdrantCollectionError(
            f"Collection operation failed during {operation}", cause=error
        )

    # Point errors
    if "point" in error_msg.lower():
        if "not found" in error_msg.lower():
            logger.error(f"Point not found during {operation}", error=error_msg)
            return QdrantPointNotFoundError(
                f"Point not found during {operation}", cause=error
            )
        logger.error(f"Point error during {operation}", error=error_msg)
        return QdrantPointError(
            f"Point operation failed during {operation}", cause=error
        )

    # Search errors
    if "search" in error_msg.lower() or "query" in error_msg.lower():
        logger.error(f"Search error during {operation}", error=error_msg)
        return QdrantSearchError(f"Search failed during {operation}", cause=error)

    # Validation errors
    if "invalid" in error_msg.lower() or "validation" in error_msg.lower():
        logger.error(f"Validation error during {operation}", error=error_msg)
        return QdrantValidationError(
            f"Validation failed during {operation}", cause=error
        )

    # Capacity errors
    if "capacity" in error_msg.lower() or "full" in error_msg.lower():
        logger.error(f"Capacity error during {operation}", error=error_msg)
        return QdrantCapacityError(
            f"Storage capacity exceeded during {operation}", cause=error
        )

    # Index errors
    if "index" in error_msg.lower():
        logger.error(f"Index error during {operation}", error=error_msg)
        return QdrantIndexError(
            f"Index operation failed during {operation}", cause=error
        )

    # Generic error
    logger.error(
        f"Unknown error during {operation}",
        error=error_msg,
        error_type=error_type,
    )
    return QdrantError(f"Operation {operation} failed: {error_msg}", cause=error)


def is_retryable_error(error: Exception) -> bool:
    """
    Check if error is retryable.

    Args:
        error: Exception to check

    Returns:
        True if error is transient and retryable
    """
    retryable_types = (
        QdrantConnectionError,
        QdrantTimeoutError,
    )

    if isinstance(error, retryable_types):
        return True

    error_msg = str(error).lower()
    retryable_keywords = [
        "timeout",
        "connection",
        "network",
        "unavailable",
        "temporary",
    ]

    return any(keyword in error_msg for keyword in retryable_keywords)


class ErrorContext:
    """
    Context manager for Qdrant error handling.

    Automatically maps exceptions to custom types.
    """

    def __init__(self, operation: str):
        """
        Initialize error context.

        Args:
            operation: Operation name for error messages
        """
        self.operation = operation

    def __enter__(self) -> "ErrorContext":
        """Enter context."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Any,
    ) -> None:
        """
        Exit context and handle exceptions.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if exc_val is not None:
            # Map to custom exception
            custom_error = handle_qdrant_error(exc_val, self.operation)
            raise custom_error from exc_val
