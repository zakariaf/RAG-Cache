# Contributing to RAG Cache

Thank you for your interest in contributing to RAG Cache! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Git
- OpenAI API key (for testing)

### Setting Up Your Development Environment

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/RAG-Cache.git
   cd RAG-Cache
   ```

2. **Create a virtual environment:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   make install-dev
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

5. **Start services:**
   ```bash
   make docker-up
   ```

6. **Verify installation:**
   ```bash
   make test-unit
   ```

## Development Workflow

### Daily Development Routine

```bash
# Morning setup
git pull origin main
make docker-up

# Create feature branch
git checkout -b feature/your-feature-name

# During development
make format           # Format code
make test-unit       # Run unit tests
make commit-check    # Pre-commit validation

# Before committing
make quality         # Full quality checks
make test-coverage   # Ensure coverage requirements

# Commit your changes
git add .
git commit -m "feat: your feature description"

# Push and create PR
git push origin feature/your-feature-name
```

### Available Make Commands

Run `make help` to see all available commands:

- `make dev` - Setup complete development environment
- `make format` - Format code with black and isort
- `make lint` - Run flake8 linter
- `make type-check` - Run mypy type checker
- `make quality` - Run all code quality checks
- `make test` - Run all tests
- `make test-unit` - Run unit tests only
- `make test-coverage` - Run tests with coverage report
- `make commit-check` - Pre-commit checks

## Code Standards

### Sandi Metz Rules (Strictly Enforced)

We follow Sandi Metz's Object-Oriented Design principles:

1. **Class Size:** Maximum 100 lines per class
2. **Method Size:** Maximum 5 lines (ideal), 10 lines (absolute max)
3. **Method Arguments:** Maximum 4 parameters
4. **Naming:** Clear, descriptive, self-documenting names

### Python Style Guide

- **Formatter:** Black (line length 88)
- **Import Sorting:** isort with black profile
- **Linting:** Flake8 with E203, W503 ignored
- **Type Hints:** Required for all function signatures
- **Docstrings:** Required for all public methods and classes

### Example of Good Code Style

```python
from typing import Optional
from pydantic import BaseModel


class CacheEntry(BaseModel):
    """Represents a cached query result.

    Attributes:
        key: Unique identifier for the cache entry
        value: Cached response content
        ttl: Time-to-live in seconds
    """
    key: str
    value: str
    ttl: Optional[int] = 3600

    def is_expired(self, current_time: int) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return current_time > self.created_at + self.ttl
```

### Code Quality Requirements

- **Test Coverage:** Minimum 70% (target 80%+)
- **Type Coverage:** 100% for public APIs
- **Documentation:** All public methods must have docstrings
- **No Warnings:** Zero flake8 warnings allowed
- **Type Safety:** Zero mypy errors allowed

## Testing Requirements

### Test-Driven Development (TDD)

We follow TDD practices:

1. **Write failing test first**
2. **Write minimal code to pass test**
3. **Refactor while keeping tests green**
4. **Repeat**

### Test Structure

```python
# tests/unit/test_cache_repository.py
import pytest
from app.repositories.redis_repository import RedisRepository


class TestRedisRepository:
    """Test suite for RedisRepository."""

    def test_get_returns_value_when_key_exists(self, mock_redis):
        """Test that get returns value for existing key."""
        # Arrange
        repo = RedisRepository(mock_redis)
        mock_redis.get.return_value = b"test_value"

        # Act
        result = repo.get("test_key")

        # Assert
        assert result == "test_value"
        mock_redis.get.assert_called_once_with("test_key")
```

### Test Coverage Requirements

- **Unit Tests:** All business logic must have unit tests
- **Integration Tests:** API endpoints and external service interactions
- **Coverage Threshold:** Minimum 70%, target 80%+
- **Test Naming:** Use descriptive names that explain what is being tested

### Running Tests

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run with coverage report
make test-coverage

# Run specific test file
pytest tests/unit/test_cache_repository.py -v

# Run specific test
pytest tests/unit/test_cache_repository.py::TestRedisRepository::test_get -v
```

## Commit Guidelines

### Commit Message Format

We follow the Conventional Commits specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```bash
# Feature
git commit -m "feat(cache): add semantic similarity matching

Implement cosine similarity calculation for semantic cache
matching using numpy. Includes validation for edge cases.

Closes #42"

# Bug fix
git commit -m "fix(redis): handle connection timeout gracefully

Add retry logic with exponential backoff for Redis connection
failures. Max 3 retries with 2s initial delay.

Fixes #58"

# Documentation
git commit -m "docs(api): update query endpoint documentation

Add examples for semantic_threshold parameter and clarify
cache hit/miss response format."

# Refactor
git commit -m "refactor(llm): extract provider factory pattern

Split provider initialization into factory class to reduce
complexity in main provider class.

Reduces class from 120 to 80 lines per Sandi Metz rules."
```

