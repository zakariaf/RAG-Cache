"""
Performance optimization module.

Provides utilities for optimizing query processing,
caching, and resource management.
"""

from app.optimization.query_optimizer import (
    QueryOptimizer,
    OptimizationConfig,
)
from app.optimization.cache_optimizer import (
    CacheOptimizer,
    CacheStrategy,
)
from app.optimization.embedding_optimizer import (
    EmbeddingOptimizer,
    BatchEmbeddingProcessor,
)
from app.optimization.connection_pool import (
    ConnectionPoolManager,
    PoolConfig,
)
from app.optimization.async_optimizer import (
    AsyncOptimizer,
    ConcurrencyLimiter,
)
from app.optimization.memory_optimizer import (
    MemoryOptimizer,
    MemoryConfig,
)
from app.optimization.batch_processor import (
    BatchProcessor,
    BatchConfig,
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
