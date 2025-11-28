"""Unit tests for Pipeline Builder."""

import pytest
from unittest.mock import MagicMock

from app.pipeline.pipeline_builder import (
    PipelineConfig,
    PipelineComponents,
    QueryPipeline,
    QueryPipelineBuilder,
)


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PipelineConfig()
        assert config.enable_exact_cache is True
        assert config.enable_semantic_cache is True
        assert config.enable_preprocessing is True
        assert config.similarity_threshold == 0.85
        assert config.max_retries == 3
        assert config.timeout_seconds == 30.0


class TestQueryPipelineBuilder:
    """Tests for QueryPipelineBuilder."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider."""
        return MagicMock()

    @pytest.fixture
    def mock_redis_cache(self):
        """Create mock Redis cache."""
        return MagicMock()

    @pytest.fixture
    def mock_embedding_generator(self):
        """Create mock embedding generator."""
        return MagicMock()

    @pytest.fixture
    def mock_qdrant_repository(self):
        """Create mock Qdrant repository."""
        return MagicMock()

    def test_build_minimal_pipeline(self, mock_llm_provider, mock_redis_cache):
        """Test building minimal pipeline with just LLM and cache."""
        pipeline = (
            QueryPipelineBuilder()
            .with_llm_provider(mock_llm_provider)
            .with_redis_cache(mock_redis_cache)
            .enable_semantic_cache(False)
            .build()
        )

        assert pipeline.has_exact_cache is True
        assert pipeline.has_semantic_cache is False

    def test_build_full_pipeline(
        self,
        mock_llm_provider,
        mock_redis_cache,
        mock_embedding_generator,
        mock_qdrant_repository,
    ):
        """Test building full pipeline with all components."""
        pipeline = (
            QueryPipelineBuilder()
            .with_llm_provider(mock_llm_provider)
            .with_redis_cache(mock_redis_cache)
            .with_embedding_generator(mock_embedding_generator)
            .with_qdrant_repository(mock_qdrant_repository)
            .build()
        )

        assert pipeline.has_exact_cache is True
        assert pipeline.has_semantic_cache is True
        assert pipeline.has_preprocessing is True

    def test_build_fails_without_llm(self, mock_redis_cache):
        """Test build fails without LLM provider."""
        with pytest.raises(ValueError, match="LLM provider is required"):
            (QueryPipelineBuilder().with_redis_cache(mock_redis_cache).build())

    def test_build_fails_without_cache_when_enabled(self, mock_llm_provider):
        """Test build fails without cache when exact cache is enabled."""
        with pytest.raises(ValueError, match="Redis cache required"):
            (
                QueryPipelineBuilder()
                .with_llm_provider(mock_llm_provider)
                .enable_exact_cache(True)
                .build()
            )

    def test_fluent_interface(self, mock_llm_provider, mock_redis_cache):
        """Test fluent interface returns builder."""
        builder = QueryPipelineBuilder()

        result = builder.with_llm_provider(mock_llm_provider)
        assert result is builder

        result = builder.with_redis_cache(mock_redis_cache)
        assert result is builder

        result = builder.with_similarity_threshold(0.9)
        assert result is builder

    def test_custom_similarity_threshold(self, mock_llm_provider, mock_redis_cache):
        """Test custom similarity threshold."""
        pipeline = (
            QueryPipelineBuilder()
            .with_llm_provider(mock_llm_provider)
            .with_redis_cache(mock_redis_cache)
            .with_similarity_threshold(0.9)
            .enable_semantic_cache(False)
            .build()
        )

        assert pipeline.config.similarity_threshold == 0.9


class TestQueryPipeline:
    """Tests for QueryPipeline."""

    def test_get_query_service(self):
        """Test getting query service from pipeline."""
        mock_llm = MagicMock()
        mock_cache = MagicMock()

        components = PipelineComponents(
            llm_provider=mock_llm,
            redis_cache=mock_cache,
        )
        config = PipelineConfig(enable_semantic_cache=False)
        pipeline = QueryPipeline(config, components)

        service = pipeline.get_query_service()
        assert service is not None