### Commit Best Practices

- **Small, Focused Commits:** One logical change per commit
- **Present Tense:** Use "add" not "added", "fix" not "fixed"
- **Descriptive Subject:** Clear description of what changed
- **Detailed Body:** Explain why and what, not how
- **Reference Issues:** Use "Closes #123" or "Fixes #456"

## Pull Request Process

### Before Creating a PR

1. **Ensure all tests pass:**
   ```bash
   make test-coverage
   ```

2. **Run quality checks:**
   ```bash
   make quality
   ```

3. **Update documentation** if needed

4. **Rebase on main:**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

### PR Title Format

Use the same format as commit messages:

```
feat(cache): add Redis connection pooling
fix(api): resolve rate limiting edge case
docs(readme): update installation instructions
```

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
- [ ] Coverage meets requirements (70%+)

## Related Issues
Closes #123
Related to #456

## Screenshots (if applicable)
```

### PR Review Process

1. **Automated Checks:** All CI/CD checks must pass
2. **Code Review:** At least one approval required
3. **Testing:** Reviewer should test changes locally
4. **Documentation:** Verify documentation is complete
5. **Merge:** Squash and merge to main branch

### Review Checklist for Reviewers

- [ ] Code follows Sandi Metz principles
- [ ] Tests are comprehensive and passing
- [ ] Type hints are present and correct
- [ ] Documentation is clear and complete
- [ ] No security vulnerabilities introduced
- [ ] Performance implications considered
- [ ] Error handling is robust
- [ ] Logging is appropriate

## Project Structure

```
RAG-Cache/
├── app/                    # Application code
│   ├── main.py            # FastAPI application entry point
│   ├── config.py          # Configuration management
│   ├── api/               # API endpoints
│   ├── cache/             # Cache services
│   ├── llm/               # LLM provider implementations
│   ├── embeddings/        # Embedding generation
│   ├── models/            # Pydantic data models
│   ├── repositories/      # Data access layer
│   ├── services/          # Business logic
│   ├── similarity/        # Similarity matching
│   └── utils/             # Utility functions
│
├── tests/                 # Test suite
│   ├── unit/             # Unit tests (mirror app structure)
│   ├── integration/      # Integration tests
│   ├── mocks/            # Test mocks and fixtures
│   └── conftest.py       # Pytest configuration
│
├── docs/                  # Documentation
│   ├── API.md            # API documentation
│   ├── ARCHITECTURE.md   # Architecture overview
│   └── DEPLOYMENT.md     # Deployment guide
│
├── .github/              # GitHub configuration
│   └── workflows/        # CI/CD workflows
│
├── docker-compose.yml    # Service orchestration
├── Dockerfile            # Container definition
├── Makefile             # Development commands
├── requirements.txt     # Production dependencies
├── requirements-dev.txt # Development dependencies
└── pytest.ini           # Pytest configuration
```

## Architecture Principles

### Dependency Injection

Always use dependency injection instead of hard-coded dependencies:

```python
# Good
class QueryService:
    def __init__(self, cache_repo: CacheRepository):
        self.cache_repo = cache_repo

# Bad
class QueryService:
    def __init__(self):
        self.cache_repo = RedisRepository()  # Hard-coded dependency
```

### Single Responsibility

Each class should have one clear responsibility:

```python
# Good - Single responsibility
class CacheKeyGenerator:
    def generate(self, query: str) -> str:
        return hashlib.sha256(query.encode()).hexdigest()

class CacheRepository:
    def get(self, key: str) -> Optional[str]:
        return self.redis.get(key)

# Bad - Multiple responsibilities
class CacheManager:
    def generate_key_and_get(self, query: str) -> Optional[str]:
        key = hashlib.sha256(query.encode()).hexdigest()
        return self.redis.get(key)
```

### Error Handling

Use specific exceptions and handle errors gracefully:

```python
from app.exceptions import CacheConnectionError, CacheKeyNotFoundError


class RedisRepository:
    def get(self, key: str) -> str:
        try:
            value = self.redis.get(key)
        except ConnectionError as e:
            raise CacheConnectionError(f"Failed to connect: {e}")

        if value is None:
            raise CacheKeyNotFoundError(f"Key not found: {key}")

        return value.decode()
```

## Getting Help

- **Documentation:** Check docs/ folder and README.md
- **Issues:** Search existing issues before creating new ones
- **Discussions:** Use GitHub Discussions for questions
- **Code Examples:** See IMPLEMENTATION_GUIDE.md for patterns

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- Project documentation for major features

Thank you for contributing to RAG Cache! 🚀
