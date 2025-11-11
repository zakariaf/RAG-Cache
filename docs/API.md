# RAG Cache API Documentation

## Overview

The RAG Cache API provides a high-performance caching layer for Language Model (LLM) queries with both exact and semantic matching capabilities. Built with FastAPI, it offers automatic OpenAPI documentation and type-safe endpoints.

## Base URL

```
Development: http://localhost:8000
Production: https://your-domain.com
```

## Interactive Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Authentication

Currently, the API does not require authentication for local development. For production deployment, implement one of the following:

- API Key authentication
- OAuth2 with JWT tokens
- Basic HTTP authentication

See [DEPLOYMENT.md](./DEPLOYMENT.md) for production authentication setup.

## API Endpoints

### Health Check

Check the health status of the service and its dependencies.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-11T10:30:00.000Z",
  "services": {
    "redis": "connected",
    "qdrant": "connected"
  }
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is unhealthy

**Example:**
```bash
curl http://localhost:8000/health
```

---

### Query Processing

Process a query with caching support.

**Endpoint:** `POST /api/v1/query`

**Request Body:**
```json
{
  "query": "What is artificial intelligence?",
  "use_cache": true,
  "semantic_threshold": 0.85,
  "provider": "openai",
  "model": "gpt-3.5-turbo",
  "max_tokens": 500,
  "temperature": 0.7
}
```

**Request Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | - | The query text to process |
| `use_cache` | boolean | No | `true` | Whether to use cache |
| `semantic_threshold` | float | No | `0.85` | Similarity threshold for semantic cache (0.0-1.0) |
| `provider` | string | No | `"openai"` | LLM provider (`openai`, `anthropic`) |
| `model` | string | No | `"gpt-3.5-turbo"` | Model name |
| `max_tokens` | integer | No | `500` | Maximum response tokens |
| `temperature` | float | No | `0.7` | Temperature for response generation (0.0-1.0) |

**Response:**
```json
{
  "query": "What is artificial intelligence?",
  "response": "Artificial intelligence (AI) refers to...",
  "provider": "openai",
  "model": "gpt-3.5-turbo",
  "cache_hit": true,
  "cache_type": "exact",
  "latency_ms": 45,
  "tokens_used": 150,
  "timestamp": "2025-11-11T10:30:00.000Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Original query text |
| `response` | string | Generated or cached response |
| `provider` | string | LLM provider used |
| `model` | string | Model used for generation |
| `cache_hit` | boolean | Whether response was from cache |
| `cache_type` | string | Type of cache hit (`exact`, `semantic`, `none`) |
| `latency_ms` | integer | Response time in milliseconds |
| `tokens_used` | integer | Tokens used (0 if cache hit) |
| `timestamp` | string | Response timestamp (ISO 8601) |

**Status Codes:**
- `200 OK` - Query processed successfully
- `400 Bad Request` - Invalid request parameters
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service dependencies unavailable

**Examples:**

```bash
# Basic query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?"
  }'

# Query with custom parameters
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain neural networks",
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.5,
    "semantic_threshold": 0.90
  }'

# Query without cache
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is deep learning?",
    "use_cache": false
  }'
