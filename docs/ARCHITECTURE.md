# RAG Cache Architecture

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Component Design](#component-design)
- [Data Flow](#data-flow)
- [Design Principles](#design-principles)
- [Technology Stack](#technology-stack)
- [Scalability](#scalability)
- [Security](#security)

## Overview

RAG Cache is a high-performance caching layer for Large Language Model (LLM) queries, designed to reduce latency and token usage through intelligent exact and semantic caching strategies. The system follows Sandi Metz's Object-Oriented Design principles, emphasizing small, focused components with clear responsibilities.

### Key Features

- **Dual-Layer Caching:** Exact matching in Redis + semantic matching in Qdrant
- **Multi-Provider Support:** OpenAI, Anthropic (extensible to more)
- **High Performance:** Sub-50ms cache hits, sub-1s total response time
- **Type Safety:** Full type hints with Pydantic models
- **Test Coverage:** 70%+ test coverage requirement
- **Observability:** Comprehensive logging and metrics

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Application                        │
│                      (Rails, Python, etc.)                       │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP/REST
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Service                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                      API Layer                              │ │
│  │  - /api/v1/query        - Health checks                    │ │
│  │  - /api/v1/cache/stats  - Error handling                   │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐ │
│  │                   Query Service                             │ │
│  │  - Orchestrates cache lookup and LLM queries               │ │
│  │  - Manages query processing pipeline                       │ │
│  └──────┬────────────────────────────────────────┬────────────┘ │
│         │                                         │              │
│  ┌──────▼────────┐                        ┌──────▼────────────┐ │
│  │  Cache Manager│                        │   LLM Provider    │ │
│  │               │                        │     Factory       │ │
│  └──────┬────────┘                        └──────┬────────────┘ │
│         │                                         │              │
│    ┌────┴────┐                            ┌──────┴──────┐       │
│    │         │                            │             │       │
│  ┌─▼──┐   ┌─▼──┐                      ┌──▼───┐    ┌───▼───┐   │
│  │Redis│   │Qdr.│                      │OpenAI│    │Anthro.│   │
│  │Repo │   │Repo│                      │Prov. │    │Prov.  │   │
│  └──┬──┘   └──┬─┘                      └──┬───┘    └───┬───┘   │
└─────┼─────────┼─────────────────────────┼────────────┼─────────┘
      │         │                         │            │
      │         │                         │            │
┌─────▼───┐  ┌──▼──────┐          ┌──────▼─────┐  ┌───▼────────┐
│  Redis  │  │ Qdrant  │          │  OpenAI    │  │ Anthropic  │
│  Cache  │  │ Vector  │          │    API     │  │    API     │
└─────────┘  │   DB    │          └────────────┘  └────────────┘
             └─────────┘
```

### Component Layers

1. **API Layer** (`app/api/`)
   - RESTful endpoints
   - Request validation
   - Response formatting
   - Error handling

2. **Service Layer** (`app/services/`)
   - Business logic
   - Orchestration
   - Query processing pipeline

3. **Repository Layer** (`app/repositories/`)
   - Data access abstraction
   - Cache operations
   - Database queries

4. **Provider Layer** (`app/llm/`)
   - LLM integration
   - Provider abstraction
   - Response standardization

5. **Infrastructure Layer**
   - Redis (exact caching)
   - Qdrant (semantic caching)
   - External APIs

## Component Design

### API Layer

**Location:** `app/api/`

**Responsibilities:**
- Define HTTP endpoints
- Validate incoming requests
- Format responses
- Handle HTTP-specific errors

**Key Components:**

```python
# app/api/endpoints/query.py
@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    query_service: QueryService = Depends(get_query_service)
) -> QueryResponse:
    """Process a query with caching support."""
    return await query_service.process(request)
```

**Design Patterns:**
- Dependency Injection (FastAPI Depends)
- Request/Response Models (Pydantic)
- Router-based organization

---

### Service Layer

**Location:** `app/services/`

**Responsibilities:**
- Implement business logic
- Orchestrate multiple operations
- Manage query processing pipeline
- Track metrics and latency

**Key Components:**

#### QueryService

```python
# app/services/query_service.py
class QueryService:
    """Orchestrates query processing with caching."""

    def __init__(
        self,
        cache_manager: CacheManager,
        llm_factory: LLMProviderFactory
    ):
        self.cache_manager = cache_manager
        self.llm_factory = llm_factory

    async def process(self, request: QueryRequest) -> QueryResponse:
        """Process query with cache-first strategy."""
        # 1. Check exact cache
        # 2. Check semantic cache
        # 3. Query LLM
        # 4. Store in cache
        # 5. Return response
```

#### CacheManager

```python
# app/services/cache_manager.py
class CacheManager:
    """Manages dual-layer cache strategy."""

    def __init__(
        self,
        redis_repo: RedisRepository,
        qdrant_repo: QdrantRepository
    ):
        self.redis_repo = redis_repo
        self.qdrant_repo = qdrant_repo

    async def get_cached_response(
        self, query: str, threshold: float = 0.85
    ) -> Optional[CachedResponse]:
        """Get response from cache (exact or semantic)."""
```

**Design Patterns:**
- Strategy Pattern (cache strategies)
- Factory Pattern (LLM providers)
- Dependency Injection

---

### Repository Layer

**Location:** `app/repositories/`

**Responsibilities:**
- Abstract data access
- Implement CRUD operations
- Handle connection pooling
- Manage transactions

**Key Components:**

#### RedisRepository

```python
# app/repositories/redis_repository.py
class RedisRepository:
    """Redis cache operations."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""

    async def set(
        self, key: str, value: str, ttl: Optional[int] = None
    ) -> bool:
        """Set value with optional TTL."""

    async def delete(self, key: str) -> bool:
        """Delete key."""
```

#### QdrantRepository

```python
# app/repositories/qdrant_repository.py
class QdrantRepository:
    """Qdrant vector operations."""

    def __init__(self, qdrant_client: QdrantClient):
        self.client = qdrant_client

    async def search_similar(
        self, embedding: List[float], threshold: float, limit: int = 5
    ) -> List[SimilarResult]:
        """Search for similar vectors."""

    async def insert(
        self, id: str, embedding: List[float], payload: dict
    ) -> bool:
        """Insert vector with metadata."""
```

**Design Patterns:**
- Repository Pattern
- Connection Pooling
- Error Handling Abstraction

---

### Provider Layer

**Location:** `app/llm/`

**Responsibilities:**
- Abstract LLM provider APIs
- Standardize request/response formats
- Handle provider-specific errors
- Implement retry logic

**Key Components:**

#### Base Provider

```python
# app/llm/base_provider.py
class BaseLLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def generate(
        self, query: str, **kwargs
    ) -> LLMResponse:
        """Generate response from LLM."""

    @abstractmethod
    async def get_embedding(
        self, text: str
    ) -> List[float]:
        """Get text embedding."""
```

#### OpenAI Provider

```python
# app/llm/openai_provider.py
class OpenAIProvider(BaseLLMProvider):
    """OpenAI API integration."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    async def generate(
        self, query: str, **kwargs
    ) -> LLMResponse:
        """Generate response using OpenAI."""
```

**Design Patterns:**
- Abstract Factory Pattern
- Template Method Pattern
- Adapter Pattern

---

### Models Layer

**Location:** `app/models/`

**Responsibilities:**
- Define data structures
- Validate data
- Serialize/deserialize
- Type safety

**Key Models:**

```python
# app/models/query.py
class QueryRequest(BaseModel):
    """Query request model."""
    query: str = Field(..., min_length=1)
    use_cache: bool = Field(default=True)
    semantic_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    provider: str = Field(default="openai")
    model: str = Field(default="gpt-3.5-turbo")

class QueryResponse(BaseModel):
    """Query response model."""
    query: str
    response: str
    cache_hit: bool
    cache_type: str
    latency_ms: int
    tokens_used: int
    timestamp: datetime
```

**Design Patterns:**
- Data Transfer Objects (DTOs)
- Builder Pattern (Pydantic)
- Validation Decorators

---

## Data Flow

### Query Processing Pipeline

```
1. Client Request
   │
   ▼
2. API Endpoint (validation)
   │
   ▼
3. Query Service
   │
   ├─▶ 4a. Check Redis (exact match)
   │   │
   │   ├─▶ Cache Hit ──────┐
   │   │                   │
   │   └─▶ Cache Miss      │
   │       │               │
   │       ▼               │
   │   4b. Check Qdrant    │
   │       (semantic)      │
   │       │               │
   │       ├─▶ Cache Hit ──┤
   │       │               │
   │       └─▶ Cache Miss  │
   │           │           │
   │           ▼           │
   │       5. Query LLM    │
   │           │           │
   │           ▼           │
   │       6. Store Cache  │
   │           │           │
   │           └───────────┤
   │                       │
   ▼                       ▼
7. Format Response
   │
   ▼
8. Return to Client
```

### Detailed Flow

#### 1. Request Validation

```python
# Validate request parameters
request = QueryRequest(**data)  # Pydantic validation
```

#### 2. Cache Lookup

```python
# Try exact match first (fastest)
cached = await redis_repo.get(cache_key)
if cached:
    return format_cached_response(cached, "exact")

# Try semantic match (slower but still fast)
embedding = await get_embedding(query)
similar = await qdrant_repo.search_similar(embedding, threshold)
if similar:
    return format_cached_response(similar[0], "semantic")
```

#### 3. LLM Query

```python
# Cache miss - query LLM
provider = llm_factory.get_provider(request.provider)
response = await provider.generate(
    query=request.query,
    model=request.model,
    temperature=request.temperature
)
```

#### 4. Cache Storage

```python
# Store in both caches for future requests
await redis_repo.set(cache_key, response.text, ttl=3600)
await qdrant_repo.insert(
    id=cache_key,
    embedding=embedding,
    payload={"query": query, "response": response.text}
)
```

#### 5. Response Formatting

```python
return QueryResponse(
    query=query,
    response=response.text,
    cache_hit=False,
    cache_type="none",
    latency_ms=elapsed_ms,
    tokens_used=response.tokens,
    timestamp=datetime.utcnow()
)
```

---

## Design Principles

### Sandi Metz Rules

We strictly follow Sandi Metz's POOD principles:

1. **Classes < 100 lines**
   - Forces single responsibility
   - Improves testability
   - Enhances maintainability

2. **Methods < 5-10 lines**
   - Clear, focused functionality
   - Easy to understand
   - Simple to test

3. **Methods < 4 parameters**
   - Reduces complexity
   - Encourages object composition
   - Improves API clarity

4. **Descriptive naming**
   - Self-documenting code
   - Reduces need for comments
   - Improves readability

### SOLID Principles

- **Single Responsibility:** Each class has one reason to change
- **Open/Closed:** Open for extension, closed for modification
- **Liskov Substitution:** Subtypes must be substitutable
- **Interface Segregation:** Many specific interfaces > one general
- **Dependency Inversion:** Depend on abstractions, not concretions

### Dependency Injection

All dependencies are injected, never instantiated internally:

```python
# Good - Dependencies injected
class QueryService:
    def __init__(
        self,
        cache_manager: CacheManager,
        llm_factory: LLMProviderFactory
    ):
        self.cache_manager = cache_manager
        self.llm_factory = llm_factory

# Bad - Hard-coded dependencies
class QueryService:
    def __init__(self):
        self.cache_manager = CacheManager()  # ❌
        self.llm_factory = LLMProviderFactory()  # ❌
```

### Error Handling

Custom exceptions for different error types:

```python
# app/exceptions.py
class RAGCacheException(Exception):
    """Base exception."""

class CacheConnectionError(RAGCacheException):
    """Cache connection failed."""

class LLMProviderError(RAGCacheException):
    """LLM provider error."""

class ValidationError(RAGCacheException):
    """Request validation error."""
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.11+ | Application code |
| Framework | FastAPI | 0.104.1+ | Web framework |
| Server | Uvicorn | Latest | ASGI server |
| Validation | Pydantic | 2.0+ | Data validation |
| Cache | Redis | 7.2+ | Exact caching |
| Vector DB | Qdrant | 1.6+ | Semantic caching |
| Testing | Pytest | 7.0+ | Test framework |

### Development Tools

| Tool | Purpose |
|------|---------|
| Black | Code formatting |
| isort | Import sorting |
| Flake8 | Linting |
| MyPy | Type checking |
| Coverage.py | Test coverage |
| Docker | Containerization |
| Docker Compose | Service orchestration |

### External Services

| Service | Purpose | Optional |
|---------|---------|----------|
| OpenAI API | LLM responses | No |
| Anthropic API | LLM responses | Yes |
| Prometheus | Metrics (future) | Yes |
| Grafana | Dashboards (future) | Yes |

---

## Scalability

### Horizontal Scaling

The application is designed to scale horizontally:

1. **Stateless API Servers**
   - No server-side state
   - Load balancer distributes requests
   - Easy to add/remove instances

2. **Shared Cache Layer**
   - All instances share Redis
   - All instances share Qdrant
   - Consistent cache across instances

3. **Connection Pooling**
   - Redis connection pool per instance
   - Qdrant connection pool per instance
   - Efficient resource usage

### Vertical Scaling

Optimize single instance performance:

1. **Async/Await**
   - Non-blocking I/O operations
   - High concurrency support
   - Efficient resource usage

2. **Caching Strategy**
   - Fast exact match (Redis)
   - Slower semantic match (Qdrant)
   - Fallback to LLM only when needed

3. **Connection Pooling**
   - Reuse connections
   - Reduce connection overhead
   - Configure pool size based on load

### Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Cache Hit Latency | < 50ms | ~45ms |
| Total Latency | < 1000ms | ~850ms |
| Throughput | 100 req/s | ~80 req/s |
| Cache Hit Rate | > 40% | ~58% |
| Uptime | 99.9% | TBD |

---

## Security

### Current Implementation

1. **Input Validation**
   - Pydantic models validate all inputs
   - Type checking prevents injection
   - Length limits prevent DoS

2. **Error Handling**
   - No sensitive data in error messages
   - Proper exception handling
   - Logging without secrets

3. **Dependencies**
   - Regular dependency updates
   - Security scanning (Bandit, Safety)
   - Minimal dependencies

### Future Enhancements

1. **Authentication**
   - API key authentication
   - JWT token support
   - OAuth2 integration

2. **Rate Limiting**
   - Per-IP rate limiting
   - Per-user rate limiting
   - Configurable limits

3. **Encryption**
   - HTTPS/TLS in production
   - Encrypted cache entries
   - Secure API key storage

4. **Access Control**
   - Role-based access
   - Resource-level permissions
   - Audit logging

---

## Monitoring and Observability

### Logging

Structured logging throughout application:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "query_processed",
    query_hash=query_hash,
    cache_hit=cache_hit,
    latency_ms=latency_ms,
    provider=provider
)
```

### Metrics (Future)

Prometheus metrics:

- `ragcache_queries_total` - Total queries
- `ragcache_cache_hits_total` - Cache hits
- `ragcache_query_duration_seconds` - Query latency
- `ragcache_cache_size` - Cache entry count

### Health Checks

Multiple health check levels:

1. **Basic:** API is responding
2. **Shallow:** Dependencies are reachable
3. **Deep:** Dependencies are functional

---

## Testing Strategy

### Test Pyramid

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

### Test Types

1. **Unit Tests** (`tests/unit/`)
   - Test individual components
   - Mock all dependencies
   - Fast execution (< 1s total)
   - High coverage (80%+)

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - Real Redis and Qdrant instances
   - Medium speed (~10s total)
   - Critical paths only

3. **E2E Tests** (Future)
   - Test complete workflows
   - Full system deployment
   - Slow execution (~60s total)
   - Happy paths and edge cases

---

## Deployment Architecture

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

### Development

```
┌──────────────────────────────────────┐
│      Docker Compose (Local)          │
│  ┌────────┐ ┌────────┐ ┌──────────┐ │
│  │FastAPI │ │ Redis  │ │  Qdrant  │ │
│  └────────┘ └────────┘ └──────────┘ │
└──────────────────────────────────────┘
```

### Production (Future)

```
┌───────────────────────────────────────────────┐
│              Load Balancer                     │
└────────┬─────────────────────────┬────────────┘
         │                         │
    ┌────▼────┐              ┌─────▼───┐
    │FastAPI 1│              │FastAPI 2│
    └────┬────┘              └────┬────┘
         │                        │
         └────────┬───────────────┘
                  │
         ┌────────▼────────┐
         │  Redis Cluster  │
         └─────────────────┘
         ┌─────────────────┐
         │ Qdrant Cluster  │
         └─────────────────┘
```

---

## Future Enhancements

### Phase 1 (MVP+)

- [ ] Anthropic provider
- [ ] Rate limiting
- [ ] API authentication
- [ ] Prometheus metrics

### Phase 2 (Production)

- [ ] Multi-model support
- [ ] Streaming responses
- [ ] Batch query processing
- [ ] Cache warming strategies

### Phase 3 (Advanced)

- [ ] Fine-tuned embeddings
- [ ] Advanced similarity algorithms
- [ ] Multi-tenant support
- [ ] Real-time analytics dashboard

---

## References

### Books

- "Practical Object-Oriented Design" by Sandi Metz
- "Clean Architecture" by Robert C. Martin
- "Designing Data-Intensive Applications" by Martin Kleppmann

### Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Redis Documentation](https://redis.io/docs)
- [Qdrant Documentation](https://qdrant.tech/documentation)
- [Pydantic Documentation](https://docs.pydantic.dev)

### Related Documents

- [API.md](./API.md) - API documentation
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines

---

**Last Updated:** November 11, 2025
