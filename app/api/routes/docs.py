"""
API Documentation configuration.

Enhanced OpenAPI documentation for the RAGCache API.

Sandi Metz Principles:
- Single Responsibility: API documentation
- Clear naming: Descriptive tags and descriptions
"""

from typing import Any, Dict

# API Tags metadata for OpenAPI documentation
TAGS_METADATA = [
    {
        "name": "health",
        "description": "Health check endpoints for monitoring service status.",
    },
    {
        "name": "query",
        "description": "Query processing endpoints. Submit queries to get cached or fresh LLM responses.",
    },
    {
        "name": "metrics",
        "description": "Metrics and monitoring endpoints for observability.",
    },
    {
        "name": "cache",
        "description": "Cache management endpoints for cache operations.",
    },
]


# API Description
API_DESCRIPTION = """
# RAGCache API

**Token-efficient RAG caching platform** that reduces LLM API costs by caching and reusing responses.

## Features

- 🚀 **Exact Cache**: Fast Redis-based exact match caching
- 🧠 **Semantic Cache**: Vector similarity search for semantically similar queries
- 💰 **Cost Savings**: Reduce LLM API calls by up to 80%
- ⚡ **Low Latency**: Sub-100ms cache hits
- 📊 **Metrics**: Built-in monitoring and observability

## Authentication

Protected endpoints require an API key passed in the `X-API-Key` header:

```
X-API-Key: your-api-key-here
```

## Rate Limiting

API requests are rate limited to prevent abuse:
- **60 requests per minute** per client
- **1000 requests per hour** per client

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Response Formats

All responses are JSON. Successful responses include:
- `response`: The LLM-generated or cached response
- `cache_info`: Information about cache hit/miss
- `usage`: Token usage metrics
- `latency_ms`: Request processing time

## Error Handling

Errors return appropriate HTTP status codes with details:
- `400`: Bad Request - Invalid input
- `401`: Unauthorized - Missing or invalid API key
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - Unexpected error
- `502`: Bad Gateway - LLM provider error
"""


# Contact information
API_CONTACT = {
    "name": "RAGCache Team",
    "url": "https://github.com/ragcache/ragcache",
    "email": "support@ragcache.io",
}


# License information
API_LICENSE = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT",
}


def get_openapi_config() -> Dict[str, Any]:
    """
    Get OpenAPI configuration.

    Returns:
        OpenAPI configuration dictionary
    """
    return {
        "title": "RAGCache API",
        "description": API_DESCRIPTION,
        "version": "0.1.0",
        "contact": API_CONTACT,
        "license_info": API_LICENSE,
        "openapi_tags": TAGS_METADATA,
        "servers": [
            {"url": "/", "description": "Current server"},
            {"url": "http://localhost:8000", "description": "Local development"},
        ],
    }


# Example request/response for documentation
QUERY_EXAMPLE = {
    "query": "What is machine learning?",
    "use_cache": True,
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "max_tokens": 500,
    "temperature": 0.7,
}

QUERY_RESPONSE_EXAMPLE = {
    "response": "Machine learning is a subset of artificial intelligence...",
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 150,
        "total_tokens": 160,
    },
    "cache_info": {
        "cache_hit": True,
        "cache_type": "semantic",
        "similarity_score": 0.92,
    },
    "latency_ms": 45.2,
}
