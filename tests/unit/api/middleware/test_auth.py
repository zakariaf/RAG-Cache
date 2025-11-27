"""Unit tests for Authentication Middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.api.middleware.auth import (
    APIKeyAuthenticator,
    AuthConfig,
    AuthenticationError,
    AuthMiddleware,
    AuthType,
    constant_time_compare,
    generate_api_key,
    hash_api_key,
)


class TestAuthConfig:
    """Tests for AuthConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AuthConfig()

        assert config.enabled is False
        assert config.auth_type == AuthType.API_KEY
        assert config.header_name == "X-API-Key"
        assert "/health" in config.excluded_paths

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AuthConfig(
            enabled=True,
            api_keys=["key1", "key2"],
            header_name="Authorization",
        )

        assert config.enabled is True
        assert len(config.api_keys) == 2


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_constant_time_compare_equal(self):
        """Test constant time compare with equal strings."""
        assert constant_time_compare("abc", "abc") is True

    def test_constant_time_compare_not_equal(self):
        """Test constant time compare with different strings."""
        assert constant_time_compare("abc", "def") is False

    def test_constant_time_compare_different_lengths(self):
        """Test constant time compare with different lengths."""
        assert constant_time_compare("abc", "abcd") is False

    def test_hash_api_key_deterministic(self):
        """Test hash is deterministic."""
        key = "test-key"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)

        assert hash1 == hash2

    def test_hash_api_key_different_keys(self):
        """Test different keys produce different hashes."""
        hash1 = hash_api_key("key1")
        hash2 = hash_api_key("key2")

        assert hash1 != hash2

    def test_generate_api_key_format(self):
        """Test generated API key format."""
        key = generate_api_key(prefix="test")

        assert key.startswith("test_")
        assert len(key) > 10

    def test_generate_api_key_unique(self):
        """Test generated keys are unique."""
        keys = [generate_api_key() for _ in range(100)]

        assert len(set(keys)) == 100


class TestAPIKeyAuthenticator:
    """Tests for APIKeyAuthenticator."""

    @pytest.fixture
    def config(self):
        return AuthConfig(
            enabled=True,
            api_keys=["valid-key-1", "valid-key-2"],
        )

    @pytest.fixture
    def authenticator(self, config):
        return APIKeyAuthenticator(config)

    def _create_mock_request(self, path="/api/v1/query", headers=None, query_params=None):
        """Create a mock request with proper method mocking."""
        request = MagicMock()
        request.url.path = path

        _headers = headers or {}
        _query_params = query_params or {}

        request.headers.get = lambda k, default=None: _headers.get(k, default)
        request.query_params.get = lambda k, default=None: _query_params.get(k, default)

        return request

    @pytest.mark.asyncio
    async def test_valid_key_in_header(self, authenticator):
        """Test authentication with valid key in header."""
        request = self._create_mock_request(
            headers={"X-API-Key": "valid-key-1"}
        )

        result = await authenticator.authenticate(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_valid_key_in_query_param(self, authenticator):
        """Test authentication with valid key in query param."""
        request = self._create_mock_request(
            query_params={"api_key": "valid-key-1"}
        )

        result = await authenticator.authenticate(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_missing_key(self, authenticator):
        """Test authentication fails without key."""
        request = self._create_mock_request()

        with pytest.raises(AuthenticationError):
            await authenticator.authenticate(request)

    @pytest.mark.asyncio
    async def test_invalid_key(self, authenticator):
        """Test authentication fails with invalid key."""
        request = self._create_mock_request(
            headers={"X-API-Key": "invalid-key"}
        )

        with pytest.raises(AuthenticationError):
            await authenticator.authenticate(request)

    @pytest.mark.asyncio
    async def test_excluded_path_no_auth_needed(self, authenticator):
        """Test excluded paths don't require auth."""
        request = self._create_mock_request(path="/health")

        result = await authenticator.authenticate(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_disabled_auth_always_passes(self):
        """Test disabled auth always passes."""
        config = AuthConfig(enabled=False)
        authenticator = APIKeyAuthenticator(config)
        request = self._create_mock_request()

        result = await authenticator.authenticate(request)
        assert result is True


class TestAuthMiddleware:
    """Tests for AuthMiddleware."""

    def _create_mock_request(self, path="/api/v1/query", headers=None, query_params=None):
        """Create a mock request."""
        request = MagicMock()
        request.url.path = path

        _headers = headers or {}
        _query_params = query_params or {}

        request.headers.get = lambda k, default=None: _headers.get(k, default)
        request.query_params.get = lambda k, default=None: _query_params.get(k, default)

        return request

    @pytest.mark.asyncio
    async def test_passes_authenticated_request(self):
        """Test middleware passes authenticated requests."""
        mock_app = MagicMock()
        request = self._create_mock_request(headers={"X-API-Key": "valid-key"})

        async def call_next(req):
            return MagicMock()

        config = AuthConfig(enabled=True, api_keys=["valid-key"])
        middleware = AuthMiddleware(mock_app, config=config)

        response = await middleware.dispatch(request, call_next)
        assert response is not None

    @pytest.mark.asyncio
    async def test_blocks_unauthenticated_request(self):
        """Test middleware blocks unauthenticated requests."""
        mock_app = MagicMock()
        request = self._create_mock_request()

        async def call_next(req):
            return MagicMock()

        config = AuthConfig(enabled=True, api_keys=["valid-key"])
        middleware = AuthMiddleware(mock_app, config=config)

        with pytest.raises(AuthenticationError):
            await middleware.dispatch(request, call_next)

