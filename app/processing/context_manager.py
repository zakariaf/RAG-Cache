"""
Request context manager.

Manages request-scoped context and metadata.

Sandi Metz Principles:
- Single Responsibility: Context management
- Small class: Focused on context tracking
- Clear naming: Descriptive context fields
"""

import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, AsyncIterator, Dict, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Context variables for async request tracking
_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_start_time_var: ContextVar[Optional[float]] = ContextVar("start_time", default=None)
_metadata_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "metadata", default=None
)


class RequestContext:
    """
    Request context data holder.

    Stores request-scoped information like ID, timing, and metadata.
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        start_time: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize request context.

        Args:
            request_id: Unique request identifier
            start_time: Request start timestamp
            metadata: Additional metadata
        """
        self.request_id = request_id or str(uuid.uuid4())
        self.start_time = start_time or time.time()
        self.metadata = metadata or {}

    @property
    def elapsed_time(self) -> float:
        """
        Get elapsed time since request start.

        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.start_time

    @property
    def elapsed_ms(self) -> float:
        """
        Get elapsed time in milliseconds.

        Returns:
            Elapsed time in milliseconds
        """
        return self.elapsed_time * 1000

    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set metadata value.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "request_id": self.request_id,
            "start_time": self.start_time,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "metadata": self.metadata.copy(),
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"RequestContext(request_id='{self.request_id}', "
            f"elapsed_ms={self.elapsed_ms:.2f})"
        )


class RequestContextManager:
    """
    Manager for request context lifecycle.

    Provides context manager interface for tracking request scope.
    """

    @staticmethod
    def generate_request_id() -> str:
        """
        Generate unique request ID.

        Returns:
            UUID string
        """
        return str(uuid.uuid4())

    @staticmethod
    def get_current_request_id() -> Optional[str]:
        """
        Get current request ID from context.

        Returns:
            Request ID or None if not in request context
        """
        return _request_id_var.get()

    @staticmethod
    def get_current_start_time() -> Optional[float]:
        """
        Get current request start time.

        Returns:
            Start timestamp or None
        """
        return _start_time_var.get()

    @staticmethod
    def get_current_metadata() -> Dict[str, Any]:
        """
        Get current request metadata.

        Returns:
            Metadata dictionary
        """
        metadata = _metadata_var.get()
        return metadata if metadata is not None else {}

    @staticmethod
    def get_current_context() -> Optional[RequestContext]:
        """
        Get current request context.

        Returns:
            RequestContext or None if not in request scope
        """
        request_id = RequestContextManager.get_current_request_id()
        if request_id is None:
            return None

        start_time = RequestContextManager.get_current_start_time()
        metadata = RequestContextManager.get_current_metadata()

        return RequestContext(
            request_id=request_id,
            start_time=start_time,
            metadata=metadata,
        )

    @staticmethod
    @asynccontextmanager
    async def create_context(
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[RequestContext]:
        """
        Create request context scope.

        Args:
            request_id: Custom request ID (generates if None)
            metadata: Initial metadata

        Yields:
            RequestContext instance

        Example:
            async with RequestContextManager.create_context() as ctx:
                ctx.set_metadata("user_id", "123")
                # Request processing here
        """
        # Generate or use provided request ID
        req_id = request_id or RequestContextManager.generate_request_id()
        start = time.time()
        meta = metadata or {}

        # Set context vars
        token_id = _request_id_var.set(req_id)
        token_time = _start_time_var.set(start)
        token_meta = _metadata_var.set(meta)

        # Create context object
        context = RequestContext(
            request_id=req_id,
            start_time=start,
            metadata=meta,
        )

        logger.debug("Request context created", request_id=req_id)

        try:
            yield context

        finally:
            # Log completion
            elapsed = (time.time() - start) * 1000
            logger.debug(
                "Request context completed",
                request_id=req_id,
                elapsed_ms=round(elapsed, 2),
            )

            # Reset context vars
            _request_id_var.reset(token_id)
            _start_time_var.reset(token_time)
            _metadata_var.reset(token_meta)

    @staticmethod
    def set_metadata(key: str, value: Any) -> None:
        """
        Set metadata in current context.

        Args:
            key: Metadata key
            value: Metadata value
        """
        metadata = RequestContextManager.get_current_metadata()
        metadata[key] = value
        _metadata_var.set(metadata)

    @staticmethod
    def get_metadata(key: str, default: Any = None) -> Any:
        """
        Get metadata from current context.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        metadata = RequestContextManager.get_current_metadata()
        return metadata.get(key, default)

    @staticmethod
    def get_elapsed_time() -> Optional[float]:
        """
        Get elapsed time for current request.

        Returns:
            Elapsed seconds or None if not in request context
        """
        start_time = RequestContextManager.get_current_start_time()
        if start_time is None:
            return None
        return time.time() - start_time

    @staticmethod
    def get_elapsed_ms() -> Optional[float]:
        """
        Get elapsed time in milliseconds.

        Returns:
            Elapsed milliseconds or None if not in request context
        """
        elapsed = RequestContextManager.get_elapsed_time()
        if elapsed is None:
            return None
        return elapsed * 1000


# Convenience functions
def get_request_id() -> Optional[str]:
    """
    Get current request ID (convenience function).

    Returns:
        Request ID or None
    """
    return RequestContextManager.get_current_request_id()


def get_request_context() -> Optional[RequestContext]:
    """
    Get current request context (convenience function).

    Returns:
        RequestContext or None
    """
    return RequestContextManager.get_current_context()


def set_request_metadata(key: str, value: Any) -> None:
    """
    Set request metadata (convenience function).

    Args:
        key: Metadata key
        value: Metadata value
    """
    RequestContextManager.set_metadata(key, value)


def get_request_metadata(key: str, default: Any = None) -> Any:
    """
    Get request metadata (convenience function).

    Args:
        key: Metadata key
        default: Default value

    Returns:
        Metadata value or default
    """
    return RequestContextManager.get_metadata(key, default)
