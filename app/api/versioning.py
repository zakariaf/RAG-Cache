"""
API Versioning Implementation.

Handles API version routing and deprecation.

Sandi Metz Principles:
- Single Responsibility: Version management
- Configurable: Multiple version support
- Clean URLs: Version in path prefix
"""

from enum import Enum
from typing import Callable, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class APIVersion(str, Enum):
    """Supported API versions."""

    V1 = "v1"
    V2 = "v2"  # Future version

    @classmethod
    def latest(cls) -> "APIVersion":
        """Get latest API version."""
        return cls.V1  # Update when new versions are added

    @classmethod
    def supported(cls) -> List["APIVersion"]:
        """Get list of supported versions."""
        return [cls.V1]

    @classmethod
    def deprecated(cls) -> List["APIVersion"]:
        """Get list of deprecated versions."""
        return []


class VersionInfo(BaseModel):
    """API version information."""

    version: str = Field(..., description="Version string")
    status: str = Field(..., description="Version status")
    deprecation_date: Optional[str] = Field(None, description="Deprecation date")
    sunset_date: Optional[str] = Field(None, description="Sunset date")


class VersionedAPIRouter:
    """
    Creates versioned API routers.

    Manages routing for multiple API versions.
    """

    def __init__(self, prefix: str = "/api"):
        """
        Initialize versioned router.

        Args:
            prefix: Base API prefix
        """
        self._prefix = prefix
        self._routers: dict[APIVersion, APIRouter] = {}

    def get_router(self, version: APIVersion) -> APIRouter:
        """
        Get or create router for version.

        Args:
            version: API version

        Returns:
            APIRouter for the version
        """
        if version not in self._routers:
            self._routers[version] = APIRouter(prefix=f"{self._prefix}/{version.value}")
        return self._routers[version]

    def include_router(
        self,
        router: APIRouter,
        versions: Optional[List[APIVersion]] = None,
        **kwargs,
    ) -> None:
        """
        Include a router in specified versions.

        Args:
            router: Router to include
            versions: Versions to include in (default: all supported)
            **kwargs: Additional router kwargs
        """
        if versions is None:
            versions = APIVersion.supported()

        for version in versions:
            versioned_router = self.get_router(version)
            versioned_router.include_router(router, **kwargs)

    @property
    def routers(self) -> List[APIRouter]:
        """Get all versioned routers."""
        return list(self._routers.values())


def version_header_dependency(request: Request) -> Optional[str]:
    """
    Extract API version from header.

    Args:
        request: FastAPI request

    Returns:
        Version string or None
    """
    return request.headers.get("X-API-Version")


def validate_version(version: str) -> APIVersion:
    """
    Validate and return API version.

    Args:
        version: Version string

    Returns:
        APIVersion enum value

    Raises:
        HTTPException: If version is invalid
    """
    try:
        api_version = APIVersion(version)

        # Check if deprecated
        if api_version in APIVersion.deprecated():
            logger.warning("Using deprecated API version", version=version)

        return api_version

    except ValueError:
        supported = [v.value for v in APIVersion.supported()]
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported API version: {version}. Supported: {supported}",
        )


def get_version_info(version: APIVersion) -> VersionInfo:
    """
    Get information about a version.

    Args:
        version: API version

    Returns:
        Version information
    """
    if version in APIVersion.deprecated():
        status = "deprecated"
    elif version == APIVersion.latest():
        status = "current"
    else:
        status = "supported"

    return VersionInfo(
        version=version.value,
        status=status,
    )


def deprecation_warning(
    version: APIVersion,
    sunset_date: Optional[str] = None,
) -> Callable:
    """
    Decorator to add deprecation warning to endpoint.

    Args:
        version: Deprecated in this version
        sunset_date: When endpoint will be removed

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            logger.warning(
                "Deprecated endpoint called",
                endpoint=func.__name__,
                version=version.value,
                sunset_date=sunset_date,
            )
            return await func(*args, **kwargs)

        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = f"[DEPRECATED] {func.__doc__}"

        return wrapper

    return decorator
