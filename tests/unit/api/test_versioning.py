"""Unit tests for API Versioning."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.versioning import (
    APIVersion,
    VersionedAPIRouter,
    VersionInfo,
    get_version_info,
    validate_version,
)


class TestAPIVersion:
    """Tests for APIVersion enum."""

    def test_v1_value(self):
        """Test V1 version value."""
        assert APIVersion.V1.value == "v1"

    def test_latest_version(self):
        """Test latest returns current version."""
        latest = APIVersion.latest()
        assert latest == APIVersion.V1

    def test_supported_versions(self):
        """Test supported versions list."""
        supported = APIVersion.supported()
        assert APIVersion.V1 in supported

    def test_deprecated_versions(self):
        """Test deprecated versions list."""
        deprecated = APIVersion.deprecated()
        assert isinstance(deprecated, list)


class TestVersionInfo:
    """Tests for VersionInfo model."""

    def test_create_version_info(self):
        """Test creating version info."""
        info = VersionInfo(
            version="v1",
            status="current",
        )

        assert info.version == "v1"
        assert info.status == "current"
        assert info.deprecation_date is None

    def test_version_info_with_dates(self):
        """Test version info with dates."""
        info = VersionInfo(
            version="v0",
            status="deprecated",
            deprecation_date="2024-01-01",
            sunset_date="2024-06-01",
        )

        assert info.deprecation_date == "2024-01-01"
        assert info.sunset_date == "2024-06-01"


class TestVersionedAPIRouter:
    """Tests for VersionedAPIRouter."""

    def test_create_router(self):
        """Test creating versioned router."""
        router = VersionedAPIRouter(prefix="/api")
        assert router._prefix == "/api"

    def test_get_router_creates_on_demand(self):
        """Test get_router creates router on demand."""
        versioned = VersionedAPIRouter()

        v1_router = versioned.get_router(APIVersion.V1)

        assert v1_router is not None
        assert APIVersion.V1 in versioned._routers

    def test_get_router_returns_same_instance(self):
        """Test get_router returns same instance."""
        versioned = VersionedAPIRouter()

        router1 = versioned.get_router(APIVersion.V1)
        router2 = versioned.get_router(APIVersion.V1)

        assert router1 is router2

    def test_routers_property(self):
        """Test routers property returns all routers."""
        versioned = VersionedAPIRouter()
        versioned.get_router(APIVersion.V1)

        routers = versioned.routers

        assert len(routers) == 1


class TestValidateVersion:
    """Tests for validate_version function."""

    def test_valid_version(self):
        """Test validating a valid version."""
        result = validate_version("v1")
        assert result == APIVersion.V1

    def test_invalid_version(self):
        """Test validating an invalid version."""
        with pytest.raises(HTTPException) as exc_info:
            validate_version("v99")

        assert exc_info.value.status_code == 400
        assert "Unsupported API version" in exc_info.value.detail


class TestGetVersionInfo:
    """Tests for get_version_info function."""

    def test_current_version_info(self):
        """Test getting info for current version."""
        info = get_version_info(APIVersion.V1)

        assert info.version == "v1"
        assert info.status == "current"

    def test_deprecated_version_info(self):
        """Test getting info for deprecated version (if any)."""
        # Currently no deprecated versions, but test the function
        info = get_version_info(APIVersion.V1)
        assert info is not None
