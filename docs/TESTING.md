# RAG Cache Testing Guide

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [Mocking](#mocking)
- [Fixtures](#fixtures)
- [CI/CD Integration](#cicd-integration)

## Overview

RAG Cache uses **pytest** for testing with a focus on:

- **Unit Tests**: Fast, isolated component tests
- **Integration Tests**: Component interaction tests
- **Coverage Target**: 70%+ coverage

### Testing Philosophy

```
        ┌───────┐
        │  E2E  │ (Few - slow, expensive)
        └───┬───┘
       ┌────▼────┐
       │  Integ  │ (Some - medium speed)
       └────┬────┘
    ┌───────▼───────┐
    │     Unit      │ (Many - fast, cheap)
    └───────────────┘
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── api/                 # API layer tests
│   │   ├── middleware/
│   │   └── routes/
│   ├── services/            # Service tests
│   ├── repositories/        # Repository tests
│   ├── llm/                 # LLM provider tests
│   ├── pipeline/            # Pipeline tests
│   ├── monitoring/          # Monitoring tests
│   └── utils/               # Utility tests
├── integration/             # Integration tests
│   ├── __init__.py
│   ├── test_api_endpoints.py
│   ├── test_cache_flow.py
│   └── test_query_pipeline.py
└── benchmarks/              # Performance tests
    └── test_qdrant_performance.py
```

## Running Tests

### Basic Commands

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run with verbose output
pytest -v

# Run specific file
pytest tests/unit/services/test_query_service.py

# Run specific test
pytest tests/unit/services/test_query_service.py::TestQueryService::test_cache_hit

# Run tests matching pattern
pytest -k "cache"

# Run with coverage
make test-coverage
```

### Pytest Options

```bash
# Stop on first failure
pytest -x

# Show local variables in traceback
pytest -l

# Run previously failed tests
pytest --lf

# Run tests in parallel
pytest -n auto

# Generate HTML report
pytest --html=report.html
```

## Writing Tests

### Unit Test Example

```python
"""Tests for QueryService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.query_service import QueryService
from app.models.query import QueryRequest, QueryResponse


class TestQueryService:
    """Test query service functionality."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        cache = MagicMock()
        cache.get_cached = AsyncMock(return_value=None)
        cache.store = AsyncMock()
        return cache

    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider."""
        provider = MagicMock()
        provider.complete = AsyncMock(return_value=MagicMock(
            content="Test response",
            prompt_tokens=10,
            completion_tokens=20,
        ))
        return provider

    @pytest.fixture
    def service(self, mock_cache_manager, mock_llm_provider):
        """Create service with mocks."""
        return QueryService(
            cache_manager=mock_cache_manager,
            llm_provider=mock_llm_provider,
        )

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(
        self, service, mock_cache_manager
    ):
        """Test cache hit returns cached response."""
        # Arrange
        mock_cache_manager.get_cached.return_value = {
            "response": "Cached response",
            "cache_type": "exact",
        }
        request = QueryRequest(query="What is AI?")

        # Act
        result = await service.process(request)

        # Assert
        assert result.cache_hit is True
        assert result.response == "Cached response"
        mock_cache_manager.get_cached.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_queries_llm(
        self, service, mock_cache_manager, mock_llm_provider
    ):
        """Test cache miss queries LLM."""
        # Arrange
        mock_cache_manager.get_cached.return_value = None
        request = QueryRequest(query="What is AI?")

        # Act
        result = await service.process(request)

        # Assert
        assert result.cache_hit is False
        mock_llm_provider.complete.assert_called_once()
```

### Integration Test Example

```python
"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestQueryEndpoint:
    """Integration tests for query endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_query_endpoint_success(self, client):
        """Test successful query."""
        response = client.post(
            "/api/v1/query",
            json={"query": "What is AI?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "cache_hit" in data

    def test_query_endpoint_validation_error(self, client):
        """Test validation error."""
        response = client.post(
            "/api/v1/query",
            json={"query": ""}  # Empty query
        )

        assert response.status_code == 422

    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "degraded"]
```

### Async Test Pattern

```python
import pytest

class TestAsyncService:
    """Test async service."""

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async operation."""
        result = await some_async_function()
        assert result is not None
```

## Test Coverage

### Running Coverage

```bash
# Generate coverage report
make test-coverage

# HTML report
pytest --cov=app --cov-report=html tests/

# Open report
open htmlcov/index.html
```

### Coverage Configuration

```ini
# pytest.ini
[pytest]
addopts = --cov=app --cov-report=term-missing
testpaths = tests
asyncio_mode = auto
```

### Coverage Requirements

| Component | Minimum Coverage |
|-----------|------------------|
| Services | 80% |
| Repositories | 70% |
| API Routes | 70% |
| Utils | 90% |
| Overall | 70% |

## Mocking

### Mock Patterns

```python
from unittest.mock import MagicMock, AsyncMock, patch

# Simple mock
mock = MagicMock()
mock.method.return_value = "value"

# Async mock
async_mock = AsyncMock()
async_mock.method.return_value = "value"

# Patch decorator
@patch("app.services.query_service.redis_client")
def test_with_patch(mock_redis):
    mock_redis.get.return_value = "cached"
    # Test code

# Patch context manager
with patch("app.config.config") as mock_config:
    mock_config.openai_api_key = "test-key"
    # Test code
```

### Mock Fixtures

```python
# conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    return redis

@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client."""
    qdrant = MagicMock()
    qdrant.search = AsyncMock(return_value=[])
    return qdrant
```

## Fixtures

### Shared Fixtures

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_query_request():
    """Create sample query request."""
    return {
        "query": "What is machine learning?",
        "use_cache": True,
        "semantic_threshold": 0.85,
    }


@pytest.fixture
def sample_cache_entry():
    """Create sample cache entry."""
    return {
        "query_hash": "abc123",
        "query": "What is AI?",
        "response": "AI is...",
        "provider": "openai",
        "model": "gpt-3.5-turbo",
    }
```

### Fixture Scopes

```python
# Function scope (default) - created for each test
@pytest.fixture
def per_test_fixture():
    return SomeResource()

# Class scope - shared within test class
@pytest.fixture(scope="class")
def per_class_fixture():
    return ExpensiveResource()

# Module scope - shared within module
@pytest.fixture(scope="module")
def per_module_fixture():
    return VeryExpensiveResource()

# Session scope - shared across all tests
@pytest.fixture(scope="session")
def per_session_fixture():
    return GlobalResource()
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7.2-alpine
        ports:
          - 6379:6379
      
      qdrant:
        image: qdrant/qdrant:v1.6.1
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: |
          pytest --cov=app --cov-report=xml tests/
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: coverage.xml
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: tests
        entry: pytest tests/unit/ -x
        language: system
        pass_filenames: false
        always_run: true
```

---

**Last Updated:** November 2025

