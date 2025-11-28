"""Unit tests for Request Context Manager."""

import pytest
import time

from app.pipeline.request_context import (
    RequestContext,
    RequestContextManager,
    start_request,
    get_current_context,
    end_request,
    get_request_id,
)


class TestRequestContext:
    """Tests for RequestContext dataclass."""

    def test_create_context(self):
        """Test context creation."""
        ctx = RequestContext.create(query="test query")
        assert ctx.query == "test query"
        assert ctx.request_id is not None
        assert ctx.start_time > 0
        assert ctx.is_complete is False

    def test_create_with_user_id(self):
        """Test context with user ID."""
        ctx = RequestContext.create(query="test", user_id="user123")
        assert ctx.user_id == "user123"

    def test_create_with_metadata(self):
        """Test context with metadata."""
        ctx = RequestContext.create(query="test", metadata={"key": "value"})
        assert ctx.metadata["key"] == "value"

    def test_elapsed_ms(self):
        """Test elapsed time calculation."""
        ctx = RequestContext.create(query="test")
        time.sleep(0.01)  # 10ms
        elapsed = ctx.elapsed_ms
        assert elapsed >= 10

    def test_mark_cache_checked(self):
        """Test cache checked marking."""
        ctx = RequestContext.create(query="test")
        ctx.mark_cache_checked(hit=True)
        assert ctx.cache_checked is True
        assert ctx.cache_hit is True

    def test_mark_semantic_checked(self):
        """Test semantic checked marking."""
        ctx = RequestContext.create(query="test")
        ctx.mark_semantic_checked(hit=True)
        assert ctx.semantic_checked is True
        assert ctx.semantic_hit is True

    def test_mark_llm_called(self):
        """Test LLM called marking."""
        ctx = RequestContext.create(query="test")
        ctx.mark_llm_called()
        assert ctx.llm_called is True

    def test_complete(self):
        """Test context completion."""
        ctx = RequestContext.create(query="test")
        assert ctx.is_complete is False
        ctx.complete()
        assert ctx.is_complete is True
        assert ctx.end_time is not None

    def test_to_dict(self):
        """Test dictionary conversion."""
        ctx = RequestContext.create(query="test query")
        ctx.mark_cache_checked(hit=True)

        d = ctx.to_dict()

        assert d["query"] == "test query"
        assert d["cache_checked"] is True
        assert d["cache_hit"] is True
        assert "elapsed_ms" in d


class TestRequestContextManager:
    """Tests for RequestContextManager class."""

    def test_start_and_current(self):
        """Test start and current context."""
        ctx = RequestContextManager.start(query="test")
        current = RequestContextManager.current()

        assert current is not None
        assert current.request_id == ctx.request_id

        # Cleanup
        RequestContextManager.end()

    def test_end_returns_context(self):
        """Test end returns completed context."""
        RequestContextManager.start(query="test")
        ctx = RequestContextManager.end()

        assert ctx is not None
        assert ctx.is_complete is True

    def test_end_clears_context(self):
        """Test end clears current context."""
        RequestContextManager.start(query="test")
        RequestContextManager.end()

        assert RequestContextManager.current() is None

    def test_get_request_id(self):
        """Test request ID retrieval."""
        ctx = RequestContextManager.start(query="test")
        req_id = RequestContextManager.get_request_id()

        assert req_id == ctx.request_id

        RequestContextManager.end()

    def test_get_request_id_none_when_no_context(self):
        """Test request ID is None without context."""
        # Ensure no context
        RequestContextManager.end()
        assert RequestContextManager.get_request_id() is None


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_start_request(self):
        """Test start_request function."""
        ctx = start_request("test query", user_id="user1")

        assert ctx.query == "test query"
        assert ctx.user_id == "user1"

        end_request()

    def test_get_current_context(self):
        """Test get_current_context function."""
        start_request("test")
        ctx = get_current_context()

        assert ctx is not None

        end_request()

    def test_end_request(self):
        """Test end_request function."""
        start_request("test")
        ctx = end_request()

        assert ctx is not None
        assert ctx.is_complete is True

    def test_get_request_id(self):
        """Test get_request_id function."""
        ctx = start_request("test")
        req_id = get_request_id()

        assert req_id == ctx.request_id

        end_request()
