"""
Request Context Manager.

Manages request-scoped context for query processing.

Sandi Metz Principles:
- Single Responsibility: Request context management
- Clear lifecycle: Start to end tracking
- Immutable data: Context values don't change
"""

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Context variable for current request
_current_context: ContextVar[Optional["RequestContext"]] = ContextVar(
    "request_context", default=None
)


@dataclass
class RequestContext:
    """
    Holds context for a single request.

    Immutable after creation.
    """

    request_id: str
    start_time: float
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Tracking fields (mutable)
    cache_checked: bool = False
    cache_hit: bool = False
    semantic_checked: bool = False
    semantic_hit: bool = False
    llm_called: bool = False
    end_time: Optional[float] = None

    @classmethod
    def create(
        cls,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "RequestContext":
        """
        Create new request context.

        Args:
            query: User query
            user_id: Optional user identifier
            session_id: Optional session identifier
            metadata: Additional metadata

        Returns:
            New RequestContext
        """
        return cls(
            request_id=str(uuid.uuid4()),
            start_time=time.time(),
            query=query,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
        )

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    @property
    def is_complete(self) -> bool:
        """Check if request is complete."""
        return self.end_time is not None

    def mark_cache_checked(self, hit: bool = False) -> None:
        """Mark exact cache as checked."""
        self.cache_checked = True
        self.cache_hit = hit

    def mark_semantic_checked(self, hit: bool = False) -> None:
        """Mark semantic cache as checked."""
        self.semantic_checked = True
        self.semantic_hit = hit

    def mark_llm_called(self) -> None:
        """Mark LLM as called."""
        self.llm_called = True

    def complete(self) -> None:
        """Mark request as complete."""
        self.end_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Returns:
            Context as dict
        """
        return {
            "request_id": self.request_id,
            "query": self.query[:100],  # Truncate for logging
            "user_id": self.user_id,
            "session_id": self.session_id,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "cache_checked": self.cache_checked,
            "cache_hit": self.cache_hit,
            "semantic_checked": self.semantic_checked,
            "semantic_hit": self.semantic_hit,
            "llm_called": self.llm_called,
            "is_complete": self.is_complete,
        }


class RequestContextManager:
    """
    Manages request context lifecycle.

    Uses context variables for async safety.
    """

    @staticmethod
    def start(
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RequestContext:
        """
        Start new request context.

        Args:
            query: User query
            user_id: Optional user identifier
            session_id: Optional session identifier
            metadata: Additional metadata

        Returns:
            New RequestContext
        """
        context = RequestContext.create(
            query=query,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata,
        )
        _current_context.set(context)

        logger.info(
            "Request context started",
            request_id=context.request_id,
            query_len=len(query),
        )

        return context

    @staticmethod
    def current() -> Optional[RequestContext]:
        """
        Get current request context.

        Returns:
            Current context or None
        """
        return _current_context.get()

    @staticmethod
    def end() -> Optional[RequestContext]:
        """
        End current request context.

        Returns:
            Completed context or None
        """
        context = _current_context.get()
        if context:
            context.complete()
            _current_context.set(None)

            logger.info(
                "Request context ended",
                request_id=context.request_id,
                elapsed_ms=round(context.elapsed_ms, 2),
                cache_hit=context.cache_hit,
                semantic_hit=context.semantic_hit,
                llm_called=context.llm_called,
            )

        return context

    @staticmethod
    def get_request_id() -> Optional[str]:
        """
        Get current request ID.

        Returns:
            Request ID or None
        """
        context = _current_context.get()
        return context.request_id if context else None


# Convenience functions
def start_request(
    query: str,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> RequestContext:
    """Start new request context."""
    return RequestContextManager.start(query, user_id=user_id, metadata=metadata)


def get_current_context() -> Optional[RequestContext]:
    """Get current request context."""
    return RequestContextManager.current()


def end_request() -> Optional[RequestContext]:
    """End current request context."""
    return RequestContextManager.end()


def get_request_id() -> Optional[str]:
    """Get current request ID."""
    return RequestContextManager.get_request_id()
