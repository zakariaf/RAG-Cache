"""Test embedding generator."""

from unittest.mock import Mock

import numpy as np
import pytest

from app.embeddings.generator import EmbeddingGenerator, EmbeddingGeneratorError


@pytest.fixture
def mock_model():
    """Create mock sentence transformer model."""
    model = Mock()
    model.encode = Mock(return_value=np.array([0.1, 0.2, 0.3]))
    model.get_sentence_embedding_dimension = Mock(return_value=3)
    return model


@pytest.fixture
def generator(mock_model):
    """Create embedding generator with mock model."""
    gen = EmbeddingGenerator(model=mock_model)
    return gen


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""

    @pytest.mark.asyncio
    async def test_generate_single_text(self, generator, mock_model):
        """Test generating embedding for single text."""
        result = await generator.generate("test text")

        assert result.text == "test text"
        assert result.embedding.vector == [0.1, 0.2, 0.3]
        assert result.tokens > 0
        assert result.normalized is True
        mock_model.encode.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_normalization(self, generator, mock_model):
        """Test generation with normalization enabled."""
        await generator.generate("test", normalize=True)

        mock_model.encode.assert_called_once()
        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs["normalize_embeddings"] is True

    @pytest.mark.asyncio
    async def test_generate_without_normalization(self, generator, mock_model):
        """Test generation without normalization."""
        await generator.generate("test", normalize=False)

        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs["normalize_embeddings"] is False

    @pytest.mark.asyncio
    async def test_generate_empty_text_raises_error(self, generator):
        """Test empty text raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await generator.generate("")

    @pytest.mark.asyncio
    async def test_generate_whitespace_only_raises_error(self, generator):
        """Test whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await generator.generate("   ")

    @pytest.mark.asyncio
    async def test_generate_batch(self, generator, mock_model):
        """Test generating batch of embeddings."""
        mock_model.encode.return_value = np.array(
            [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
            ]
        )

        results = await generator.generate_batch(["text1", "text2"])

        assert len(results) == 2
        assert results[0].text == "text1"
        assert results[1].text == "text2"
        assert results[0].embedding.vector == [0.1, 0.2, 0.3]
        assert results[1].embedding.vector == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    async def test_generate_batch_empty_raises_error(self, generator):
        """Test empty batch raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await generator.generate_batch([])

    @pytest.mark.asyncio
    async def test_generate_batch_with_normalization(self, generator, mock_model):
        """Test batch generation with normalization."""
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])

        await generator.generate_batch(["text"], normalize=True)

        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs["normalize_embeddings"] is True

    def test_get_embedding_dimensions(self, generator, mock_model):
        """Test getting embedding dimensions."""
        dimensions = generator.get_embedding_dimensions()

        assert dimensions == 3
        mock_model.get_sentence_embedding_dimension.assert_called_once()

    def test_estimate_tokens(self, generator):
        """Test token estimation."""
        # 20 characters = 5 tokens (4 chars per token)
        tokens = generator._estimate_tokens("a" * 20)
        assert tokens == 5

        # Very short text should have at least 1 token
        tokens = generator._estimate_tokens("hi")
        assert tokens == 1

    def test_supports_batch_processing(self, generator):
        """Test batch processing support check."""
        assert generator.supports_batch_processing() is True

    @pytest.mark.asyncio
    async def test_health_check_success(self, generator, mock_model):
        """Test health check when model is healthy."""
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])

        result = await generator.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_no_model(self):
        """Test health check fails when model not loaded."""
        gen = EmbeddingGenerator(model=None)

        result = await gen.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_model_fails(self, generator, mock_model):
        """Test health check fails when model errors."""
        mock_model.encode.side_effect = Exception("Model error")

        result = await generator.health_check()

        assert result is False

    def test_set_model(self, generator, mock_model):
        """Test setting a new model."""
        new_model = Mock()
        generator.set_model(new_model)

        assert generator._model == new_model

    def test_model_property_when_not_loaded(self):
        """Test model property raises error when not loaded."""
        gen = EmbeddingGenerator(model=None)

        with pytest.raises(EmbeddingGeneratorError, match="not loaded"):
            _ = gen.model

    @pytest.mark.asyncio
    async def test_generate_error_handling(self, generator, mock_model):
        """Test error handling during generation."""
        mock_model.encode.side_effect = Exception("Encoding failed")

        with pytest.raises(EmbeddingGeneratorError, match="Failed to generate"):
            await generator.generate("test")

    @pytest.mark.asyncio
    async def test_generate_batch_error_handling(self, generator, mock_model):
        """Test error handling during batch generation."""
        mock_model.encode.side_effect = Exception("Batch encoding failed")

        with pytest.raises(EmbeddingGeneratorError, match="Failed to generate batch"):
            await generator.generate_batch(["text1", "text2"])
