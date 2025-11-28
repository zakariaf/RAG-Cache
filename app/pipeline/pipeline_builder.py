"""
Query Pipeline Builder.

Builds configurable query processing pipelines.

Sandi Metz Principles:
- Single Responsibility: Pipeline construction
- Builder Pattern: Fluent interface for configuration
- Dependency Injection: Components injected
"""

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from app.cache.redis_cache import RedisCache
from app.embeddings.embedding_generator import EmbeddingGenerator
from app.llm.provider import BaseLLMProvider
from app.pipeline.query_normalizer import QueryNormalizer
from app.pipeline.query_preprocessor import QueryPreprocessor
from app.pipeline.query_validator import QueryValidator
from app.pipeline.semantic_matcher import SemanticMatcher
from app.repositories.qdrant_repository import QdrantRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for query pipeline."""

    enable_exact_cache: bool = True
    enable_semantic_cache: bool = True
    enable_preprocessing: bool = True
    enable_metrics: bool = True
    enable_error_recovery: bool = True
    similarity_threshold: float = 0.85
    max_retries: int = 3
    timeout_seconds: float = 30.0


@dataclass
class PipelineComponents:
    """Container for pipeline components."""

    redis_cache: Optional[RedisCache] = None
    llm_provider: Optional[BaseLLMProvider] = None
    embedding_generator: Optional[EmbeddingGenerator] = None
    qdrant_repository: Optional[QdrantRepository] = None
    normalizer: Optional[QueryNormalizer] = None
    validator: Optional[QueryValidator] = None
    preprocessor: Optional[QueryPreprocessor] = None
    semantic_matcher: Optional[SemanticMatcher] = None
    middleware: List[Callable] = field(default_factory=list)


class QueryPipelineBuilder:
    """
    Builder for constructing query pipelines.

    Uses fluent interface for easy configuration.
    """

    def __init__(self):
        """Initialize builder with defaults."""
        self._config = PipelineConfig()
        self._components = PipelineComponents()

    def with_config(self, config: PipelineConfig) -> "QueryPipelineBuilder":
        """
        Set pipeline configuration.

        Args:
            config: Pipeline configuration

        Returns:
            Self for chaining
        """
        self._config = config
        return self

    def with_redis_cache(self, cache: RedisCache) -> "QueryPipelineBuilder":
        """
        Set Redis cache component.

        Args:
            cache: Redis cache instance

        Returns:
            Self for chaining
        """
        self._components.redis_cache = cache
        return self

    def with_llm_provider(self, provider: BaseLLMProvider) -> "QueryPipelineBuilder":
        """
        Set LLM provider component.

        Args:
            provider: LLM provider instance

        Returns:
            Self for chaining
        """
        self._components.llm_provider = provider
        return self

    def with_embedding_generator(
        self, generator: EmbeddingGenerator
    ) -> "QueryPipelineBuilder":
        """
        Set embedding generator component.

        Args:
            generator: Embedding generator instance

        Returns:
            Self for chaining
        """
        self._components.embedding_generator = generator
        return self

    def with_qdrant_repository(
        self, repository: QdrantRepository
    ) -> "QueryPipelineBuilder":
        """
        Set Qdrant repository component.

        Args:
            repository: Qdrant repository instance

        Returns:
            Self for chaining
        """
        self._components.qdrant_repository = repository
        return self

    def with_normalizer(self, normalizer: QueryNormalizer) -> "QueryPipelineBuilder":
        """
        Set query normalizer component.

        Args:
            normalizer: Query normalizer instance

        Returns:
            Self for chaining
        """
        self._components.normalizer = normalizer
        return self

    def with_validator(self, validator: QueryValidator) -> "QueryPipelineBuilder":
        """
        Set query validator component.

        Args:
            validator: Query validator instance

        Returns:
            Self for chaining
        """
        self._components.validator = validator
        return self

    def with_middleware(self, middleware: Callable) -> "QueryPipelineBuilder":
        """
        Add middleware to pipeline.

        Args:
            middleware: Middleware function

        Returns:
            Self for chaining
        """
        self._components.middleware.append(middleware)
        return self

    def enable_exact_cache(self, enabled: bool = True) -> "QueryPipelineBuilder":
        """
        Enable or disable exact cache.

        Args:
            enabled: Whether to enable

        Returns:
            Self for chaining
        """
        self._config.enable_exact_cache = enabled
        return self

    def enable_semantic_cache(self, enabled: bool = True) -> "QueryPipelineBuilder":
        """
        Enable or disable semantic cache.

        Args:
            enabled: Whether to enable

        Returns:
            Self for chaining
        """
        self._config.enable_semantic_cache = enabled
        return self

    def with_similarity_threshold(self, threshold: float) -> "QueryPipelineBuilder":
        """
        Set similarity threshold.

        Args:
            threshold: Similarity threshold (0.0-1.0)

        Returns:
            Self for chaining
        """
        self._config.similarity_threshold = threshold
        return self

    def with_timeout(self, seconds: float) -> "QueryPipelineBuilder":
        """
        Set request timeout.

        Args:
            seconds: Timeout in seconds

        Returns:
            Self for chaining
        """
        self._config.timeout_seconds = seconds
        return self

    def with_retries(self, max_retries: int) -> "QueryPipelineBuilder":
        """
        Set max retries.

        Args:
            max_retries: Maximum retry count

        Returns:
            Self for chaining
        """
        self._config.max_retries = max_retries
        return self

    def build(self) -> "QueryPipeline":
        """
        Build the configured pipeline.

        Returns:
            Configured QueryPipeline

        Raises:
            ValueError: If required components are missing
        """
        # Validate required components
        if not self._components.llm_provider:
            raise ValueError("LLM provider is required")

        if self._config.enable_exact_cache and not self._components.redis_cache:
            raise ValueError("Redis cache required when exact cache is enabled")

        # Build preprocessor if not provided
        if self._config.enable_preprocessing and not self._components.preprocessor:
            self._components.preprocessor = QueryPreprocessor(
                normalizer=self._components.normalizer or QueryNormalizer(),
                validator=self._components.validator or QueryValidator(),
            )

        # Build semantic matcher if semantic cache enabled
        if self._config.enable_semantic_cache:
            if not self._components.embedding_generator:
                raise ValueError("Embedding generator required for semantic cache")
            if not self._components.qdrant_repository:
                raise ValueError("Qdrant repository required for semantic cache")

            self._components.semantic_matcher = SemanticMatcher(
                embedding_generator=self._components.embedding_generator,
                qdrant_repository=self._components.qdrant_repository,
                similarity_threshold=self._config.similarity_threshold,
            )

        logger.info(
            "Pipeline built",
            exact_cache=self._config.enable_exact_cache,
            semantic_cache=self._config.enable_semantic_cache,
            preprocessing=self._config.enable_preprocessing,
        )

        return QueryPipeline(self._config, self._components)


class QueryPipeline:
    """
    Configured query processing pipeline.

    Executes query processing with configured components.
    """

    def __init__(self, config: PipelineConfig, components: PipelineComponents):
        """
        Initialize pipeline.

        Args:
            config: Pipeline configuration
            components: Pipeline components
        """
        self._config = config
        self._components = components

    @property
    def config(self) -> PipelineConfig:
        """Get pipeline configuration."""
        return self._config

    @property
    def components(self) -> PipelineComponents:
        """Get pipeline components."""
        return self._components

    @property
    def has_exact_cache(self) -> bool:
        """Check if exact cache is enabled."""
        return (
            self._config.enable_exact_cache and self._components.redis_cache is not None
        )

    @property
    def has_semantic_cache(self) -> bool:
        """Check if semantic cache is enabled."""
        return (
            self._config.enable_semantic_cache
            and self._components.semantic_matcher is not None
        )

    @property
    def has_preprocessing(self) -> bool:
        """Check if preprocessing is enabled."""
        return (
            self._config.enable_preprocessing
            and self._components.preprocessor is not None
        )

    def get_query_service(self):
        """
        Get configured query service.

        Returns:
            QueryService instance
        """
        from app.services.query_service import QueryService

        return QueryService(
            cache=self._components.redis_cache,
            llm_provider=self._components.llm_provider,
            semantic_matcher=self._components.semantic_matcher,
        )
