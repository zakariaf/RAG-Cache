# RAG Cache

A high-performance caching layer for Large Language Model (LLM) queries with exact and semantic matching capabilities.

## 🎯 What is RAG Cache?

RAG Cache sits between your application and LLM providers (OpenAI, Anthropic) to:

- **💰 Save Money** - Avoid paying for duplicate queries
- **⚡ Reduce Latency** - Return cached responses in ~2ms instead of ~10 seconds
- **🛡️ Increase Reliability** - Reduce dependency on external APIs

### How It Works

```
User Query → Exact Match (Redis) → Semantic Match (Qdrant) → LLM (if needed)
                   ↓                       ↓
              ~2ms hit               ~50ms hit              ~10,000ms
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone <your-repo>
cd "Rag cache"

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start Redis & Qdrant
docker-compose up -d redis qdrant

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0"
}
```

## 📡 API Usage

### Query Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "use_cache": true
  }'
```

**First Request (Cache Miss):**
```json
{
  "response": "Machine learning is a subset of AI...",
  "provider": "openai",
  "model": "gpt-4o-mini-2024-07-18",
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 418,
    "total_tokens": 430
  },
  "cache_info": {
    "cache_hit": false,
    "cache_type": null
  },
  "latency_ms": 10090.93
}
```

**Second Request (Cache Hit):**
```json
{
  "response": "Machine learning is a subset of AI...",
  "cache_info": {
    "cache_hit": true,
    "cache_type": "exact"
  },
  "latency_ms": 2.03
}
```

### Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI documentation |
| `/api/v1/query` | POST | Process query with caching |
| `/api/v1/metrics` | GET | Application metrics |
| `/api/v1/metrics/prometheus` | GET | Prometheus format metrics |

## 📊 Real Performance Tests

Tests performed on November 27, 2025:

### Cache Hit Performance

| Test | Latency | Improvement |
|------|---------|-------------|
| First Query (Cache Miss) | 10,090ms | - |
| Second Query (Cache Hit) | 2.03ms | **4,970x faster** |
| Cached Query Avg (5 runs) | 2.11ms | **4,782x faster** |

### Batch Performance (5 Cached Queries)

```
Query 1: 1.06ms
Query 2: 1.64ms
Query 3: 2.63ms
Query 4: 3.62ms
Query 5: 1.62ms
Average: 2.11ms
```

### Cache Bypass Test

| Mode | Latency |
|------|---------|
| With Cache (hit) | 0.71ms |
| Without Cache (bypass) | 7,870ms |

## 📈 Metrics

```bash
curl http://localhost:8000/api/v1/metrics
```

```json
{
  "application": {
    "name": "RAGCache",
    "environment": "development",
    "version": "0.1.0"
  },
  "pipeline": {
    "total_requests": 0,
    "cache_hits": 0,
    "cache_hit_rate": 0.0,
    "avg_latency_ms": 0.0
  },
  "cache": {
    "total_keys": 286,
    "memory_used_bytes": 1585248,
    "hits": 2,
    "misses": 2032,
    "hit_rate": 0.1
  },
  "config": {
    "semantic_cache_enabled": true,
    "exact_cache_enabled": true,
    "similarity_threshold": 0.85,
    "cache_ttl_seconds": 3600
  }
}
```

### Prometheus Metrics

```bash
curl http://localhost:8000/api/v1/metrics/prometheus
```

```
# HELP ragcache_info Application information
# TYPE ragcache_info gauge
ragcache_info{version="0.1.0",environment="development"} 1

# HELP ragcache_requests_total Total requests processed
# TYPE ragcache_requests_total counter
ragcache_requests_total 0

# HELP ragcache_cache_hits_total Total cache hits
# TYPE ragcache_cache_hits_total counter
ragcache_cache_hits_total 0

# HELP ragcache_redis_keys Total Redis keys
# TYPE ragcache_redis_keys gauge
ragcache_redis_keys 283
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Application                              │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAG Cache (FastAPI)                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Query Service                          │   │
│  │  1. Check Redis (exact match)                             │   │
│  │  2. Check Qdrant (semantic match)                         │   │
│  │  3. Call LLM if no cache hit                              │   │
│  │  4. Store response in cache                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────┐   │
│  │   Redis    │  │   Qdrant   │  │    LLM Providers         │   │
│  │  (Exact)   │  │ (Semantic) │  │  OpenAI / Anthropic      │   │
│  └────────────┘  └────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key (required) |
| `ANTHROPIC_API_KEY` | - | Anthropic API key (optional) |
| `REDIS_HOST` | `localhost` | Redis host |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `SEMANTIC_SIMILARITY_THRESHOLD` | `0.85` | Similarity threshold (0.0-1.0) |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL in seconds |
| `DEFAULT_MODEL` | `gpt-3.5-turbo` | Default LLM model |

## 📁 Project Structure

```
app/
├── api/              # FastAPI routes & middleware
│   ├── routes/       # API endpoints
│   └── middleware/   # Auth, rate limiting, logging
├── cache/            # Redis & Qdrant clients
├── llm/              # LLM provider integrations
│   ├── openai_provider.py
│   └── anthropic_provider.py
├── embeddings/       # Text embedding generation
├── pipeline/         # Query processing pipeline
├── monitoring/       # Prometheus metrics & alerts
├── optimization/     # Performance optimization
├── models/           # Pydantic data models
├── services/         # Business logic
└── utils/            # Utilities (logger, hasher)
```

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/unit/test_config.py -v
```

## 🐳 Docker

### Start Services

```bash
# Start all services
docker-compose up -d

# Start only Redis and Qdrant
docker-compose up -d redis qdrant

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Deployment

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Or use deployment script
./scripts/deploy.sh production
```

## 💰 Cost Savings Example

| Scenario | Without Cache | With Cache (50% hit rate) |
|----------|---------------|---------------------------|
| 10,000 queries/day | ~$50/day | ~$25/day |
| Average latency | ~10,000ms | ~5,000ms |
| P95 latency | ~15,000ms | ~2ms (cache hit) |

## 📚 Documentation

- [API Documentation](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [Testing Guide](docs/TESTING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Security Best Practices](docs/SECURITY.md)
- [Performance Tuning](docs/PERFORMANCE.md)

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11 |
| Framework | FastAPI |
| Exact Cache | Redis 7.2 |
| Semantic Cache | Qdrant 1.6 |
| LLM Providers | OpenAI, Anthropic |
| Embeddings | sentence-transformers |
| Testing | pytest |
| Containerization | Docker |

## 🤝 Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - See [LICENSE](LICENSE) file.

---

**Built with ❤️ following Sandi Metz's POOD principles**
