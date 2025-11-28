"""
API Response Compression Middleware.

Compresses responses using gzip for reduced bandwidth.

Sandi Metz Principles:
- Single Responsibility: Response compression
- Configurable: Min size, compression level
- Efficient: Only compress when beneficial
"""

import gzip
from dataclasses import dataclass
from typing import Callable, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CompressionConfig:
    """Compression configuration."""

    enabled: bool = True
    minimum_size: int = 500  # Minimum response size to compress
    compression_level: int = 6  # 1-9, higher = more compression
    compressible_types: List[str] = None  # type: ignore
    excluded_paths: List[str] = None  # type: ignore

    def __post_init__(self):
        if self.compressible_types is None:
            self.compressible_types = [
                "application/json",
                "text/plain",
                "text/html",
                "text/css",
                "text/javascript",
                "application/javascript",
                "application/xml",
            ]
        if self.excluded_paths is None:
            self.excluded_paths = []


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for response compression.

    Compresses responses using gzip when client supports it.
    """

    def __init__(
        self,
        app,
        config: Optional[CompressionConfig] = None,
    ):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            config: Compression configuration
        """
        super().__init__(app)
        self._config = config or CompressionConfig()

    def _accepts_gzip(self, request: Request) -> bool:
        """Check if client accepts gzip encoding."""
        accept_encoding = request.headers.get("Accept-Encoding", "")
        return "gzip" in accept_encoding.lower()

    def _should_compress(
        self, request: Request, response: Response, body: bytes
    ) -> bool:
        """Determine if response should be compressed."""
        if not self._config.enabled:
            return False

        # Check excluded paths
        if request.url.path in self._config.excluded_paths:
            return False

        # Check client accepts gzip
        if not self._accepts_gzip(request):
            return False

        # Check minimum size
        if len(body) < self._config.minimum_size:
            return False

        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if not any(ct in content_type for ct in self._config.compressible_types):
            return False

        # Don't re-compress already compressed responses
        if response.headers.get("Content-Encoding"):
            return False

        return True

    def _compress(self, body: bytes) -> bytes:
        """Compress body using gzip."""
        return gzip.compress(body, compresslevel=self._config.compression_level)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with compression.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Possibly compressed response
        """
        # Get response
        response = await call_next(request)

        # For streaming responses, we can't easily compress
        # Only compress regular responses
        if hasattr(response, "body"):
            body = response.body

            if self._should_compress(request, response, body):
                compressed = self._compress(body)

                # Only use compressed if smaller
                if len(compressed) < len(body):
                    return Response(
                        content=compressed,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )

        return response


# GZip middleware from Starlette (alternative, simpler approach)
from starlette.middleware.gzip import GZipMiddleware as StarletteGZipMiddleware


def create_gzip_middleware(minimum_size: int = 500):
    """
    Create GZip middleware wrapper.

    Args:
        minimum_size: Minimum response size to compress

    Returns:
        Configured middleware class
    """
    return StarletteGZipMiddleware


# Default configuration
default_compression_config = CompressionConfig(
    enabled=True,
    minimum_size=500,
    compression_level=6,
)
