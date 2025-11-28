"""
Query processing pipeline module.

Contains query processing components:
- Query Normalizer
- Query Validator
- Query Preprocessor
- Semantic Matcher
- Request Context Manager
- Pipeline Builder
- Error Recovery
- Performance Monitor
- Async Processor
- Parallel Cache
- Deduplication
- Result Aggregator
"""

from app.pipeline.async_processor import AsyncQueryProcessor, AsyncResult
from app.pipeline.deduplication import (
    DeduplicatingProcessor,
    QueryDeduplicator,
    DeduplicationStats,
)
from app.pipeline.error_recovery import (
    PipelineErrorHandler,
    RecoveryAction,
    RecoveryResult,
    with_recovery,
)
from app.pipeline.parallel_cache import (
    CacheResult,
    CacheSource,
    ParallelCacheChecker,
    check_caches_parallel,
)
from app.pipeline.performance_monitor import (
    OperationMetrics,
    PerformanceMonitor,
    PipelineMetrics,
    get_monitor,
    track_operation,
)
from app.pipeline.pipeline_builder import (
    PipelineConfig,
    PipelineComponents,
    QueryPipeline,
    QueryPipelineBuilder,
)
from app.pipeline.query_normalizer import QueryNormalizer, normalize_query
from app.pipeline.query_preprocessor import (
    PreprocessResult,
    QueryPreprocessor,
    preprocess_query,
)
from app.pipeline.query_validator import (
    QueryValidator,
    ValidationResult,
    validate_query,
)
from app.pipeline.request_context import (
    RequestContext,
    RequestContextManager,
    end_request,
    get_current_context,
    get_request_id,
    start_request,
)
from app.pipeline.result_aggregator import (
    AggregatedResult,
    AggregationStrategy,
    BatchAggregator,
    BatchResult,
    ResultAggregator,
)
from app.pipeline.semantic_matcher import SemanticMatch, SemanticMatcher

__all__ = [
    # Normalizer
    "QueryNormalizer",
    "normalize_query",
    # Validator
    "QueryValidator",
    "ValidationResult",
    "validate_query",
    # Preprocessor
    "QueryPreprocessor",
    "PreprocessResult",
    "preprocess_query",
    # Semantic Matcher
    "SemanticMatcher",
    "SemanticMatch",
    # Request Context
    "RequestContext",
    "RequestContextManager",
    "start_request",
    "get_current_context",
    "end_request",
    "get_request_id",
    # Pipeline Builder
    "QueryPipelineBuilder",
    "QueryPipeline",
    "PipelineConfig",
    "PipelineComponents",
    # Error Recovery
    "PipelineErrorHandler",
    "RecoveryAction",
    "RecoveryResult",
    "with_recovery",
    # Performance Monitor
    "PerformanceMonitor",
    "PipelineMetrics",
    "OperationMetrics",
    "get_monitor",
    "track_operation",
    # Async Processor
    "AsyncQueryProcessor",
    "AsyncResult",
    # Parallel Cache
    "ParallelCacheChecker",
    "CacheResult",
    "CacheSource",
    "check_caches_parallel",
    # Deduplication
    "QueryDeduplicator",
    "DeduplicatingProcessor",
    "DeduplicationStats",
    # Result Aggregator
    "ResultAggregator",
    "BatchAggregator",
    "AggregatedResult",
    "BatchResult",
    "AggregationStrategy",
]
