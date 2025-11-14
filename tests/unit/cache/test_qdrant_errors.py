"""Unit tests for Qdrant error handling."""

import pytest

from app.cache.qdrant_errors import (
    ErrorContext,
    QdrantCollectionError,
    QdrantCollectionExistsError,
    QdrantCollectionNotFoundError,
    QdrantConnectionError,
    QdrantError,
    QdrantPointError,
    QdrantPointNotFoundError,
    QdrantSearchError,
    QdrantTimeoutError,
    QdrantValidationError,
    handle_qdrant_error,
    is_retryable_error,
)


class TestQdrantError:
    """Tests for QdrantError base class."""

    def test_error_creation(self):
        """Test QdrantError creation."""
        error = QdrantError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.cause is None

    def test_error_with_cause(self):
        """Test QdrantError with cause."""
        cause = ValueError("Original error")
        error = QdrantError("Test error", cause=cause)

        assert error.cause is cause
        assert "caused by" in str(error)
        assert "Original error" in str(error)


class TestErrorMapping:
    """Tests for handle_qdrant_error function."""

    def test_connection_error_mapping(self):
        """Test mapping connection errors."""
        error = Exception("Failed to connect to server")
        result = handle_qdrant_error(error, "test_operation")

        assert isinstance(result, QdrantConnectionError)
        assert result.cause is error
        assert "test_operation" in result.message

    def test_timeout_error_mapping(self):
        """Test mapping timeout errors."""
        error = Exception("Operation timeout exceeded")
        result = handle_qdrant_error(error, "search")

        assert isinstance(result, QdrantTimeoutError)
        assert "timeout" in result.message.lower()

    def test_collection_not_found_mapping(self):
        """Test mapping collection not found errors."""
        error = Exception("Collection not found")
        result = handle_qdrant_error(error, "get_collection")

        assert isinstance(result, QdrantCollectionNotFoundError)

    def test_collection_exists_mapping(self):
        """Test mapping collection exists errors."""
        error = Exception("Collection already exists")
        result = handle_qdrant_error(error, "create_collection")

        assert isinstance(result, QdrantCollectionExistsError)

    def test_collection_error_mapping(self):
        """Test mapping generic collection errors."""
        error = Exception("Collection operation failed")
        result = handle_qdrant_error(error, "update_collection")

        assert isinstance(result, QdrantCollectionError)

    def test_point_not_found_mapping(self):
        """Test mapping point not found errors."""
        error = Exception("Point not found")
        result = handle_qdrant_error(error, "get_point")

        assert isinstance(result, QdrantPointNotFoundError)

    def test_point_error_mapping(self):
        """Test mapping generic point errors."""
        error = Exception("Point operation failed")
        result = handle_qdrant_error(error, "upsert_point")

        assert isinstance(result, QdrantPointError)

    def test_search_error_mapping(self):
        """Test mapping search errors."""
        error = Exception("Search query failed")
        result = handle_qdrant_error(error, "search")

        assert isinstance(result, QdrantSearchError)

    def test_validation_error_mapping(self):
        """Test mapping validation errors."""
        error = Exception("Invalid vector dimension")
        result = handle_qdrant_error(error, "validate")

        assert isinstance(result, QdrantValidationError)

    def test_generic_error_mapping(self):
        """Test mapping generic errors."""
        error = Exception("Unknown error")
        result = handle_qdrant_error(error, "unknown_op")

        assert isinstance(result, QdrantError)
        assert result.cause is error


class TestRetryableErrors:
    """Tests for is_retryable_error function."""

    def test_connection_error_retryable(self):
        """Test connection errors are retryable."""
        error = QdrantConnectionError("Connection failed")

        assert is_retryable_error(error) is True

    def test_timeout_error_retryable(self):
        """Test timeout errors are retryable."""
        error = QdrantTimeoutError("Operation timed out")

        assert is_retryable_error(error) is True

    def test_validation_error_not_retryable(self):
        """Test validation errors are not retryable."""
        error = QdrantValidationError("Invalid input")

        assert is_retryable_error(error) is False

    def test_generic_timeout_retryable(self):
        """Test generic timeout errors are retryable."""
        error = Exception("Request timeout")

        assert is_retryable_error(error) is True

    def test_generic_connection_retryable(self):
        """Test generic connection errors are retryable."""
        error = Exception("Network connection lost")

        assert is_retryable_error(error) is True

    def test_generic_unavailable_retryable(self):
        """Test unavailable errors are retryable."""
        error = Exception("Service unavailable")

        assert is_retryable_error(error) is True

    def test_non_retryable_error(self):
        """Test non-retryable errors."""
        error = Exception("Invalid operation")

        assert is_retryable_error(error) is False


class TestErrorContext:
    """Tests for ErrorContext context manager."""

    def test_error_context_no_error(self):
        """Test ErrorContext with no errors."""
        with ErrorContext("test_operation"):
            pass  # No error should occur

    def test_error_context_maps_error(self):
        """Test ErrorContext maps exceptions."""
        with pytest.raises(QdrantConnectionError):
            with ErrorContext("test_operation"):
                raise Exception("Connection failed")

    def test_error_context_preserves_operation(self):
        """Test ErrorContext preserves operation name."""
        try:
            with ErrorContext("my_operation"):
                raise Exception("Test error")
        except QdrantError as e:
            assert "my_operation" in e.message

    def test_error_context_chains_exceptions(self):
        """Test ErrorContext chains exceptions properly."""
        original = ValueError("Original error")

        try:
            with ErrorContext("test_op"):
                raise original
        except QdrantError as e:
            assert e.cause is original
