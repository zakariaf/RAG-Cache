# RAG Cache Troubleshooting Guide

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Issues](#common-issues)
- [Service Issues](#service-issues)
- [Performance Issues](#performance-issues)
- [Cache Issues](#cache-issues)
- [LLM Provider Issues](#llm-provider-issues)
- [Debug Mode](#debug-mode)
- [Getting Help](#getting-help)

## Quick Diagnostics

### Health Check

```bash
# Check overall health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "redis": "connected",
  "qdrant": "connected"
}
```

### Service Status

```bash
# Check Docker services
docker-compose ps

# Check logs
docker-compose logs --tail=50

# Check specific service
docker-compose logs api --tail=100
```

### Metrics Check

```bash
# Get cache statistics
curl http://localhost:8000/api/v1/cache/stats

# Get Prometheus metrics
curl http://localhost:8000/metrics
```

## Common Issues

### 1. Application Won't Start

**Symptoms:**
- Service exits immediately
- Connection refused errors
- Import errors

**Diagnosis:**
```bash
# Check logs
docker-compose logs api

# Check environment
cat .env | grep -v PASSWORD | grep -v KEY
```

**Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing dependencies | `pip install -r requirements.txt` |
| `ValidationError` | Invalid config | Check `.env` values |
| `Address already in use` | Port conflict | Change PORT or stop other service |
| `OPENAI_API_KEY required` | Missing API key | Add to `.env` file |

### 2. Redis Connection Failed

**Symptoms:**
```
ConnectionError: Error connecting to redis://localhost:6379
```

**Diagnosis:**
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
# Should return: PONG

# Check Redis logs
docker-compose logs redis
```

**Solutions:**

```bash
# Restart Redis
docker-compose restart redis

# Check Redis configuration
docker-compose exec redis redis-cli CONFIG GET maxclients

# Increase connection limit if needed
docker-compose exec redis redis-cli CONFIG SET maxclients 10000
```

### 3. Qdrant Connection Failed

**Symptoms:**
```
ConnectionError: Cannot connect to Qdrant at localhost:6333
```

**Diagnosis:**
```bash
# Check Qdrant is running
docker-compose ps qdrant

# Test connection
curl http://localhost:6333/health

# Check logs
docker-compose logs qdrant
```

**Solutions:**

```bash
# Restart Qdrant
docker-compose restart qdrant

# Check disk space (Qdrant needs space for vectors)
df -h

# Recreate collection if corrupted
curl -X DELETE http://localhost:6333/collections/ragcache
```

### 4. API Returns 500 Error

**Symptoms:**
- Internal Server Error responses
- Error logs showing exceptions

**Diagnosis:**
```bash
# Check API logs with debug level
LOG_LEVEL=DEBUG docker-compose up api

# Check specific request
curl -v http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

**Solutions:**

| Error Type | Likely Cause | Solution |
|------------|--------------|----------|
| `LLMProviderError` | API key issue | Check `OPENAI_API_KEY` |
| `CacheError` | Redis/Qdrant down | Restart services |
| `ValidationError` | Invalid input | Check request format |
| `TimeoutError` | Slow LLM | Increase timeout |

### 5. Slow Response Times

**Symptoms:**
- Responses taking > 5 seconds
- Timeout errors

**Diagnosis:**
```bash
# Check cache hit rate
curl http://localhost:8000/api/v1/cache/stats | jq '.hit_rate'

# Check latency breakdown
curl http://localhost:8000/api/v1/cache/stats | jq '{
  avg_latency: .avg_latency_ms,
  cache_latency: .avg_cache_latency_ms,
  llm_latency: .avg_llm_latency_ms
}'
```

**Solutions:**

See [Performance Issues](#performance-issues) section.

## Service Issues

### Redis Issues

**Too many connections:**
```bash
# Check current connections
docker-compose exec redis redis-cli CLIENT LIST | wc -l

# Kill idle connections
docker-compose exec redis redis-cli CLIENT KILL TYPE normal

# Reduce pool size in .env
REDIS_POOL_SIZE=5
```

**Memory issues:**
```bash
# Check memory usage
docker-compose exec redis redis-cli INFO memory

# Set memory limit
docker-compose exec redis redis-cli CONFIG SET maxmemory 1gb
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Qdrant Issues

**Collection not found:**
```bash
# List collections
curl http://localhost:6333/collections

# Create collection
curl -X PUT http://localhost:6333/collections/ragcache \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {"size": 384, "distance": "Cosine"}
  }'
```

**Vector dimension mismatch:**
```bash
# Check collection info
curl http://localhost:6333/collections/ragcache

# Delete and recreate with correct size
curl -X DELETE http://localhost:6333/collections/ragcache
# Then restart application to recreate
```

## Performance Issues

### Low Cache Hit Rate

**Diagnosis:**
```bash
curl http://localhost:8000/api/v1/cache/stats | jq '.hit_rate'
```

**Solutions:**

| Hit Rate | Action |
|----------|--------|
| < 10% | Lower `SEMANTIC_THRESHOLD` to 0.80 |
| 10-30% | Check query diversity, may be normal |
| 30-60% | Good, optimize with longer TTL |
| > 60% | Excellent, cache working well |

**Configuration changes:**
```bash
# Lower semantic threshold
SEMANTIC_THRESHOLD=0.80

# Increase cache TTL
CACHE_TTL=7200

# Increase cache size
MAX_CACHE_SIZE=50000
```

### High Latency

**Diagnosis:**
```bash
# Check which phase is slow
curl http://localhost:8000/api/v1/cache/stats

# If avg_cache_latency_ms high: Redis/Qdrant issue
# If avg_llm_latency_ms high: LLM provider issue
```

**Solutions:**

For Redis latency:
```bash
# Check Redis performance
docker-compose exec redis redis-cli --latency

# Optimize pool size
REDIS_POOL_SIZE=20
```

For Qdrant latency:
```bash
# Check collection size
curl http://localhost:6333/collections/ragcache | jq '.result.points_count'

# Create index for faster search
curl -X PUT http://localhost:6333/collections/ragcache/index \
  -H "Content-Type: application/json" \
  -d '{"field_name": "query_hash", "field_schema": "keyword"}'
```

For LLM latency:
```bash
# Use faster model
DEFAULT_MODEL=gpt-3.5-turbo

# Reduce max tokens
DEFAULT_MAX_TOKENS=300
```

### Memory Issues

**Diagnosis:**
```bash
# Check container memory
docker stats

# Check Python memory
curl http://localhost:8000/api/v1/cache/stats | jq '.memory_usage_mb'
```

**Solutions:**
```bash
# Reduce worker count
WORKERS=2

# Reduce cache size
MAX_CACHE_SIZE=5000

# Add memory limits to docker-compose
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1G
```

## Cache Issues

### Cache Not Working

**Diagnosis:**
```bash
# Check if caching is enabled
curl http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "use_cache": true}' | jq '.cache_hit'

# Second request should be cache hit
curl http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "use_cache": true}' | jq '.cache_hit'
```

**Solutions:**
```bash
# Check Redis has data
docker-compose exec redis redis-cli KEYS "query:*" | head

# Check Qdrant has data
curl http://localhost:6333/collections/ragcache | jq '.result.points_count'

# Clear and rebuild cache
curl -X DELETE http://localhost:8000/api/v1/cache
```

### Stale Cache Data

**Symptoms:**
- Outdated responses
- Incorrect information

**Solutions:**
```bash
# Clear all cache
curl -X DELETE http://localhost:8000/api/v1/cache

# Reduce TTL for fresher data
CACHE_TTL=1800  # 30 minutes

# Force bypass cache for specific query
curl http://localhost:8000/api/v1/query \
  -d '{"query": "test", "use_cache": false}'
```

## LLM Provider Issues

### OpenAI Errors

**Rate limit exceeded:**
```
Error: Rate limit exceeded
```

```bash
# Wait and retry
# Or reduce request rate
OPENAI_RATE_LIMIT=30  # Requests per minute
```

**Invalid API key:**
```
Error: Invalid API key
```

```bash
# Check API key is set
echo $OPENAI_API_KEY | head -c 10

# Verify key format (should start with sk-)
# Regenerate key at platform.openai.com
```

**Model not available:**
```
Error: Model not found
```

```bash
# Check model name
DEFAULT_MODEL=gpt-3.5-turbo

# List available models at platform.openai.com
```

### Anthropic Errors

**Similar issues apply:**
```bash
# Check API key
echo $ANTHROPIC_API_KEY | head -c 10

# Use correct model name
DEFAULT_MODEL=claude-3-5-sonnet-20241022
```

## Debug Mode

### Enable Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG

# Or via environment
LOG_LEVEL=DEBUG docker-compose up api
```

### Debug Specific Components

```python
# Add to code temporarily
import logging
logging.getLogger("app.services.query_service").setLevel(logging.DEBUG)
```

### Interactive Debugging

```bash
# Run with debugger
python -m debugpy --listen 5678 -m uvicorn app.main:app

# Connect VS Code debugger to port 5678
```

## Getting Help

### Before Asking for Help

1. Check this troubleshooting guide
2. Check application logs
3. Verify environment configuration
4. Try to reproduce with minimal example

### Reporting Issues

Include in your issue:

```markdown
## Environment
- OS: macOS 14 / Ubuntu 22.04 / Windows 11
- Python: 3.11.x
- Docker: 20.10.x

## Configuration
- CACHE_TTL: 3600
- SEMANTIC_THRESHOLD: 0.85
(redact API keys!)

## Steps to Reproduce
1. Start application
2. Send request
3. See error

## Expected Behavior
Description of what should happen

## Actual Behavior
Description of what happened

## Logs
```
Relevant log output
```

## Additional Context
Any other relevant information
```

---

**Last Updated:** November 2025

