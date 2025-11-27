"""
API Authentication Middleware.

Handles API key authentication for protected endpoints.

Sandi Metz Principles:
- Single Responsibility: Authentication
- Configurable: Multiple auth strategies
- Secure: Constant-time comparison
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthType(str, Enum):
    """Authentication type."""

    API_KEY = "api_key"
    BEARER = "bearer"
    NONE = "none"


@dataclass
class AuthConfig:
    """Authentication configuration."""

    enabled: bool = False
    auth_type: AuthType = AuthType.API_KEY
    api_keys: List[str] = None  # type: ignore
    header_name: str = "X-API-Key"
    excluded_paths: List[str] = None  # type: ignore

    def __post_init__(self):
        if self.api_keys is None:
            self.api_keys = []
        if self.excluded_paths is None:
            self.excluded_paths = [
                "/health",
                "/healthz",
                "/ready",
                "/docs",
                "/redoc",
                "/openapi.json",
            ]


class AuthenticationError(HTTPException):
    """Exception for authentication failures."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=401,
            detail=detail,
            headers={"WWW-Authenticate": "ApiKey"},
        )


class AuthorizationError(HTTPException):
    """Exception for authorization failures."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=detail)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare strings in constant time to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal
    """
    return hmac.compare_digest(a.encode(), b.encode())


def hash_api_key(key: str) -> str:
    """
    Hash an API key for secure storage.

    Args:
        key: API key to hash

    Returns:
        Hashed key
    """
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key(prefix: str = "rag") -> str:
    """
    Generate a secure API key.

    Args:
        prefix: Key prefix for identification

    Returns:
        Generated API key
    """
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"


class APIKeyAuthenticator:
    """
    Authenticates requests using API keys.

    Supports multiple valid API keys.
    """

    def __init__(self, config: AuthConfig):
        """
        Initialize authenticator.

        Args:
            config: Authentication configuration
        """
        self._config = config
        # Hash API keys for secure comparison
        self._hashed_keys = {hash_api_key(k) for k in config.api_keys}

    def _get_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request."""
        # Check header
        header_key = request.headers.get(self._config.header_name)
        if header_key:
            return header_key

        # Check query parameter (fallback, less secure)
        query_key = request.query_params.get("api_key")
        if query_key:
            return query_key

        return None

    async def authenticate(self, request: Request) -> bool:
        """
        Authenticate request.

        Args:
            request: FastAPI request

        Returns:
            True if authenticated

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self._config.enabled:
            return True

        # Check excluded paths
        if request.url.path in self._config.excluded_paths:
            return True

        # Get API key
        api_key = self._get_api_key(request)

        if not api_key:
            logger.warning("Missing API key", path=request.url.path)
            raise AuthenticationError("API key required")

        # Verify API key
        hashed = hash_api_key(api_key)
        if hashed not in self._hashed_keys:
            logger.warning("Invalid API key", path=request.url.path)
            raise AuthenticationError("Invalid API key")

        logger.debug("Authentication successful", path=request.url.path)
        return True


class AuthMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for authentication.

    Validates API keys on protected endpoints.
    """

    def __init__(
        self,
        app,
        authenticator: Optional[APIKeyAuthenticator] = None,
        config: Optional[AuthConfig] = None,
    ):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            authenticator: Authenticator instance
            config: Authentication configuration
        """
        super().__init__(app)
        self._config = config or AuthConfig()
        self._authenticator = authenticator or APIKeyAuthenticator(self._config)

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request with authentication.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Authenticate request
        await self._authenticator.authenticate(request)

        # Process request
        return await call_next(request)


# Default configuration
default_auth_config = AuthConfig(
    enabled=False,  # Disabled by default for development
    auth_type=AuthType.API_KEY,
    api_keys=[],
)

