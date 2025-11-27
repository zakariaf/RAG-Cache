# RAG Cache Performance Tuning Guide

## Table of Contents

- [Performance Targets](#performance-targets)
- [Optimization Strategies](#optimization-strategies)
- [Cache Optimization](#cache-optimization)
- [LLM Optimization](#llm-optimization)
- [Infrastructure Optimization](#infrastructure-optimization)
- [Monitoring Performance](#monitoring-performance)
- [Benchmarking](#benchmarking)

## Performance Targets

### Latency Targets

| Metric | Target | Description |
|--------|--------|-------------|
| Cache Hit (Exact) | < 20ms | Redis lookup |
| Cache Hit (Semantic) | < 50ms | Qdrant similarity search |
| Cache Miss (LLM) | < 2000ms | Full LLM round-trip |
| Health Check | < 10ms | Basic health response |

### Throughput Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Requests/second | 100+ | Per worker |
| Concurrent users | 500+ | With connection pooling |
| Cache hit rate | > 50% | For typical workload |

## Optimization Strategies

### 1. Cache-First Architecture

The cache lookup order matters:

```
1. Exact Match (Redis) → Fastest, ~5ms
2. Semantic Match (Qdrant) → Fast, ~30ms
3. LLM Query → Slowest, ~1000ms
```

**Optimization**: Maximize cache hits to minimize LLM calls.

### 2. Connection Pooling

```bash
# Redis connection pool
REDIS_POOL_SIZE=20          # Increase for high concurrency
REDIS_SOCKET_TIMEOUT=5      # Seconds

# Calculate pool size
# Rule: pool_size = (concurrent_requests / workers) * 2
```

### 3. Async Processing

```python
# Good: Parallel cache checks
exact, semantic = await asyncio.gather(
    redis.get(key),
    qdrant.search(embedding)
)

# Bad: Sequential checks
exact = await redis.get(key)
semantic = await qdrant.search(embedding)
```

## Cache Optimization

### Semantic Threshold Tuning

| Threshold | Trade-off |
|-----------|-----------|
| 0.95 | High precision, low hit rate |
| 0.90 | Good precision, moderate hit rate |
| 0.85 | Balanced (recommended) |
| 0.80 | Higher hit rate, some precision loss |
| 0.75 | Maximum hit rate, lower precision |

**Recommendation**: Start at 0.85, adjust based on your use case.

```bash
# Monitor hit rate
curl http://localhost:8000/api/v1/cache/stats | jq '.hit_rate'

# Adjust threshold
SEMANTIC_THRESHOLD=0.82
```

### TTL Optimization

| Use Case | Recommended TTL |
|----------|-----------------|
| Real-time data | 300s (5 min) |
| General knowledge | 3600s (1 hour) |
| Static content | 86400s (24 hours) |
| Reference data | 604800s (1 week) |

```bash
# Configure TTL
CACHE_TTL=7200  # 2 hours
```

### Cache Size Optimization

```bash
# Estimate cache size needed
# Size = unique_queries_per_hour * TTL_hours

# Example: 1000 queries/hour, 24h TTL
MAX_CACHE_SIZE=24000

# Monitor cache size
curl http://localhost:6333/collections/ragcache | jq '.result.points_count'
```

### Redis Optimization

```bash
# Redis configuration
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
tcp-backlog 511
tcp-keepalive 300

# Enable persistence for recovery
save 900 1
save 300 10
save 60 10000
```

### Qdrant Optimization

```bash
# Create payload index for faster filtering
curl -X PUT http://localhost:6333/collections/ragcache/index \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "query_hash",
    "field_schema": "keyword"
  }'

# Optimize collection
curl -X POST http://localhost:6333/collections/ragcache/optimize
```

## LLM Optimization

### Model Selection

| Model | Speed | Cost | Quality |
|-------|-------|------|---------|
| gpt-3.5-turbo | ⚡⚡⚡ | $ | Good |
| gpt-4-turbo | ⚡⚡ | $$ | Very Good |
| gpt-4 | ⚡ | $$$ | Best |
| claude-3-haiku | ⚡⚡⚡ | $ | Good |
| claude-3-5-sonnet | ⚡⚡ | $$ | Very Good |

**Recommendation**: Use `gpt-3.5-turbo` for most queries, fallback to GPT-4 for complex ones.

### Token Optimization

```bash
# Reduce max tokens for faster responses
DEFAULT_MAX_TOKENS=300

# Lower temperature for more deterministic (faster) responses
DEFAULT_TEMPERATURE=0.5
```

### Rate Limiting

```bash
# Avoid hitting API rate limits
OPENAI_RATE_LIMIT=50      # Requests per minute
ANTHROPIC_RATE_LIMIT=40   # Requests per minute

# Implement exponential backoff on errors
```

## Infrastructure Optimization

### Worker Configuration

```bash
# Calculate optimal workers
# Rule: workers = (2 × CPU_cores) + 1

# 4-core machine
WORKERS=9

# Adjust based on monitoring
# High CPU: reduce workers
# Low CPU, slow responses: increase workers
```

### Memory Configuration

```bash
# Per-worker memory estimate
# Base: 200MB + (cache_size × 0.01MB)

# Example: 10000 cache entries
# Memory = 200 + (10000 × 0.01) = 300MB per worker

# Total with 4 workers: 1.2GB
```

### Docker Optimization

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### Network Optimization

```bash
# Use internal Docker network
# Reduce latency between containers

# Keep connections alive
REDIS_SOCKET_KEEPALIVE=true
```

## Monitoring Performance

### Key Metrics

```bash
# Cache performance
curl http://localhost:8000/api/v1/cache/stats | jq '{
  hit_rate: .hit_rate,
  avg_latency: .avg_latency_ms,
  cache_latency: .avg_cache_latency_ms,
  llm_latency: .avg_llm_latency_ms
}'
```

### Prometheus Queries

```promql
# Request rate
rate(ragcache_requests_total[5m])

# Cache hit rate
ragcache_cache_hit_rate

# Request latency p95
histogram_quantile(0.95, 
  rate(ragcache_request_duration_seconds_bucket[5m])
)

# LLM cost rate
rate(ragcache_llm_cost_total[1h])
```

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Cache hit rate | < 30% | < 10% |
| p95 latency | > 2s | > 5s |
| Error rate | > 1% | > 5% |
| Memory usage | > 80% | > 95% |

## Benchmarking

### Load Testing

```bash
# Using wrk
wrk -t12 -c400 -d30s http://localhost:8000/health

# Using hey
hey -n 10000 -c 100 http://localhost:8000/health

# Using ab
ab -n 10000 -c 100 http://localhost:8000/health
```

### Query Benchmarking

```bash
# Benchmark query endpoint
hey -n 1000 -c 50 -m POST \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?"}' \
  http://localhost:8000/api/v1/query
```

### Profiling

```python
# CPU profiling
import cProfile
cProfile.run('process_query(request)')

# Memory profiling
from memory_profiler import profile

@profile
def process_query(request):
    # ...
```

### Performance Regression Tests

```python
# tests/benchmarks/test_performance.py
import pytest
import time

class TestPerformance:
    def test_cache_hit_under_50ms(self, client):
        # Warm cache
        client.post("/api/v1/query", json={"query": "test"})
        
        # Benchmark cache hit
        start = time.time()
        response = client.post("/api/v1/query", json={"query": "test"})
        duration = (time.time() - start) * 1000
        
        assert duration < 50, f"Cache hit took {duration}ms"
```

## Quick Tuning Checklist

- [ ] Set `SEMANTIC_THRESHOLD` to 0.85 (adjust based on hit rate)
- [ ] Set `CACHE_TTL` appropriate for your data freshness needs
- [ ] Configure `WORKERS` based on CPU cores
- [ ] Set `REDIS_POOL_SIZE` for expected concurrency
- [ ] Use `gpt-3.5-turbo` for faster responses
- [ ] Enable Redis persistence for cache durability
- [ ] Create Qdrant indexes for faster queries
- [ ] Monitor and alert on key metrics

---

**Last Updated:** November 2025

