"""Test Redis repository."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories.redis_repository import RedisRepository
from app.models.cache_entry import CacheEntry


@pytest.fixture
def mock_pool():
    """Create mock Redis connection pool."""
    return MagicMock()


@pytest.fixture
def redis_repository(mock_pool):
    """Create Redis repository with mock pool."""
    return RedisRepository(pool=mock_pool)


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


class TestRedisRepository:
    """Test Redis repository implementation."""

    @pytest.mark.asyncio
    async def test_should_fetch_entry(self, redis_repository, sample_entry):
        """Test fetching cache entry."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = sample_entry.model_dump_json()

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.fetch("test_key")

            assert result.query_hash == sample_entry.query_hash
            assert result.original_query == sample_entry.original_query
            mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_should_return_none_when_not_found(self, redis_repository):
        """Test fetching non-existent entry."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.fetch("non_existent_key")

            assert result is None

    @pytest.mark.asyncio
    async def test_should_store_entry_with_ttl(self, redis_repository, sample_entry):
        """Test storing cache entry with TTL."""
        mock_redis = AsyncMock()

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.store("test_key", sample_entry, 3600)

            assert result is True
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_store_entry_without_ttl(self, redis_repository, sample_entry):
        """Test storing cache entry without TTL."""
        mock_redis = AsyncMock()

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.store("test_key", sample_entry)

            assert result is True
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_store_error(self, redis_repository, sample_entry):
        """Test handling store errors."""
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = Exception("Store failed")

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.store("test_key", sample_entry, 3600)

            assert result is False

    @pytest.mark.asyncio
    async def test_should_delete_entry(self, redis_repository):
        """Test deleting cache entry."""
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 1

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.delete("test_key")

            assert result is True
            mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_should_handle_delete_not_found(self, redis_repository):
        """Test deleting non-existent entry."""
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 0

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.delete("non_existent_key")

            assert result is False

    @pytest.mark.asyncio
    async def test_should_check_exists(self, redis_repository):
        """Test checking if key exists."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.exists("test_key")

            assert result is True
            mock_redis.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_should_check_not_exists(self, redis_repository):
        """Test checking non-existent key."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.exists("non_existent_key")

            assert result is False

    @pytest.mark.asyncio
    async def test_should_ping_successfully(self, redis_repository):
        """Test successful Redis ping."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.ping()

            assert result is True
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_ping_failure(self, redis_repository):
        """Test handling Redis ping failure."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection failed")

        with patch("app.repositories.redis_repository.Redis") as mock_redis_class:
            mock_redis_class.return_value.__aenter__.return_value = mock_redis

            result = await redis_repository.ping()

            assert result is False
