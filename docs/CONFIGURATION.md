# RAG Cache Configuration Guide

## Table of Contents

- [Overview](#overview)
- [Environment Variables](#environment-variables)
- [Application Configuration](#application-configuration)
- [Cache Configuration](#cache-configuration)
- [LLM Provider Configuration](#llm-provider-configuration)
- [Monitoring Configuration](#monitoring-configuration)
- [Security Configuration](#security-configuration)

## Overview

RAG Cache uses environment variables and Pydantic-based configuration for flexible, type-safe settings management. All configuration is validated at startup.

### Configuration Loading Order

1. Default values (hardcoded)
2. `.env` file
3. Environment variables (override `.env`)
4. Command-line arguments (where applicable)

## Environment Variables

### Core Application

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_NAME` | string | `RAG-Cache` | Application name |
| `APP_VERSION` | string | `1.0.0` | Application version |
| `APP_ENV` | string | `development` | Environment: `development`, `staging`, `production` |
| `DEBUG` | bool | `false` | Enable debug mode |
| `LOG_LEVEL` | string | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Server Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `HOST` | string | `0.0.0.0` | Server bind host |
| `PORT` | int | `8000` | Server bind port |
| `WORKERS` | int | `1` | Number of Uvicorn workers |
| `RELOAD` | bool | `false` | Enable auto-reload (dev only) |

### Redis Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_HOST` | string | `localhost` | Redis host |
| `REDIS_PORT` | int | `6379` | Redis port |
| `REDIS_PASSWORD` | string | `""` | Redis password |
| `REDIS_DB` | int | `0` | Redis database number |
| `REDIS_POOL_SIZE` | int | `10` | Connection pool size |
| `REDIS_SOCKET_TIMEOUT` | int | `5` | Socket timeout (seconds) |

### Qdrant Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `QDRANT_HOST` | string | `localhost` | Qdrant host |
| `QDRANT_PORT` | int | `6333` | Qdrant port |
| `QDRANT_API_KEY` | string | `""` | Qdrant API key |
| `QDRANT_COLLECTION_NAME` | string | `ragcache` | Collection name |
| `QDRANT_VECTOR_SIZE` | int | `384` | Vector dimensions |

### LLM Provider Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENAI_API_KEY` | string | *required* | OpenAI API key |
| `ANTHROPIC_API_KEY` | string | `""` | Anthropic API key |
| `DEFAULT_LLM_PROVIDER` | string | `openai` | Default provider |
| `DEFAULT_MODEL` | string | `gpt-3.5-turbo` | Default model |
| `DEFAULT_MAX_TOKENS` | int | `500` | Default max tokens |
| `DEFAULT_TEMPERATURE` | float | `0.7` | Default temperature |

### Cache Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CACHE_TTL` | int | `3600` | Default TTL (seconds) |
| `SEMANTIC_THRESHOLD` | float | `0.85` | Default similarity threshold |
| `MAX_CACHE_SIZE` | int | `10000` | Maximum cache entries |
| `CACHE_ENABLED` | bool | `true` | Enable caching |

### Monitoring Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `METRICS_ENABLED` | bool | `true` | Enable Prometheus metrics |
| `METRICS_PATH` | string | `/metrics` | Metrics endpoint path |
| `HEALTH_CHECK_INTERVAL` | int | `30` | Health check interval (seconds) |

## Application Configuration

### Configuration Class

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with validation."""

    # Application
    app_name: str = "RAG-Cache"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # LLM
    openai_api_key: str
    default_model: str = "gpt-3.5-turbo"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

config = Settings()
```

### Accessing Configuration

```python
from app.config import config

# Access settings
api_key = config.openai_api_key
redis_host = config.redis_host

# Check environment
if config.app_env == "production":
    # Production-specific logic
    pass
```

## Cache Configuration

### TTL Configuration

```python
# Different TTL for different response types
TTL_CONFIG = {
    "default": 3600,           # 1 hour
    "short_lived": 300,        # 5 minutes
    "long_lived": 86400,       # 24 hours
    "permanent": None,         # No expiration
}
```

### Semantic Threshold Tuning

| Threshold | Use Case | Hit Rate | Precision |
|-----------|----------|----------|-----------|
| `0.95` | Strict matching | Low | Very High |
| `0.90` | High precision | Medium | High |
| `0.85` | Balanced (default) | Medium-High | Good |
| `0.80` | Higher hit rate | High | Moderate |
| `0.75` | Maximum coverage | Very High | Lower |

### Example Configuration

```bash
# .env
CACHE_TTL=7200              # 2 hours
SEMANTIC_THRESHOLD=0.88     # Slightly higher precision
MAX_CACHE_SIZE=50000        # Larger cache
```

## LLM Provider Configuration

### OpenAI Models

| Model | Speed | Cost | Quality |
|-------|-------|------|---------|
| `gpt-3.5-turbo` | Fast | Low | Good |
| `gpt-4` | Slow | High | Best |
| `gpt-4-turbo` | Medium | Medium | Very Good |
| `gpt-4o` | Fast | Medium | Very Good |

### Anthropic Models

| Model | Speed | Cost | Quality |
|-------|-------|------|---------|
| `claude-3-5-sonnet` | Medium | Medium | Very Good |
| `claude-3-opus` | Slow | High | Best |
| `claude-3-haiku` | Fast | Low | Good |

### Rate Limiting

```bash
# Provider-specific rate limits
OPENAI_RATE_LIMIT=60         # Requests per minute
ANTHROPIC_RATE_LIMIT=50      # Requests per minute
```

## Monitoring Configuration

### Prometheus Metrics

```bash
# Enable/disable metrics
METRICS_ENABLED=true

# Configure scrape interval
METRICS_SCRAPE_INTERVAL=15s
```

### Alert Thresholds

```bash
# Alert configuration
ALERT_ERROR_RATE_THRESHOLD=0.05      # 5% error rate
ALERT_CACHE_HIT_RATE_MIN=0.20        # Minimum 20% hit rate
ALERT_LLM_LATENCY_MAX_MS=5000        # 5 second max latency
```

## Security Configuration

### API Authentication

```bash
# API key authentication
API_KEY_ENABLED=true
API_KEY=your-secure-api-key

# Allowed API keys (comma-separated)
ALLOWED_API_KEYS=key1,key2,key3
```

### CORS Configuration

```bash
# CORS settings
CORS_ORIGINS=https://app.example.com,https://admin.example.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,DELETE
CORS_ALLOW_HEADERS=*
```

### Rate Limiting

```bash
# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100        # Requests per window
RATE_LIMIT_WINDOW=60           # Window in seconds
```

## Configuration Profiles

### Development

```bash
# .env.development
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG
RELOAD=true
WORKERS=1
CACHE_TTL=300
```

### Staging

```bash
# .env.staging
APP_ENV=staging
DEBUG=false
LOG_LEVEL=INFO
RELOAD=false
WORKERS=2
CACHE_TTL=1800
```

### Production

```bash
# .env.production
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING
RELOAD=false
WORKERS=4
CACHE_TTL=3600
```

## Validation

Configuration is validated at startup:

```python
# Startup validation
try:
    config = Settings()
except ValidationError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)
```

### Common Validation Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `OPENAI_API_KEY required` | Missing API key | Set in `.env` |
| `Invalid port number` | Port out of range | Use 1-65535 |
| `Invalid threshold` | Not 0.0-1.0 | Use valid range |

---

**Last Updated:** November 2025

