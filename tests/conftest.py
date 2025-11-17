"""
Pytest configuration and fixtures.

Provides common fixtures for testing.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

# Mock sentence-transformers to avoid heavy PyTorch dependency in tests
# This allows tests to run quickly without downloading/installing torch
mock_sentence_transformer = MagicMock()
mock_sentence_transformer.SentenceTransformer = Mock
sys.modules["sentence_transformers"] = mock_sentence_transformer

from app.config import AppConfig  # noqa: E402


@pytest.fixture
def test_config() -> AppConfig:
    """
    Create test configuration.

    Returns:
        Test configuration instance
    """
    return AppConfig(
        app_env="development",
        redis_host="localhost",
        redis_port=6379,
        qdrant_host="localhost",
        qdrant_port=6333,
        openai_api_key="test-key",
        anthropic_api_key="test-key",
    )


@pytest.fixture
def mock_redis_pool():
    """
    Mock Redis connection pool.

    Returns:
        Mocked Redis pool
    """
    pool = MagicMock()
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def mock_redis_client():
    """
    Mock Redis client.

    Returns:
        Mocked Redis client
    """
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=0)
    return client


@pytest.fixture
def mock_qdrant_client():
    """
    Mock Qdrant client.

    Returns:
        Mocked Qdrant client
    """
    client = MagicMock()
    client.close = AsyncMock()
    client.search = AsyncMock(return_value=[])
    client.upsert = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_embedding_model():
    """
    Mock embedding model.

    Returns:
        Mocked embedding model
    """
    model = MagicMock()
    model.encode = MagicMock(return_value=[[0.1] * 384])
    return model


@pytest.fixture
def sample_query() -> str:
    """
    Sample query for testing.

    Returns:
        Sample query text
    """
    return "What is the capital of France?"


@pytest.fixture
def sample_response() -> str:
    """
    Sample response for testing.

    Returns:
        Sample response text
    """
    return "The capital of France is Paris."


@pytest.fixture
def sample_embedding() -> list:
    """
    Sample embedding vector for testing.

    Returns:
        Sample embedding vector
    """
    return [0.1] * 384
