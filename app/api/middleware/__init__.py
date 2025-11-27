"""
API Middleware module.

Contains middleware for:
- Rate limiting
- Authentication
- Request logging
- Response compression
"""

from app.api.middleware.auth import (
    APIKeyAuthenticator,
    AuthConfig,
    AuthenticationError,
    AuthMiddleware,
    AuthorizationError,
    AuthType,
    default_auth_config,
    generate_api_key,
)
from app.api.middleware.compression import (
    CompressionConfig,
    CompressionMiddleware,
    create_gzip_middleware,
    default_compression_config,
)
from app.api.middleware.logging import (
    LoggingConfig,
    RequestLoggingMiddleware,
    default_logging_config,
)
from app.api.middleware.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    RateLimitMiddleware,
    default_rate_limit_config,
)

__all__ = [
    # Rate Limiting
    "RateLimitMiddleware",
    "RateLimitConfig",
    "RateLimitExceeded",
    "InMemoryRateLimiter",
    "default_rate_limit_config",
    # Authentication
    "AuthMiddleware",
    "AuthConfig",
    "AuthType",
    "APIKeyAuthenticator",
    "AuthenticationError",
    "AuthorizationError",
    "default_auth_config",
    "generate_api_key",
    # Logging
    "RequestLoggingMiddleware",
    "LoggingConfig",
    "default_logging_config",
    # Compression
    "CompressionMiddleware",
    "CompressionConfig",
    "create_gzip_middleware",
    "default_compression_config",
]

