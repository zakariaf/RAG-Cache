"""
Query processing pipeline.

Fluent builder for assembling query processing pipeline.

Sandi Metz Principles:
- Single Responsibility: Pipeline assembly and execution
- Small methods: Each step isolated
- Builder Pattern: Fluent interface
"""

from typing import Callable, List, Optional

from app.models.query import QueryRequest
from app.processing.context_manager import RequestContextManager
from app.processing.normalizer import QueryNormalizer
from app.processing.preprocessor import PreprocessedQuery, QueryPreprocessor
from app.processing.validator import QueryValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PipelineError(Exception):
    """Pipeline processing error."""

    pass


class PipelineResult:
    """
    Result of pipeline processing.

    Contains all intermediate and final results.
    """

    def __init__(self):
        """Initialize pipeline result."""
        self.original_query: Optional[str] = None
        self.normalized_query: Optional[str] = None
        self.preprocessed: Optional[PreprocessedQuery] = None
        self.validated: bool = False
        self.metadata: dict = {}
        self.errors: List[str] = []
        self.request_id: Optional[str] = None

    def has_errors(self) -> bool:
        """Check if pipeline encountered errors."""
        return len(self.errors) > 0

    def add_error(self, error: str) -> None:
        """Add error to result."""
        self.errors.append(error)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "validated": self.validated,
            "has_errors": self.has_errors(),
            "errors": self.errors.copy(),
            "metadata": self.metadata.copy(),
            "request_id": self.request_id,
        }


class QueryPipeline:
    """
    Query processing pipeline.

    Executes configured processing steps in sequence.
    """

    def __init__(self):
        """Initialize pipeline."""
        self._steps: List[Callable] = []
        self._normalizer: Optional[QueryNormalizer] = None
        self._validator: Optional[QueryValidator] = None
        self._preprocessor: Optional[QueryPreprocessor] = None
        self._error_handlers: List[Callable] = []
        self._continue_on_error: bool = False

    def with_normalizer(self, normalizer: QueryNormalizer) -> "QueryPipeline":
        """
        Add normalization step.

        Args:
            normalizer: Query normalizer

        Returns:
            Self for chaining
        """
        self._normalizer = normalizer
        self._steps.append(self._normalize_step)
        return self

    def with_validator(self, validator: QueryValidator) -> "QueryPipeline":
        """
        Add validation step.

        Args:
            validator: Query validator

        Returns:
            Self for chaining
        """
        self._validator = validator
        self._steps.append(self._validate_step)
        return self

    def with_preprocessor(self, preprocessor: QueryPreprocessor) -> "QueryPipeline":
        """
        Add preprocessing step.

        Args:
            preprocessor: Query preprocessor

        Returns:
            Self for chaining
        """
        self._preprocessor = preprocessor
        self._steps.append(self._preprocess_step)
        return self

    def with_step(self, step: Callable) -> "QueryPipeline":
        """
        Add custom processing step.

        Args:
            step: Callable that takes (query: str, result: PipelineResult)

        Returns:
            Self for chaining
        """
        self._steps.append(step)
        return self

    def with_error_handler(self, handler: Callable) -> "QueryPipeline":
        """
        Add error handler.

        Args:
            handler: Error handler callable

        Returns:
            Self for chaining
        """
        self._error_handlers.append(handler)
        return self

    def continue_on_error(self, continue_: bool = True) -> "QueryPipeline":
        """
        Configure error handling behavior.

        Args:
            continue_: If True, continue pipeline on errors

        Returns:
            Self for chaining
        """
        self._continue_on_error = continue_
        return self

    async def process(self, query: str) -> PipelineResult:
        """
        Process query through pipeline.

        Args:
            query: Query text

        Returns:
            Pipeline result

        Raises:
            PipelineError: If processing fails (when continue_on_error=False)
        """
        result = PipelineResult()
        result.original_query = query

        # Get request context if available
        result.request_id = RequestContextManager.get_current_request_id()

        logger.debug(
            "Starting pipeline processing",
            query_length=len(query),
            steps_count=len(self._steps),
            request_id=result.request_id,
        )

        current_query = query

        try:
            # Execute each step
            for i, step in enumerate(self._steps):
                try:
                    logger.debug(f"Executing pipeline step {i + 1}/{len(self._steps)}")
                    current_query = await step(current_query, result)

                    # Check if step produced errors
                    if result.has_errors() and not self._continue_on_error:
                        raise PipelineError(
                            f"Pipeline step {i + 1} failed: {result.errors[-1]}"
                        )

                except Exception as e:
                    error_msg = f"Step {i + 1} failed: {str(e)}"
                    result.add_error(error_msg)

                    # Call error handlers
                    for handler in self._error_handlers:
                        try:
                            handler(e, result)
                        except Exception as handler_error:
                            logger.error(
                                "Error handler failed", error=str(handler_error)
                            )

                    if not self._continue_on_error:
                        raise PipelineError(error_msg) from e

                    logger.warning(
                        "Continuing pipeline after error",
                        step=i + 1,
                        error=str(e),
                    )

            logger.info(
                "Pipeline processing completed",
                has_errors=result.has_errors(),
                errors_count=len(result.errors),
                request_id=result.request_id,
            )

            return result

        except PipelineError:
            raise
        except Exception as e:
            error_msg = f"Pipeline processing failed: {str(e)}"
            result.add_error(error_msg)
            logger.error(error_msg, query=query[:100])
            raise PipelineError(error_msg) from e

    async def _normalize_step(self, query: str, result: PipelineResult) -> str:
        """
        Execute normalization step.

        Args:
            query: Query text
            result: Pipeline result

        Returns:
            Normalized query
        """
        if self._normalizer:
            normalized = self._normalizer.normalize(query)
            result.normalized_query = normalized
            result.metadata["normalization_applied"] = True
            return normalized
        return query

    async def _validate_step(self, query: str, result: PipelineResult) -> str:
        """
        Execute validation step.

        Args:
            query: Query text
            result: Pipeline result

        Returns:
            Query (unchanged)

        Raises:
            Exception: If validation fails
        """
        if self._validator:
            self._validator.validate(query)
            result.validated = True
            result.metadata["validation_passed"] = True
        return query

    async def _preprocess_step(self, query: str, result: PipelineResult) -> str:
        """
        Execute preprocessing step.

        Args:
            query: Query text
            result: Pipeline result

        Returns:
            Preprocessed query
        """
        if self._preprocessor:
            preprocessed = self._preprocessor.preprocess(query)
            result.preprocessed = preprocessed
            result.normalized_query = preprocessed.normalized
            result.validated = preprocessed.is_valid
            result.metadata["preprocessing_applied"] = True

            if not preprocessed.is_valid:
                for error in preprocessed.validation_errors:
                    result.add_error(f"Preprocessing error: {error}")

            return preprocessed.normalized
        return query


