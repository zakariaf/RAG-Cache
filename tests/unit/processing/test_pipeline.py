"""Test query processing pipeline."""

import pytest

from app.processing.normalizer import QueryNormalizer
from app.processing.pipeline import (
    PipelineError,
    PipelineResult,
    QueryPipeline,
    QueryPipelineBuilder,
    process_with_pipeline,
)
from app.processing.preprocessor import QueryPreprocessor
from app.processing.validator import QueryValidator


class TestPipelineResult:
    """Test PipelineResult class."""

    def test_initialization(self):
        """Test result initialization."""
        result = PipelineResult()

        assert result.original_query is None
        assert result.normalized_query is None
        assert result.validated is False
        assert result.metadata == {}
        assert result.errors == []

    def test_has_errors_empty(self):
        """Test has_errors when no errors."""
        result = PipelineResult()

        assert result.has_errors() is False

    def test_has_errors_with_errors(self):
        """Test has_errors when errors present."""
        result = PipelineResult()
        result.add_error("Test error")

        assert result.has_errors() is True

    def test_add_error(self):
        """Test adding errors."""
        result = PipelineResult()

        result.add_error("Error 1")
        result.add_error("Error 2")

        assert len(result.errors) == 2
        assert "Error 1" in result.errors
        assert "Error 2" in result.errors

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = PipelineResult()
        result.original_query = "test"
        result.normalized_query = "test normalized"
        result.validated = True
        result.add_error("Error")
        result.metadata["key"] = "value"

        result_dict = result.to_dict()

        assert result_dict["original_query"] == "test"
        assert result_dict["normalized_query"] == "test normalized"
        assert result_dict["validated"] is True
        assert result_dict["has_errors"] is True
        assert len(result_dict["errors"]) == 1
        assert result_dict["metadata"]["key"] == "value"


class TestQueryPipeline:
    """Test QueryPipeline class."""

    @pytest.mark.asyncio
    async def test_empty_pipeline(self):
        """Test processing with empty pipeline."""
        pipeline = QueryPipeline()

        result = await pipeline.process("test query")

        assert result.original_query == "test query"
        assert not result.has_errors()

    @pytest.mark.asyncio
    async def test_with_normalizer(self):
        """Test pipeline with normalizer."""
        normalizer = QueryNormalizer()
        pipeline = QueryPipeline().with_normalizer(normalizer)

        result = await pipeline.process("  TEST  QUERY  ")

        assert result.original_query == "  TEST  QUERY  "
        assert result.normalized_query == "test query"
        assert result.metadata.get("normalization_applied") is True

    @pytest.mark.asyncio
    async def test_with_validator(self):
        """Test pipeline with validator."""
        validator = QueryValidator()
        pipeline = QueryPipeline().with_validator(validator)

        result = await pipeline.process("test query")

        assert result.validated is True
        assert result.metadata.get("validation_passed") is True

    @pytest.mark.asyncio
    async def test_with_preprocessor(self):
        """Test pipeline with preprocessor."""
        preprocessor = QueryPreprocessor()
        pipeline = QueryPipeline().with_preprocessor(preprocessor)

        result = await pipeline.process("  TEST  QUERY  ")

        assert result.preprocessed is not None
        assert result.normalized_query == "test query"
        assert result.metadata.get("preprocessing_applied") is True

    @pytest.mark.asyncio
    async def test_with_custom_step(self):
        """Test pipeline with custom step."""
        step_called = []

        async def custom_step(query: str, result: PipelineResult) -> str:
            step_called.append(True)
            result.metadata["custom_step"] = True
            return query.upper()

        pipeline = QueryPipeline().with_step(custom_step)

        result = await pipeline.process("test")

        assert len(step_called) == 1
        assert result.metadata.get("custom_step") is True

    @pytest.mark.asyncio
    async def test_multiple_steps_order(self):
        """Test multiple steps execute in order."""
        execution_order = []

        async def step1(query: str, result: PipelineResult) -> str:
            execution_order.append(1)
            return query

        async def step2(query: str, result: PipelineResult) -> str:
            execution_order.append(2)
            return query

        pipeline = QueryPipeline().with_step(step1).with_step(step2)

        await pipeline.process("test")

        assert execution_order == [1, 2]

    @pytest.mark.asyncio
    async def test_error_handling_fail_immediately(self):
        """Test pipeline fails immediately by default."""

        async def failing_step(query: str, result: PipelineResult) -> str:
            raise ValueError("Step failed")

        pipeline = QueryPipeline().with_step(failing_step)

        with pytest.raises(PipelineError, match="Step 1 failed"):
            await pipeline.process("test")

    @pytest.mark.asyncio
    async def test_error_handling_continue_on_error(self):
        """Test pipeline continues on error when configured."""
        step2_called = []

        async def failing_step(query: str, result: PipelineResult) -> str:
            raise ValueError("Step failed")

        async def step2(query: str, result: PipelineResult) -> str:
            step2_called.append(True)
            return query

        pipeline = (
            QueryPipeline()
            .with_step(failing_step)
            .with_step(step2)
            .continue_on_error(True)
        )

        result = await pipeline.process("test")

        assert result.has_errors()
        assert len(step2_called) == 1  # Second step should still execute

    @pytest.mark.asyncio
    async def test_with_error_handler(self):
        """Test error handler is called."""
        handler_called = []

        def error_handler(error, result):
            handler_called.append(str(error))

        async def failing_step(query: str, result: PipelineResult) -> str:
            raise ValueError("Test error")

        pipeline = (
            QueryPipeline()
            .with_step(failing_step)
            .with_error_handler(error_handler)
            .continue_on_error(True)
        )

        await pipeline.process("test")

        assert len(handler_called) == 1
        assert "Test error" in handler_called[0]

    @pytest.mark.asyncio
    async def test_error_handler_exception_ignored(self):
        """Test pipeline continues if error handler fails."""

        def failing_handler(error, result):
            raise Exception("Handler failed")

        async def failing_step(query: str, result: PipelineResult) -> str:
            raise ValueError("Step failed")

        pipeline = (
            QueryPipeline()
            .with_step(failing_step)
            .with_error_handler(failing_handler)
            .continue_on_error(True)
        )

        # Should not raise, handler error is caught
        result = await pipeline.process("test")
        assert result.has_errors()

    @pytest.mark.asyncio
    async def test_validation_error_stops_pipeline(self):
        """Test validation error stops pipeline."""
        validator = QueryValidator(min_length=10)
        pipeline = QueryPipeline().with_validator(validator)

        with pytest.raises(PipelineError):
            await pipeline.process("short")


