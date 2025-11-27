"""
Memory usage optimization.

Sandi Metz Principles:
- Single Responsibility: Memory management
- Small methods: Each optimization isolated
- Observable: Memory metrics tracking
"""

import gc
import sys
import weakref
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class MemoryConfig:
    """Memory optimization configuration."""

    # Thresholds (in MB)
    warning_threshold_mb: int = 512
    critical_threshold_mb: int = 1024
    
    # GC settings
    enable_gc_optimization: bool = True
    gc_threshold_mb: int = 256
    gc_interval_operations: int = 1000
    
    # Cache settings
    max_cache_items: int = 10000
    cache_item_max_size_kb: int = 100
    
    # Object pooling
    enable_object_pooling: bool = True
    pool_max_size: int = 100


@dataclass
class MemoryStats:
    """Memory statistics."""

    current_mb: float = 0.0
    peak_mb: float = 0.0
    gc_collections: int = 0
    objects_tracked: int = 0
    cache_memory_mb: float = 0.0


class MemoryOptimizer:
    """
    Optimizes memory usage through various strategies.

    Monitors memory and triggers cleanup when needed.
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        """
        Initialize optimizer.

        Args:
            config: Memory configuration
        """
        self._config = config or MemoryConfig()
        self._stats = MemoryStats()
        self._operation_count = 0
        self._tracked_objects: weakref.WeakSet = weakref.WeakSet()
        self._object_pools: Dict[str, List[Any]] = {}

    def track_memory(self) -> float:
        """
        Track current memory usage.

        Returns:
            Current memory usage in MB
        """
        # Get process memory (approximate)
        import os
        try:
            # Try to use resource module (Unix)
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            memory_mb = usage.ru_maxrss / 1024  # KB to MB on macOS
            if sys.platform == "linux":
                memory_mb = usage.ru_maxrss / 1024  # Already in KB on Linux
        except ImportError:
            # Fallback: estimate from gc
            memory_mb = sum(
                sys.getsizeof(obj) for obj in gc.get_objects()
            ) / (1024 * 1024)

        self._stats.current_mb = memory_mb
        if memory_mb > self._stats.peak_mb:
            self._stats.peak_mb = memory_mb

        self._check_thresholds(memory_mb)
        return memory_mb

    def _check_thresholds(self, memory_mb: float) -> None:
        """Check memory against thresholds."""
        if memory_mb >= self._config.critical_threshold_mb:
            logger.error(
                "Critical memory usage",
                memory_mb=memory_mb,
                threshold=self._config.critical_threshold_mb
            )
            self.force_cleanup()
        elif memory_mb >= self._config.warning_threshold_mb:
            logger.warning(
                "High memory usage",
                memory_mb=memory_mb,
                threshold=self._config.warning_threshold_mb
            )

    def maybe_gc(self) -> bool:
        """
        Run garbage collection if needed.

        Returns:
            True if GC was run
        """
        if not self._config.enable_gc_optimization:
            return False

        self._operation_count += 1

        # Check interval
        if self._operation_count % self._config.gc_interval_operations != 0:
            return False

        # Check memory threshold
        current = self.track_memory()
        if current < self._config.gc_threshold_mb:
            return False

        return self.force_gc()

    def force_gc(self) -> bool:
        """
        Force garbage collection.

        Returns:
            True if collection ran
        """
        collected = gc.collect()
        self._stats.gc_collections += 1

        logger.debug(
            "Garbage collection completed",
            objects_collected=collected
        )

        return True

    def force_cleanup(self) -> None:
        """Force aggressive memory cleanup."""
        # Clear all object pools
        for pool in self._object_pools.values():
            pool.clear()

        # Run full GC
        gc.collect(0)  # Generation 0
        gc.collect(1)  # Generation 1
        gc.collect(2)  # Generation 2

        self._stats.gc_collections += 3
        logger.info("Forced memory cleanup completed")

    def track_object(self, obj: Any) -> None:
        """
        Track an object for memory monitoring.

        Args:
            obj: Object to track
        """
        self._tracked_objects.add(obj)
        self._stats.objects_tracked = len(self._tracked_objects)

    def estimate_size(self, obj: Any) -> int:
        """
        Estimate object size in bytes.

        Args:
            obj: Object to estimate

        Returns:
            Estimated size in bytes
        """
        try:
            return sys.getsizeof(obj)
        except TypeError:
            return 0

    def should_cache_object(self, obj: Any) -> bool:
        """
        Determine if object should be cached.

        Args:
            obj: Object to check

        Returns:
            True if object should be cached
        """
        size_kb = self.estimate_size(obj) / 1024

        if size_kb > self._config.cache_item_max_size_kb:
            logger.debug(
                "Object too large to cache",
                size_kb=size_kb,
                max_kb=self._config.cache_item_max_size_kb
            )
            return False

        return True

    # Object pooling methods

    def get_from_pool(self, pool_name: str) -> Optional[Any]:
        """
        Get object from pool.

        Args:
            pool_name: Name of the pool

        Returns:
            Object from pool or None
        """
        if not self._config.enable_object_pooling:
            return None

        pool = self._object_pools.get(pool_name, [])
        if pool:
            return pool.pop()
        return None

    def return_to_pool(self, pool_name: str, obj: Any) -> bool:
        """
        Return object to pool.

        Args:
            pool_name: Name of the pool
            obj: Object to return

        Returns:
            True if object was pooled
        """
        if not self._config.enable_object_pooling:
            return False

        if pool_name not in self._object_pools:
            self._object_pools[pool_name] = []

        pool = self._object_pools[pool_name]
        if len(pool) >= self._config.pool_max_size:
            return False

        pool.append(obj)
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        self.track_memory()

        return {
            "current_mb": round(self._stats.current_mb, 2),
            "peak_mb": round(self._stats.peak_mb, 2),
            "gc_collections": self._stats.gc_collections,
            "objects_tracked": self._stats.objects_tracked,
            "object_pools": {
                name: len(pool)
                for name, pool in self._object_pools.items()
            },
            "gc_enabled": gc.isenabled(),
        }


class ObjectPool:
    """
    Generic object pool for reusing expensive objects.

    Reduces allocation overhead for frequently created objects.
    """

    def __init__(
        self,
        factory: Callable[[], T],
        reset_fn: Optional[Callable[[T], None]] = None,
        max_size: int = 100
    ):
        """
        Initialize pool.

        Args:
            factory: Function to create new objects
            reset_fn: Function to reset object state
            max_size: Maximum pool size
        """
        self._factory = factory
        self._reset_fn = reset_fn
        self._max_size = max_size
        self._pool: List[T] = []
        self._created_count = 0
        self._reused_count = 0

    def acquire(self) -> T:
        """
        Acquire object from pool.

        Returns:
            Object from pool or newly created
        """
        if self._pool:
            obj = self._pool.pop()
            self._reused_count += 1
            return obj

        self._created_count += 1
        return self._factory()

    def release(self, obj: T) -> None:
        """
        Release object back to pool.

        Args:
            obj: Object to release
        """
        if len(self._pool) >= self._max_size:
            return

        if self._reset_fn:
            self._reset_fn(obj)

        self._pool.append(obj)

    @property
    def reuse_rate(self) -> float:
        """Get object reuse rate."""
        total = self._created_count + self._reused_count
        if total == 0:
            return 0.0
        return self._reused_count / total

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "pool_size": len(self._pool),
            "max_size": self._max_size,
            "created_count": self._created_count,
            "reused_count": self._reused_count,
            "reuse_rate": round(self.reuse_rate, 4),
        }

