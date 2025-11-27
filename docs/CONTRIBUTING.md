# Contributing to RAG Cache

Thank you for your interest in contributing to RAG Cache! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Pull Request Process](#pull-request-process)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment. All contributors are expected to:

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Publishing others' private information
- Other conduct which could be considered inappropriate

## Getting Started

### Prerequisites

1. Python 3.11+
2. Docker and Docker Compose
3. Git
4. OpenAI API key (for testing)

### Setup Development Environment

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/RAG-Cache.git
cd RAG-Cache

# 3. Add upstream remote
git remote add upstream https://github.com/original-org/RAG-Cache.git

# 4. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 5. Install dependencies
make install-dev

# 6. Configure environment
cp .env.example .env
# Add your OPENAI_API_KEY

# 7. Start services
make docker-up

# 8. Verify setup
make test
```

### Finding Issues to Work On

- Look for issues labeled `good first issue`
- Check `help wanted` labels
- Ask in discussions before starting major work

## Development Process

### 1. Create a Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Changes

Follow our [Code Standards](#code-standards) while developing.

```bash
# Make your changes
# Write tests
# Update documentation

# Run quality checks
make quality

# Run tests
make test
```

### 3. Commit Changes

We use [Conventional Commits](https://conventionalcommits.org):

```bash
# Format: type(scope): description

# Types:
feat:     New feature
fix:      Bug fix
docs:     Documentation only
style:    Code style (formatting, no logic change)
refactor: Code refactoring
test:     Adding/updating tests
chore:    Maintenance tasks

# Examples:
git commit -m "feat(cache): add semantic cache TTL configuration"
git commit -m "fix(api): handle empty query validation"
git commit -m "docs(readme): update installation instructions"
git commit -m "test(query): add cache hit test cases"
```

### 4. Keep Branch Updated

```bash
git fetch upstream
git rebase upstream/main
```

## Pull Request Process

### Before Submitting

- [ ] All tests pass (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Documentation updated if needed
- [ ] Changelog updated for significant changes

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Follows code style guidelines
```

### Review Process

1. Automated checks must pass
2. At least one maintainer approval required
3. All comments must be addressed
4. Squash merge to main branch

### After Merge

```bash
# Update local main
git checkout main
git pull upstream main

# Delete feature branch
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## Code Standards

### Python Style

We follow PEP 8 with these specifics:

```python
# Line length: 88 characters (Black default)
# Use type hints everywhere
def process_query(query: str, threshold: float = 0.85) -> QueryResponse:
    """Process a query with semantic matching.
    
    Args:
        query: The query text to process
        threshold: Similarity threshold (0.0-1.0)
        
    Returns:
        QueryResponse with result and metadata
        
    Raises:
        ValidationError: If query is invalid
    """
    pass
```

### Sandi Metz Rules

We strictly follow these principles:

1. **Classes < 100 lines** - Split large classes
2. **Methods < 10 lines** - Extract helper methods
3. **< 4 parameters** - Use data classes for more
4. **Descriptive names** - Self-documenting code

### Imports

```python
# Order: stdlib, third-party, local
# Each group separated by blank line
# Use isort for automatic sorting

import asyncio
from typing import Optional

from fastapi import Depends
from pydantic import BaseModel

from app.config import config
from app.services.query_service import QueryService
```

### Error Handling

```python
# Use custom exceptions
from app.exceptions import CacheError, ValidationError

# Specific error handling
try:
    result = await cache.get(key)
except CacheError as e:
    logger.error("Cache error", error=str(e))
    raise
except Exception as e:
    logger.error("Unexpected error", error=str(e))
    raise CacheError(f"Unexpected: {e}") from e
```

### Logging

```python
# Use structured logging
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Good
logger.info("Query processed", 
    query_hash=hash,
    cache_hit=True,
    latency_ms=45
)

# Bad
logger.info(f"Query {query} processed in {latency}ms")
```

## Testing Requirements

### Coverage Requirements

| Component | Minimum |
|-----------|---------|
| Services | 80% |
| Repositories | 70% |
| API Routes | 70% |
| Utils | 90% |
| **Overall** | **70%** |

### Test Structure

```python
"""Tests for QueryService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.query_service import QueryService


class TestQueryService:
    """Query service test cases."""

    @pytest.fixture
    def service(self, mock_cache, mock_llm):
        """Create service with mocks."""
        return QueryService(cache=mock_cache, llm=mock_llm)

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(self, service):
        """Test that cache hit returns cached response."""
        # Arrange
        # Act
        # Assert
```

### Running Tests

```bash
# All tests
make test

# With coverage
make test-coverage

# Specific tests
pytest tests/unit/services/test_query_service.py -v
```

## Documentation

### When to Update Docs

- New features → Update API.md
- Configuration changes → Update CONFIGURATION.md
- New dependencies → Update DEVELOPMENT.md
- Architecture changes → Update ARCHITECTURE.md

### Documentation Style

```markdown
# Use ATX headers (# not underlining)

## Table of Contents at the top

### Code examples with language tags

```python
# Example code
def example():
    pass
```

### Tables for structured information

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
```

### Docstrings

```python
def function_name(param1: str, param2: int = 10) -> dict:
    """Short description of function.
    
    Longer description if needed. Explain what the function
    does, not how it does it.
    
    Args:
        param1: Description of param1
        param2: Description of param2 with default
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        
    Example:
        >>> result = function_name("test")
        >>> print(result)
        {'status': 'ok'}
    """
```

## Questions?

- Open a [GitHub Discussion](https://github.com/org/RAG-Cache/discussions)
- Check existing issues and PRs
- Read the documentation in `/docs`

---

Thank you for contributing to RAG Cache! 🎉

