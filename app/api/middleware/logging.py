"""
API Request Logging Middleware.

Logs all incoming requests and responses for debugging and auditing.

Sandi Metz Principles:
- Single Responsibility: Request/response logging
- Non-intrusive: Doesn't modify request/response
- Configurable: Log levels and fields
"""

import time
import uuid
from dataclasses import dataclass
from typing import Callable, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LoggingConfig:
    """Logging configuration."""

    enabled: bool = True
    log_request_body: bool = False
    log_response_body: bool = False
    log_headers: bool = False
    excluded_paths: List[str] = None  # type: ignore
    max_body_length: int = 1000
    slow_request_threshold_ms: float = 1000.0

    def __post_init__(self):
        if self.excluded_paths is None:
            self.excluded_paths = ["/health", "/healthz", "/ready"]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for request/response logging.

    Logs request details, timing, and response status.
    """

    def __init__(
        self,
        app,
        config: Optional[LoggingConfig] = None,
    ):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            config: Logging configuration
        """
        super().__init__(app)
        self._config = config or LoggingConfig()

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        return str(uuid.uuid4())[:8]

    def _should_log(self, path: str) -> bool:
        """Check if path should be logged."""
        if not self._config.enabled:
            return False
        return path not in self._config.excluded_paths

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "...[truncated]"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with logging.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Generate request ID
        request_id = self._generate_request_id()

        # Check if should log
        if not self._should_log(request.url.path):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Log request
        start_time = time.time()

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params) if request.query_params else None,
            "client": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("User-Agent", "unknown")[:100],
        }

        if self._config.log_headers:
            log_data["headers"] = dict(request.headers)

        logger.info("Request started", **log_data)

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Request failed",
                request_id=request_id,
                duration_ms=round(duration_ms, 2),
                error=str(e),
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        response_log = {
            "request_id": request_id,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }

        # Check for slow requests
        if duration_ms > self._config.slow_request_threshold_ms:
            logger.warning("Slow request detected", **response_log)
        else:
            logger.info("Request completed", **response_log)

        # Add request ID header
        response.headers["X-Request-ID"] = request_id

        return response


# Default configuration
default_logging_config = LoggingConfig(
    enabled=True,
    log_request_body=False,
    log_response_body=False,
    slow_request_threshold_ms=1000.0,
)
