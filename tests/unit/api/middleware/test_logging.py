"""Unit tests for Request Logging Middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.middleware.logging import (
    LoggingConfig,
    RequestLoggingMiddleware,
)


class TestLoggingConfig:
    """Tests for LoggingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LoggingConfig()

        assert config.enabled is True
        assert config.log_request_body is False
        assert config.log_response_body is False
        assert config.slow_request_threshold_ms == 1000.0
        assert "/health" in config.excluded_paths

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LoggingConfig(
            enabled=False,
            log_request_body=True,
            slow_request_threshold_ms=500.0,
        )

        assert config.enabled is False
        assert config.log_request_body is True
        assert config.slow_request_threshold_ms == 500.0


class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""

    def _create_mock_request(self, path="/api/v1/query"):
        """Create a mock request."""
        request = MagicMock()
        request.method = "POST"
        request.url.path = path
        request.query_params = {}
        request.client.host = "127.0.0.1"

        _headers = {"User-Agent": "test-agent"}
        request.headers.get = lambda k, default="": _headers.get(k, default)

        return request

    async def _call_next(self, request):
        """Mock call_next function."""
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        return response

    @pytest.fixture
    def middleware(self):
        mock_app = MagicMock()
        config = LoggingConfig(enabled=True)
        return RequestLoggingMiddleware(mock_app, config=config)

    @pytest.mark.asyncio
    async def test_adds_request_id_header(self, middleware):
        """Test middleware adds X-Request-ID header."""
        request = self._create_mock_request()
        response = await middleware.dispatch(request, self._call_next)

        assert "X-Request-ID" in response.headers

    @pytest.mark.asyncio
    async def test_request_id_format(self, middleware):
        """Test request ID has correct format."""
        request = self._create_mock_request()
        response = await middleware.dispatch(request, self._call_next)

        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 8  # 8 character UUID prefix

    @pytest.mark.asyncio
    async def test_skips_excluded_paths(self, middleware):
        """Test middleware skips excluded paths."""
        request = self._create_mock_request(path="/health")
        response = await middleware.dispatch(request, self._call_next)

        # Should still add request ID
        assert "X-Request-ID" in response.headers

    @pytest.mark.asyncio
    async def test_disabled_still_processes_request(self):
        """Test disabled middleware still processes requests."""
        mock_app = MagicMock()
        config = LoggingConfig(enabled=False)
        middleware = RequestLoggingMiddleware(mock_app, config=config)

        request = self._create_mock_request()
        response = await middleware.dispatch(request, self._call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.api.middleware.logging.logger")
    async def test_logs_request_start(self, mock_logger, middleware):
        """Test middleware logs request start."""
        request = self._create_mock_request()
        await middleware.dispatch(request, self._call_next)

        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    @patch("app.api.middleware.logging.logger")
    async def test_logs_request_completion(self, mock_logger, middleware):
        """Test middleware logs request completion."""
        request = self._create_mock_request()
        await middleware.dispatch(request, self._call_next)

        # Should have at least 2 info calls (start and complete)
        assert mock_logger.info.call_count >= 2

    @pytest.mark.asyncio
    @patch("app.api.middleware.logging.logger")
    async def test_logs_error_on_exception(self, mock_logger, middleware):
        """Test middleware logs errors on exceptions."""
        request = self._create_mock_request()

        async def failing_call_next(request):
            raise Exception("Test error")

        with pytest.raises(Exception):
            await middleware.dispatch(request, failing_call_next)

        mock_logger.error.assert_called()

    def test_truncate_short_text(self, middleware):
        """Test truncate with short text."""
        result = middleware._truncate("short", 100)
        assert result == "short"

    def test_truncate_long_text(self, middleware):
        """Test truncate with long text."""
        result = middleware._truncate("a" * 200, 100)
        assert len(result) <= 120  # 100 + truncation marker
        assert "[truncated]" in result

    def test_should_log_regular_path(self, middleware):
        """Test _should_log returns True for regular paths."""
        assert middleware._should_log("/api/v1/query") is True

    def test_should_log_excluded_path(self, middleware):
        """Test _should_log returns False for excluded paths."""
        assert middleware._should_log("/health") is False

    def test_generate_request_id(self, middleware):
        """Test request ID generation."""
        id1 = middleware._generate_request_id()
        id2 = middleware._generate_request_id()

        assert id1 != id2
        assert len(id1) == 8