class TestQueryPipelineBuilder:
    """Test QueryPipelineBuilder class."""

    @pytest.mark.asyncio
    async def test_create_empty_pipeline(self):
        """Test creating empty pipeline."""
        pipeline = QueryPipelineBuilder.create()

        result = await pipeline.process("test")

        assert result.original_query == "test"

    @pytest.mark.asyncio
    async def test_default_pipeline(self):
        """Test default pipeline has normalizer and validator."""
        pipeline = QueryPipelineBuilder.default()

        result = await pipeline.process("  TEST  ")

        assert result.normalized_query == "test"
        assert result.validated is True

    @pytest.mark.asyncio
    async def test_strict_pipeline(self):
        """Test strict pipeline uses strict preprocessor."""
        pipeline = QueryPipelineBuilder.strict()

        result = await pipeline.process("  TEST  ")

        assert result.preprocessed is not None
        assert result.normalized_query == "test"

    @pytest.mark.asyncio
    async def test_lenient_pipeline(self):
        """Test lenient pipeline continues on errors."""
        pipeline = QueryPipelineBuilder.lenient()

        # Very short query would normally fail validation
        result = await pipeline.process("x")

        # Lenient pipeline should process it anyway
        assert result.original_query == "x"


class TestProcessWithPipeline:
    """Test process_with_pipeline convenience function."""

    @pytest.mark.asyncio
    async def test_with_default_pipeline(self):
        """Test processing with default pipeline."""
        result = await process_with_pipeline("  TEST  ")

        assert result.normalized_query == "test"
        assert result.validated is True

    @pytest.mark.asyncio
    async def test_with_custom_pipeline(self):
        """Test processing with custom pipeline."""
        pipeline = QueryPipeline().with_normalizer(QueryNormalizer())

        result = await process_with_pipeline("  TEST  ", pipeline=pipeline)

        assert result.normalized_query == "test"


class TestPipelineIntegration:
    """Test pipeline integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self):
        """Test complete pipeline with all steps."""
        pipeline = (
            QueryPipeline()
            .with_normalizer(QueryNormalizer())
            .with_validator(QueryValidator())
        )

        result = await pipeline.process("  How are YOU today?  ")

        assert result.original_query == "  How are YOU today?  "
        assert result.normalized_query == "how are you today?"
        assert result.validated is True
        assert not result.has_errors()

    @pytest.mark.asyncio
    async def test_pipeline_with_request_context(self):
        """Test pipeline captures request context."""
        from app.processing.context_manager import RequestContextManager

        async with RequestContextManager.create_context() as ctx:
            pipeline = QueryPipeline()

            result = await pipeline.process("test")

            assert result.request_id == ctx.request_id

    @pytest.mark.asyncio
    async def test_chained_pipeline_building(self):
        """Test fluent interface for building pipeline."""
        pipeline = (
            QueryPipeline()
            .with_normalizer(QueryNormalizer())
            .with_validator(QueryValidator())
            .continue_on_error(False)
        )

        result = await pipeline.process("test query")

        assert result.normalized_query == "test query"
        assert result.validated is True