```

---

### Cache Statistics

Get cache performance statistics.

**Endpoint:** `GET /api/v1/cache/stats`

**Response:**
```json
{
  "total_queries": 1500,
  "cache_hits": 875,
  "cache_misses": 625,
  "hit_rate": 58.33,
  "exact_hits": 500,
  "semantic_hits": 375,
  "avg_latency_ms": 125,
  "avg_cache_latency_ms": 45,
  "avg_llm_latency_ms": 850,
  "tokens_saved": 125000,
  "uptime_seconds": 86400
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `total_queries` | integer | Total queries processed |
| `cache_hits` | integer | Total cache hits |
| `cache_misses` | integer | Total cache misses |
| `hit_rate` | float | Cache hit rate percentage |
| `exact_hits` | integer | Exact cache hits |
| `semantic_hits` | integer | Semantic cache hits |
| `avg_latency_ms` | integer | Average latency |
| `avg_cache_latency_ms` | integer | Average cache hit latency |
| `avg_llm_latency_ms` | integer | Average LLM query latency |
| `tokens_saved` | integer | Total tokens saved by caching |
| `uptime_seconds` | integer | Service uptime |

**Example:**
```bash
curl http://localhost:8000/api/v1/cache/stats
```

---

### Clear Cache

Clear all cached entries (admin operation).

**Endpoint:** `DELETE /api/v1/cache`

**Response:**
```json
{
  "message": "Cache cleared successfully",
  "entries_deleted": 150
}
```

**Status Codes:**
- `200 OK` - Cache cleared successfully
- `500 Internal Server Error` - Failed to clear cache

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/v1/cache
```

---

### Get Cache Entry

Retrieve a specific cache entry by query.

**Endpoint:** `GET /api/v1/cache/entry`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | The query to lookup |

**Response:**
```json
{
  "query": "What is AI?",
  "response": "Artificial intelligence refers to...",
  "created_at": "2025-11-11T10:30:00.000Z",
  "ttl": 3600,
  "hits": 5
}
```

**Status Codes:**
- `200 OK` - Cache entry found
- `404 Not Found` - Cache entry not found

**Example:**
```bash
curl "http://localhost:8000/api/v1/cache/entry?query=What%20is%20AI%3F"
```

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-11-11T10:30:00.000Z"
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_QUERY` | 400 | Query text is empty or invalid |
| `INVALID_THRESHOLD` | 400 | Semantic threshold out of range (0.0-1.0) |
| `PROVIDER_NOT_FOUND` | 400 | Invalid LLM provider specified |
| `CACHE_ERROR` | 500 | Cache service error |
| `LLM_ERROR` | 500 | LLM provider error |
| `SERVICE_UNAVAILABLE` | 503 | Required service unavailable |

### Example Error Response

```json
{
  "detail": "Semantic threshold must be between 0.0 and 1.0",
  "error_code": "INVALID_THRESHOLD",
  "timestamp": "2025-11-11T10:30:00.000Z"
}
```

---

## Rate Limiting

**Current Status:** Not implemented in MVP

**Future Implementation:**
- Rate limiting by IP address
- Rate limiting by API key
- Configurable limits (requests per minute/hour)
- 429 Too Many Requests response

---

## Pagination

**Current Status:** Not applicable for current endpoints

**Future Implementation:**
- Paginated cache history endpoint
- Paginated query logs endpoint

---

## Webhooks

**Current Status:** Not implemented

**Future Implementation:**
- Webhook notifications for cache events
- Configurable webhook endpoints
- Retry logic for failed deliveries

---

## Client Libraries

### Python

```python
import requests

class RAGCacheClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def query(
        self,
        query: str,
        use_cache: bool = True,
        semantic_threshold: float = 0.85,
        provider: str = "openai",
        model: str = "gpt-3.5-turbo"
    ) -> dict:
        """Send a query to the RAG Cache API."""
        response = requests.post(
            f"{self.base_url}/api/v1/query",
            json={
                "query": query,
                "use_cache": use_cache,
                "semantic_threshold": semantic_threshold,
                "provider": provider,
                "model": model
            }
        )
        response.raise_for_status()
        return response.json()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        response = requests.get(f"{self.base_url}/api/v1/cache/stats")
        response.raise_for_status()
        return response.json()

# Usage
client = RAGCacheClient()
result = client.query("What is machine learning?")
print(f"Response: {result['response']}")
print(f"Cache hit: {result['cache_hit']}")
```

### JavaScript/TypeScript

```typescript
class RAGCacheClient {
  constructor(private baseUrl: string = 'http://localhost:8000') {}

  async query(options: {
    query: string;
    useCache?: boolean;
    semanticThreshold?: number;
    provider?: string;
    model?: string;
  }): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/v1/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: options.query,
        use_cache: options.useCache ?? true,
        semantic_threshold: options.semanticThreshold ?? 0.85,
        provider: options.provider ?? 'openai',
        model: options.model ?? 'gpt-3.5-turbo',
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  }

  async getStats(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/v1/cache/stats`);
    return response.json();
  }
}

// Usage
const client = new RAGCacheClient();
const result = await client.query({ query: 'What is machine learning?' });
console.log(`Response: ${result.response}`);
console.log(`Cache hit: ${result.cache_hit}`);
```

### cURL

```bash
# Function to query the API
query_api() {
  local query="$1"
  local provider="${2:-openai}"
  local model="${3:-gpt-3.5-turbo}"

  curl -X POST http://localhost:8000/api/v1/query \
    -H "Content-Type: application/json" \
    -d "{
      \"query\": \"$query\",
      \"provider\": \"$provider\",
      \"model\": \"$model\"
    }"
}

# Usage
query_api "What is machine learning?" "openai" "gpt-4"
```

---

## Performance Considerations

### Latency Targets

- **Cache Hit:** < 50ms
- **Cache Miss (with LLM):** < 1000ms
- **Health Check:** < 10ms

### Caching Strategy

1. **Exact Match:** Check for exact query match in Redis
2. **Semantic Match:** Check for similar queries in Qdrant
3. **LLM Query:** Fall back to LLM if no cache hit
4. **Cache Store:** Store new response in both caches

### Best Practices

1. **Use Caching:** Enable `use_cache` for better performance
2. **Adjust Threshold:** Lower `semantic_threshold` for more cache hits
3. **Batch Queries:** Group similar queries together
4. **Monitor Stats:** Check cache hit rate regularly
5. **Clean Cache:** Periodically clear old entries

---

## Monitoring

### Metrics Endpoints

Future implementation will include Prometheus metrics:

- `/metrics` - Prometheus metrics endpoint
- Counter: `ragcache_queries_total`
- Counter: `ragcache_cache_hits_total`
- Counter: `ragcache_cache_misses_total`
- Histogram: `ragcache_query_duration_seconds`
- Gauge: `ragcache_cache_size`

### Logging

All API requests are logged with:
- Request ID
- Timestamp
- Endpoint
- Status code
- Response time
- Cache hit/miss status

---

## Versioning

The API uses URL-based versioning:

- **Current Version:** v1
- **Base Path:** `/api/v1`

Breaking changes will be introduced in new versions (`/api/v2`, etc.) while maintaining backward compatibility.

---

## Support

For API issues or questions:

1. Check the [interactive documentation](http://localhost:8000/docs)
2. Review [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
3. See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines
4. Open an issue on GitHub for bugs or feature requests

---

## Changelog

### v1.0.0 (Current)

- Initial API release
- Query processing endpoint
- Health check endpoint
- Cache statistics endpoint
- Exact and semantic caching support
- OpenAI provider integration

### Future Versions

- v1.1.0: Add Anthropic provider
- v1.2.0: Add rate limiting
- v1.3.0: Add authentication
- v2.0.0: Breaking changes (TBD)

---

**Last Updated:** November 11, 2025
