"""Test Redis cache service."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.cache.redis_cache import RedisCache
from app.models.cache_entry import CacheEntry


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    repository = AsyncMock()
    return repository


@pytest.fixture
def redis_cache(mock_repository):
    """Create Redis cache with mock repository."""
    return RedisCache(repository=mock_repository)


@pytest.fixture
def sample_entry():
    """Create sample cache entry."""
    return CacheEntry(
        query_hash="test_hash",
        original_query="What is Python?",
        response="Python is a programming language",
        provider="openai",
        model="gpt-3.5-turbo",
        prompt_tokens=10,
        completion_tokens=20,
        embedding=None,
    )


class TestRedisCache:
    """Test Redis cache service."""

    @pytest.mark.asyncio
    async def test_should_get_cached_entry(
        self, redis_cache, mock_repository, sample_entry
    ):
        """Test getting cached entry."""
        mock_repository.fetch.return_value = sample_entry

        result = await redis_cache.get("What is Python?")

        assert result == sample_entry
        mock_repository.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_return_none_when_not_cached(
        self, redis_cache, mock_repository
    ):
        """Test getting non-cached entry."""
        mock_repository.fetch.return_value = None

        result = await redis_cache.get("What is Python?")

        assert result is None
        mock_repository.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_set_cache_entry(
        self, redis_cache, mock_repository, sample_entry
    ):
        """Test setting cache entry."""
        mock_repository.store.return_value = True

        result = await redis_cache.set(sample_entry)

        assert result is True
        mock_repository.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_set_failure(
        self, redis_cache, mock_repository, sample_entry
    ):
        """Test handling cache set failure."""
        mock_repository.store.return_value = False

        result = await redis_cache.set(sample_entry)

        assert result is False
        mock_repository.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_delete_cache_entry(self, redis_cache, mock_repository):
        """Test deleting cache entry."""
        mock_repository.delete.return_value = True

        result = await redis_cache.delete("What is Python?")

        assert result is True
        mock_repository.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_check_if_exists(self, redis_cache, mock_repository):
        """Test checking if entry exists."""
        mock_repository.exists.return_value = True

        result = await redis_cache.exists("What is Python?")

        assert result is True
        mock_repository.exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_check_health(self, redis_cache, mock_repository):
        """Test health check."""
        mock_repository.ping.return_value = True

        result = await redis_cache.health_check()

        assert result is True
        mock_repository.ping.assert_called_once()
