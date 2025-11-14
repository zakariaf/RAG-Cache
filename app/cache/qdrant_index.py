"""
Qdrant index optimization and management.

Sandi Metz Principles:
- Single Responsibility: Index optimization
- Small methods: Each optimization focused
- Clear naming: Descriptive method names
"""

from typing import Dict, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    HnswConfigDiff,
    OptimizersConfigDiff,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
)

from app.utils.logger import get_logger

logger = get_logger(__name__)


class IndexOptimizationConfig:
    """
    Configuration for index optimization.

    Defines HNSW and optimization parameters.
    """

    def __init__(
        self,
        m: Optional[int] = None,
        ef_construct: Optional[int] = None,
        full_scan_threshold: Optional[int] = None,
        max_indexing_threads: Optional[int] = None,
        on_disk: Optional[bool] = None,
    ):
        """
        Initialize optimization configuration.

        Args:
            m: Number of edges per node in graph (4-64, default: 16)
            ef_construct: Size of dynamic candidate list (default: 100)
            full_scan_threshold: Threshold for full scan vs HNSW (default: 10000)
            max_indexing_threads: Max threads for indexing (default: 0 = auto)
            on_disk: Store index on disk vs memory (default: False)
        """
        self.m = m
        self.ef_construct = ef_construct
        self.full_scan_threshold = full_scan_threshold
        self.max_indexing_threads = max_indexing_threads
        self.on_disk = on_disk


class OptimizationProfile:
    """
    Predefined optimization profiles for different use cases.

    Provides balanced configurations for common scenarios.
    """

    # High accuracy, slower indexing/search
    HIGH_ACCURACY = IndexOptimizationConfig(
        m=64,
        ef_construct=200,
        full_scan_threshold=20000,
        max_indexing_threads=0,
        on_disk=False,
    )

    # Balanced accuracy and speed
    BALANCED = IndexOptimizationConfig(
        m=16,
        ef_construct=100,
        full_scan_threshold=10000,
        max_indexing_threads=0,
        on_disk=False,
    )

    # Fast search, lower accuracy
    FAST_SEARCH = IndexOptimizationConfig(
        m=8,
        ef_construct=64,
        full_scan_threshold=5000,
        max_indexing_threads=0,
        on_disk=False,
    )

    # Memory optimized (disk storage)
    MEMORY_OPTIMIZED = IndexOptimizationConfig(
        m=16,
        ef_construct=100,
        full_scan_threshold=10000,
        max_indexing_threads=0,
        on_disk=True,
    )

    # Large dataset optimized
    LARGE_DATASET = IndexOptimizationConfig(
        m=32,
        ef_construct=128,
        full_scan_threshold=50000,
        max_indexing_threads=0,
        on_disk=True,
    )


class QdrantIndexOptimizer:
    """
    Optimizer for Qdrant collection indexes.

    Manages HNSW configuration and optimizations.
    """

    def __init__(self, client: AsyncQdrantClient, collection_name: str):
        """
        Initialize index optimizer.

        Args:
            client: Qdrant client
            collection_name: Collection to optimize
        """
        self._client = client
        self._collection_name = collection_name

    async def optimize_hnsw(self, config: IndexOptimizationConfig) -> bool:
        """
        Optimize HNSW index configuration.

        Args:
            config: Optimization configuration

        Returns:
            True if successful
        """
        try:
            hnsw_config = HnswConfigDiff(
                m=config.m,
                ef_construct=config.ef_construct,
                full_scan_threshold=config.full_scan_threshold,
                on_disk=config.on_disk,
            )

            await self._client.update_collection(
                collection_name=self._collection_name,
                hnsw_config=hnsw_config,
            )

            logger.info(
                "HNSW index optimized",
                collection=self._collection_name,
                m=config.m,
                ef_construct=config.ef_construct,
            )
            return True

        except Exception as e:
            logger.error("HNSW optimization failed", error=str(e))
            return False

    async def optimize_indexing(
        self,
        memmap_threshold: Optional[int] = None,
        max_segment_size: Optional[int] = None,
    ) -> bool:
        """
        Optimize indexing parameters.

        Args:
            memmap_threshold: Memory map threshold in KB
            max_segment_size: Maximum segment size

        Returns:
            True if successful
        """
        try:
            optimizer_config = OptimizersConfigDiff(
                memmap_threshold=memmap_threshold,
                max_segment_size=max_segment_size,
            )

            await self._client.update_collection(
                collection_name=self._collection_name,
                optimizers_config=optimizer_config,
            )

            logger.info(
                "Indexing optimized",
                collection=self._collection_name,
                memmap_threshold=memmap_threshold,
                max_segment_size=max_segment_size,
            )
            return True

        except Exception as e:
            logger.error("Indexing optimization failed", error=str(e))
            return False

    async def enable_quantization(
        self,
        quantization_type: str = "scalar",
        always_ram: bool = True,
    ) -> bool:
        """
        Enable vector quantization for memory optimization.

        Args:
            quantization_type: Type of quantization (scalar, product)
            always_ram: Keep quantized vectors in RAM

        Returns:
            True if successful
        """
        try:
            if quantization_type == "scalar":
                quantization = ScalarQuantization(
                    scalar=ScalarQuantizationConfig(
                        type=ScalarType.INT8,
                        always_ram=always_ram,
                    )
                )
            else:
                logger.warning(f"Unsupported quantization type: {quantization_type}")
                return False

            await self._client.update_collection(
                collection_name=self._collection_name,
                quantization_config=quantization,
            )

            logger.info(
                "Quantization enabled",
                collection=self._collection_name,
                type=quantization_type,
            )
            return True

        except Exception as e:
            logger.error("Quantization enable failed", error=str(e))
            return False

    async def apply_profile(self, profile: IndexOptimizationConfig) -> bool:
        """
        Apply optimization profile.

        Args:
            profile: Optimization profile to apply

        Returns:
            True if successful
        """
        return await self.optimize_hnsw(profile)

    async def get_index_stats(self) -> Optional[Dict]:
        """
        Get current index statistics.

        Returns:
            Index statistics dictionary
        """
        try:
            info = await self._client.get_collection(
                collection_name=self._collection_name
            )

            return {
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "optimizer_status": info.optimizer_status,
            }

        except Exception as e:
            logger.error("Get index stats failed", error=str(e))
            return None

    async def reindex(self) -> bool:
        """
        Trigger reindexing of collection.

        Returns:
            True if successful
        """
        try:
            # Trigger optimization which includes reindexing
            await self._client.update_collection(
                collection_name=self._collection_name,
                optimizers_config=OptimizersConfigDiff(),
            )

            logger.info("Reindexing triggered", collection=self._collection_name)
            return True

        except Exception as e:
            logger.error("Reindex failed", error=str(e))
            return False


