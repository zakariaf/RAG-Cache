"""
Performance optimization module.

Provides utilities for optimizing query processing,
caching, and resource management.
"""

from app.optimization.async_optimizer import (
    AsyncOptimizer,
    ConcurrencyLimiter,
)
from app.optimization.batch_processor import (
    BatchConfig,
    BatchProcessor,
)
from app.optimization.cache_optimizer import (
    CacheOptimizer,
    CacheStrategy,
)
from app.optimization.connection_pool import (
    ConnectionPoolManager,
    PoolConfig,
)
from app.optimization.embedding_optimizer import (
    BatchEmbeddingProcessor,
    EmbeddingOptimizer,
)
from app.optimization.memory_optimizer import (
    MemoryConfig,
    MemoryOptimizer,
)
from app.optimization.query_optimizer import (
    OptimizationConfig,
    QueryOptimizer,
)

__all__ = [
    # Query optimization
    "QueryOptimizer",
    "OptimizationConfig",
    # Cache optimization
    "CacheOptimizer",
    "CacheStrategy",
    # Embedding optimization
    "EmbeddingOptimizer",
    "BatchEmbeddingProcessor",
    # Connection pooling
    "ConnectionPoolManager",
    "PoolConfig",
    # Async optimization
    "AsyncOptimizer",
    "ConcurrencyLimiter",
    # Memory optimization
    "MemoryOptimizer",
    "MemoryConfig",
    # Batch processing
    "BatchProcessor",
    "BatchConfig",
]
