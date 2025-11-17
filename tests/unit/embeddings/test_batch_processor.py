"""Test embedding batch processor."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.embeddings.batch_processor import (
    BatchProcessingError,
    EmbeddingBatchProcessor,
)
from app.models.embedding import EmbeddingResult


@pytest.fixture
def mock_cache():
    """Create mock embedding cache."""
    cache = Mock()
    cache.peek = Mock(return_value=None)
    cache.get_or_generate = AsyncMock()
    return cache


@pytest.fixture
def mock_generator():
    """Create mock embedding generator."""
    generator = Mock()
    generator.generate_batch = AsyncMock()
    return generator


@pytest.fixture
def sample_embedding():
    """Create sample embedding result."""
    return EmbeddingResult.create(
        text="test",
        vector=[0.1, 0.2, 0.3],
        model="test-model",
        tokens=1,
    )


@pytest.fixture
def processor_with_cache(mock_cache, mock_generator):
    """Create processor with cache."""
    return EmbeddingBatchProcessor(
        cache=mock_cache,
        generator=mock_generator,
        default_batch_size=32,
    )


@pytest.fixture
def processor_without_cache(mock_generator):
    """Create processor without cache."""
    return EmbeddingBatchProcessor(
        cache=None,
        generator=mock_generator,
        default_batch_size=32,
    )


class TestEmbeddingBatchProcessor:
    """Test EmbeddingBatchProcessor class."""

    @pytest.mark.asyncio
    async def test_process_batch_with_cache(
        self, processor_with_cache, mock_generator, sample_embedding
    ):
        """Test batch processing with cache."""
        mock_generator.generate_batch.return_value = [
            sample_embedding,
            sample_embedding,
        ]

        results = await processor_with_cache.process_batch(
            ["text1", "text2"],
            normalize=True,
        )

        assert len(results) == 2
        mock_generator.generate_batch.assert_called()

    @pytest.mark.asyncio
    async def test_process_batch_without_cache(
        self, processor_without_cache, mock_generator, sample_embedding
    ):
        """Test batch processing without cache."""
        mock_generator.generate_batch.return_value = [
            sample_embedding,
            sample_embedding,
        ]

        results = await processor_without_cache.process_batch(
            ["text1", "text2"],
            normalize=True,
        )

        assert len(results) == 2
        mock_generator.generate_batch.assert_called()

    @pytest.mark.asyncio
    async def test_process_batch_empty_raises_error(self, processor_with_cache):
        """Test empty batch raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await processor_with_cache.process_batch([])

    @pytest.mark.asyncio
    async def test_process_batch_custom_batch_size(
        self, processor_with_cache, mock_generator, sample_embedding
    ):
        """Test batch processing with custom batch size."""
        mock_generator.generate_batch.return_value = [sample_embedding]

        await processor_with_cache.process_batch(
            ["text1"],
            batch_size=16,
        )

        # Batch size is used internally for chunking
        mock_generator.generate_batch.assert_called()

    @pytest.mark.asyncio
    async def test_process_with_cache_hits(
        self, processor_with_cache, mock_cache, sample_embedding
    ):
        """Test processing with cache hits."""
        # Mock cache hit
        mock_cache.peek.return_value = sample_embedding

        results = await processor_with_cache.process_batch(["text1"])

        assert len(results) == 1
        # Should not call generator for cached items
        assert results[0] == sample_embedding

    @pytest.mark.asyncio
    async def test_process_batch_parallel(
        self, processor_with_cache, mock_cache, sample_embedding
    ):
        """Test parallel batch processing."""
        mock_cache.get_or_generate.return_value = sample_embedding

        results = await processor_with_cache.process_batch_parallel(
            ["text1", "text2"],
            max_concurrent=2,
        )

        assert len(results) == 2
        assert mock_cache.get_or_generate.call_count == 2

    @pytest.mark.asyncio
    async def test_process_batch_parallel_empty_raises_error(
        self, processor_with_cache
    ):
        """Test parallel processing with empty list raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await processor_with_cache.process_batch_parallel([])

    @pytest.mark.asyncio
    async def test_process_batch_parallel_without_cache(
        self, processor_without_cache, mock_generator, sample_embedding
    ):
        """Test parallel processing falls back to batch for generator."""
        mock_generator.generate_batch.return_value = [sample_embedding]

        results = await processor_without_cache.process_batch_parallel(["text1"])

        assert len(results) == 1
        mock_generator.generate_batch.assert_called()

    @pytest.mark.asyncio
    async def test_process_with_progress(
        self, processor_with_cache, mock_cache, sample_embedding
    ):
        """Test processing with progress callback."""
        mock_cache.get_or_generate.return_value = sample_embedding

        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        results = await processor_with_cache.process_with_progress(
            ["text1", "text2", "text3"],
            progress_callback=progress_callback,
        )

        assert len(results) == 3
        # Progress callback should be called
        assert len(progress_calls) > 0
        # Final progress should be (3, 3)
        assert progress_calls[-1] == (3, 3)

    @pytest.mark.asyncio
    async def test_process_with_progress_empty_raises_error(self, processor_with_cache):
        """Test progress processing with empty list raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await processor_with_cache.process_with_progress([])

    @pytest.mark.asyncio
    async def test_process_with_progress_without_cache(
        self, processor_without_cache, mock_generator, sample_embedding
    ):
        """Test progress processing without cache."""
        mock_generator.generate_batch.return_value = [sample_embedding]

        results = await processor_without_cache.process_with_progress(["text1"])

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_process_with_progress_no_callback(
        self, processor_with_cache, mock_cache, sample_embedding
    ):
        """Test progress processing without callback."""
        mock_cache.get_or_generate.return_value = sample_embedding

        results = await processor_with_cache.process_with_progress(
            ["text1"],
            progress_callback=None,
        )

        assert len(results) == 1

    def test_get_optimal_batch_size_small(self, processor_with_cache):
        """Test optimal batch size for small batches."""
        batch_size = processor_with_cache.get_optimal_batch_size(10)

        # Should return actual size for small batches
        assert batch_size == 10

    def test_get_optimal_batch_size_large(self, processor_with_cache):
        """Test optimal batch size for large batches."""
        batch_size = processor_with_cache.get_optimal_batch_size(100)

        # Should return default batch size for large batches
        assert batch_size == 32

    def test_set_default_batch_size(self, processor_with_cache):
        """Test setting default batch size."""
        processor_with_cache.set_default_batch_size(64)

        assert processor_with_cache._default_batch_size == 64

    def test_set_default_batch_size_invalid(self, processor_with_cache):
        """Test setting invalid batch size raises error."""
        with pytest.raises(ValueError, match="at least 1"):
            processor_with_cache.set_default_batch_size(0)

    @pytest.mark.asyncio
    async def test_process_batch_no_cache_or_generator(self):
        """Test processing fails without cache or generator."""
        processor = EmbeddingBatchProcessor(cache=None, generator=None)

        with pytest.raises(BatchProcessingError, match="No cache or generator"):
            await processor.process_batch(["text1"])

    @pytest.mark.asyncio
    async def test_process_batch_parallel_no_cache_or_generator(self):
        """Test parallel processing fails without cache or generator."""
        processor = EmbeddingBatchProcessor(cache=None, generator=None)

        with pytest.raises(BatchProcessingError, match="No cache or generator"):
            await processor.process_batch_parallel(["text1"])

    @pytest.mark.asyncio
    async def test_process_with_progress_no_cache_or_generator(self):
        """Test progress processing fails without cache or generator."""
        processor = EmbeddingBatchProcessor(cache=None, generator=None)

        with pytest.raises(BatchProcessingError, match="No cache or generator"):
            await processor.process_with_progress(["text1"])

    @pytest.mark.asyncio
    async def test_process_batch_error_handling(
        self, processor_with_cache, mock_generator
    ):
        """Test error handling during batch processing."""
        mock_generator.generate_batch.side_effect = Exception("Generation failed")

        with pytest.raises(BatchProcessingError, match="Failed to process batch"):
            await processor_with_cache.process_batch(["text1"])

    @pytest.mark.asyncio
    async def test_process_batch_parallel_error_handling(
        self, processor_with_cache, mock_cache
    ):
        """Test error handling during parallel processing."""
        mock_cache.get_or_generate.side_effect = Exception("Cache failed")

        with pytest.raises(BatchProcessingError, match="Failed to process batch"):
            await processor_with_cache.process_batch_parallel(["text1"])

    @pytest.mark.asyncio
    async def test_large_batch_chunking(
        self, processor_without_cache, mock_generator, sample_embedding
    ):
        """Test that large batches are chunked properly."""
        # Create 100 texts
        texts = [f"text{i}" for i in range(100)]

        # Mock should return correct number of embeddings for each batch
        def generate_batch_side_effect(batch_texts, normalize=True):
            return [sample_embedding for _ in range(len(batch_texts))]

        mock_generator.generate_batch.side_effect = generate_batch_side_effect

        # Process with default batch size of 32
        results = await processor_without_cache.process_batch(texts)

        # Should be called 4 times (32+32+32+4 = 100)
        assert mock_generator.generate_batch.call_count == 4
        assert len(results) == 100