class IndexTuner:
    """
    Automatic index tuning based on collection size.

    Provides recommendations for optimal settings.
    """

    @staticmethod
    def recommend_config(
        collection_size: int,
        memory_available_gb: float = 8.0,
    ) -> IndexOptimizationConfig:
        """
        Recommend index configuration based on collection size.

        Args:
            collection_size: Number of vectors in collection
            memory_available_gb: Available memory in GB

        Returns:
            Recommended configuration
        """
        # Small collections (< 10K vectors)
        if collection_size < 10_000:
            return IndexOptimizationConfig(
                m=8,
                ef_construct=64,
                full_scan_threshold=5000,
                on_disk=False,
            )

        # Medium collections (10K - 100K vectors)
        elif collection_size < 100_000:
            return IndexOptimizationConfig(
                m=16,
                ef_construct=100,
                full_scan_threshold=10000,
                on_disk=memory_available_gb < 4.0,
            )

        # Large collections (100K - 1M vectors)
        elif collection_size < 1_000_000:
            return IndexOptimizationConfig(
                m=32,
                ef_construct=128,
                full_scan_threshold=20000,
                on_disk=memory_available_gb < 8.0,
            )

        # Very large collections (> 1M vectors)
        else:
            return IndexOptimizationConfig(
                m=48,
                ef_construct=150,
                full_scan_threshold=50000,
                on_disk=True,
            )

    @staticmethod
    def estimate_memory_usage(
        vector_count: int,
        vector_size: int,
        m: int = 16,
        quantized: bool = False,
    ) -> float:
        """
        Estimate memory usage for collection.

        Args:
            vector_count: Number of vectors
            vector_size: Dimension of vectors
            m: HNSW m parameter
            quantized: Whether quantization is enabled

        Returns:
            Estimated memory usage in GB
        """
        # Vector storage (4 bytes per float, or 1 byte if quantized)
        bytes_per_element = 1 if quantized else 4
        vector_memory = vector_count * vector_size * bytes_per_element

        # HNSW graph overhead (approximately m * 2 * 8 bytes per vector)
        graph_memory = vector_count * m * 2 * 8

        # Payload overhead (estimated 1KB per vector)
        payload_memory = vector_count * 1024

        total_bytes = vector_memory + graph_memory + payload_memory
        return total_bytes / (1024**3)  # Convert to GB


async def optimize_collection(
    client: AsyncQdrantClient,
    collection_name: str,
    profile: Optional[IndexOptimizationConfig] = None,
) -> bool:
    """
    Optimize collection with recommended or custom profile.

    Args:
        client: Qdrant client
        collection_name: Collection to optimize
        profile: Custom profile (uses auto-tuned if None)

    Returns:
        True if successful
    """
    optimizer = QdrantIndexOptimizer(client, collection_name)

    if profile is None:
        # Auto-tune based on collection size
        stats = await optimizer.get_index_stats()
        if stats:
            size = stats.get("vectors_count", 0)
            profile = IndexTuner.recommend_config(size)
            logger.info(
                "Auto-tuned index configuration",
                collection=collection_name,
                size=size,
            )

    if profile:
        return await optimizer.apply_profile(profile)

    return False
