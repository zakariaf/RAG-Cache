# RAG Cache Development Setup Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Environment](#development-environment)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [IDE Setup](#ide-setup)

## Prerequisites

### Required Software

| Software | Version | Installation |
|----------|---------|--------------|
| Python | 3.11+ | [python.org](https://python.org) |
| Docker | 20.10+ | [docker.com](https://docker.com) |
| Docker Compose | 2.0+ | Included with Docker |
| Git | 2.30+ | [git-scm.com](https://git-scm.com) |
| Make | Any | Pre-installed on macOS/Linux |

### Recommended

| Software | Purpose |
|----------|---------|
| VS Code / PyCharm | IDE |
| Postman / Insomnia | API testing |
| Redis CLI | Cache debugging |

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/RAG-Cache.git
cd RAG-Cache

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
make install-dev

# 4. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 5. Start infrastructure
make docker-up

# 6. Run the application
make run

# 7. Verify
curl http://localhost:8000/health
```

## Development Environment

### Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Deactivate
deactivate
```

### Dependencies

```bash
# Install all dependencies
make install-dev

# Install production only
make install

# Update dependencies
pip install --upgrade -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key

# Optional
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
LOG_LEVEL=DEBUG
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### Docker Services

```bash
# Start Redis and Qdrant
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down

# Clean up (remove volumes)
docker-compose down -v
```

## Project Structure

```
RAG-Cache/
├── app/                      # Application code
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── api/                 # API layer
│   │   ├── routes/          # Endpoint definitions
│   │   ├── middleware/      # Request middleware
│   │   └── deps.py          # Dependency injection
│   ├── services/            # Business logic
│   ├── repositories/        # Data access
│   ├── llm/                 # LLM providers
│   ├── cache/               # Caching layer
│   ├── embeddings/          # Embedding generation
│   ├── pipeline/            # Query processing
│   ├── monitoring/          # Metrics & alerts
│   ├── models/              # Pydantic models
│   ├── exceptions/          # Custom exceptions
│   └── utils/               # Utilities
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── conftest.py          # Pytest fixtures
├── docs/                    # Documentation
├── docker-compose.yml       # Docker services
├── Dockerfile              # Container definition
├── Makefile                # Development commands
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── pytest.ini              # Pytest configuration
└── .env.example            # Environment template
```

## Development Workflow

### Running the Application

```bash
# Development mode (with hot reload)
make dev

# Production mode
make run

# With specific settings
WORKERS=4 LOG_LEVEL=INFO make run
```

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# With coverage
make test-coverage

# Specific test file
pytest tests/unit/test_query_service.py -v

# Specific test
pytest tests/unit/test_query_service.py::TestQueryService::test_cache_hit -v
```

### Code Quality

```bash
# Run all quality checks
make quality

# Format code
make format

# Lint code
make lint

# Type checking
make type-check

# Individual tools
black app tests
isort app tests
flake8 app tests
mypy app
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature
```

## Code Style

### Python Style

We follow PEP 8 with these tools:

- **Black** - Code formatting
- **isort** - Import sorting
- **Flake8** - Linting
- **MyPy** - Type checking

### Commit Messages

Follow [Conventional Commits](https://conventionalcommits.org):

```
feat: add semantic cache support
fix: resolve Redis connection timeout
docs: update API documentation
test: add query service tests
refactor: simplify cache manager
chore: update dependencies
```

### Sandi Metz Rules

1. Classes should be < 100 lines
2. Methods should be < 10 lines
3. Methods should have < 4 parameters
4. Use descriptive naming

## IDE Setup

### VS Code

Install recommended extensions:

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.isort",
    "ms-python.flake8",
    "ms-python.mypy-type-checker",
    "charliermarsh.ruff"
  ]
}
```

Settings:

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### PyCharm

1. Set Python interpreter to `venv/bin/python`
2. Enable Black formatter
3. Configure isort
4. Enable Flake8 inspections
5. Configure MyPy

### Makefile Commands

```bash
make help           # Show all commands
make install        # Install production deps
make install-dev    # Install all deps
make run            # Run application
make dev            # Run with hot reload
make test           # Run all tests
make test-unit      # Run unit tests
make test-coverage  # Run with coverage
make format         # Format code
make lint           # Lint code
make quality        # All quality checks
make docker-up      # Start Docker services
make docker-down    # Stop Docker services
make docker-logs    # View Docker logs
make clean          # Clean build artifacts
```

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -e .
```

**Redis connection failed:**
```bash
# Check Redis is running
docker-compose ps redis
docker-compose logs redis
```

**Tests failing:**
```bash
# Ensure services are running
make docker-up

# Run with verbose output
pytest -v --tb=long
```

---

**Last Updated:** November 2025

