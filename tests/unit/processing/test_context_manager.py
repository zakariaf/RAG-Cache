"""Test request context manager."""

import pytest

from app.processing.context_manager import (
    RequestContext,
    RequestContextManager,
    get_request_context,
    get_request_id,
    get_request_metadata,
    set_request_metadata,
)


class TestRequestContext:
    """Test RequestContext class."""

    def test_create_context(self):
        """Test creating request context."""
        context = RequestContext(request_id="test-123")
        assert context.request_id == "test-123"
        assert context.start_time > 0

    def test_create_context_auto_id(self):
        """Test creating context with auto-generated ID."""
        context = RequestContext()
        assert context.request_id is not None
        assert len(context.request_id) > 0

    def test_elapsed_time(self):
        """Test elapsed time calculation."""
        context = RequestContext()
        elapsed = context.elapsed_time
        assert elapsed >= 0

    def test_elapsed_ms(self):
        """Test elapsed time in milliseconds."""
        context = RequestContext()
        elapsed_ms = context.elapsed_ms
        assert elapsed_ms >= 0

    def test_set_metadata(self):
        """Test setting metadata."""
        context = RequestContext()
        context.set_metadata("key", "value")
        assert context.metadata["key"] == "value"

    def test_get_metadata(self):
        """Test getting metadata."""
        context = RequestContext()
        context.set_metadata("key", "value")
        assert context.get_metadata("key") == "value"

    def test_get_metadata_default(self):
        """Test getting metadata with default."""
        context = RequestContext()
        assert context.get_metadata("missing", "default") == "default"

    def test_to_dict(self):
        """Test converting context to dict."""
        context = RequestContext(request_id="test-123")
        data = context.to_dict()
        assert data["request_id"] == "test-123"
        assert "start_time" in data
        assert "elapsed_ms" in data
        assert "metadata" in data

    def test_repr(self):
        """Test string representation."""
        context = RequestContext(request_id="test-123")
        repr_str = repr(context)
        assert "RequestContext" in repr_str
        assert "test-123" in repr_str


class TestRequestContextManager:
    """Test RequestContextManager class."""

    def test_generate_request_id(self):
        """Test request ID generation."""
        request_id = RequestContextManager.generate_request_id()
        assert request_id is not None
        assert len(request_id) > 0

    def test_generate_unique_ids(self):
        """Test generated IDs are unique."""
        id1 = RequestContextManager.generate_request_id()
        id2 = RequestContextManager.generate_request_id()
        assert id1 != id2

    def test_get_current_request_id_none_by_default(self):
        """Test getting current request ID outside context."""
        request_id = RequestContextManager.get_current_request_id()
        assert request_id is None

    def test_get_current_context_none_by_default(self):
        """Test getting current context outside scope."""
        context = RequestContextManager.get_current_context()
        assert context is None

    @pytest.mark.asyncio
    async def test_create_context(self):
        """Test creating context manager."""
        async with RequestContextManager.create_context() as ctx:
            assert ctx.request_id is not None
            assert RequestContextManager.get_current_request_id() == ctx.request_id

    @pytest.mark.asyncio
    async def test_create_context_custom_id(self):
        """Test creating context with custom ID."""
        async with RequestContextManager.create_context(request_id="custom-123") as ctx:
            assert ctx.request_id == "custom-123"

    @pytest.mark.asyncio
    async def test_create_context_with_metadata(self):
        """Test creating context with metadata."""
        metadata = {"user_id": "123"}
        async with RequestContextManager.create_context(metadata=metadata) as ctx:
            assert ctx.metadata["user_id"] == "123"

    @pytest.mark.asyncio
    async def test_context_cleared_after_exit(self):
        """Test context is cleared after exiting scope."""
        async with RequestContextManager.create_context(request_id="test-123"):
            pass  # Exit context

        # Context should be cleared
        assert RequestContextManager.get_current_request_id() is None

    @pytest.mark.asyncio
    async def test_set_metadata_in_context(self):
        """Test setting metadata while in context."""
        async with RequestContextManager.create_context():
            RequestContextManager.set_metadata("key", "value")
            value = RequestContextManager.get_metadata("key")
            assert value == "value"

    @pytest.mark.asyncio
    async def test_get_metadata_with_default(self):
        """Test getting metadata with default."""
        async with RequestContextManager.create_context():
            value = RequestContextManager.get_metadata("missing", "default")
            assert value == "default"

    @pytest.mark.asyncio
    async def test_get_elapsed_time(self):
        """Test getting elapsed time."""
        async with RequestContextManager.create_context():
            elapsed = RequestContextManager.get_elapsed_time()
            assert elapsed is not None
            assert elapsed >= 0

    @pytest.mark.asyncio
    async def test_get_elapsed_ms(self):
        """Test getting elapsed milliseconds."""
        async with RequestContextManager.create_context():
            elapsed_ms = RequestContextManager.get_elapsed_ms()
            assert elapsed_ms is not None
            assert elapsed_ms >= 0


def test_get_request_id_convenience():
    """Test get_request_id convenience function."""
    request_id = get_request_id()
    assert request_id is None  # Outside context


def test_get_request_context_convenience():
    """Test get_request_context convenience function."""
    context = get_request_context()
    assert context is None  # Outside context


@pytest.mark.asyncio
async def test_convenience_functions_in_context():
    """Test convenience functions work in context."""
    async with RequestContextManager.create_context(request_id="test-123"):
        assert get_request_id() == "test-123"

        context = get_request_context()
        assert context is not None
        assert context.request_id == "test-123"

        set_request_metadata("key", "value")
        assert get_request_metadata("key") == "value"