class QueryPipelineBuilder:
    """
    Builder for query processing pipelines.

    Provides fluent interface for constructing pipelines.
    """

    @staticmethod
    def create() -> QueryPipeline:
        """
        Create new pipeline.

        Returns:
            Empty pipeline
        """
        return QueryPipeline()

    @staticmethod
    def default() -> QueryPipeline:
        """
        Create pipeline with default configuration.

        Returns:
            Pipeline with normalization and validation
        """
        return (
            QueryPipeline()
            .with_normalizer(QueryNormalizer())
            .with_validator(QueryValidator())
        )

    @staticmethod
    def strict() -> QueryPipeline:
        """
        Create strict pipeline.

        Returns:
            Pipeline with strict preprocessing
        """
        from app.processing.preprocessor import StrictQueryPreprocessor

        return QueryPipeline().with_preprocessor(StrictQueryPreprocessor())

    @staticmethod
    def lenient() -> QueryPipeline:
        """
        Create lenient pipeline.

        Returns:
            Pipeline that continues on errors
        """
        from app.processing.preprocessor import LenientQueryPreprocessor

        return (
            QueryPipeline()
            .with_preprocessor(LenientQueryPreprocessor())
            .continue_on_error(True)
        )


# Convenience function
async def process_with_pipeline(
    query: str,
    pipeline: Optional[QueryPipeline] = None,
) -> PipelineResult:
    """
    Process query with pipeline (convenience function).

    Args:
        query: Query text
        pipeline: Pipeline to use (creates default if None)

    Returns:
        Pipeline result
    """
    if pipeline is None:
        pipeline = QueryPipelineBuilder.default()

    return await pipeline.process(query)
