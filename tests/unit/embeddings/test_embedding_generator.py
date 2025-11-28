"""
Unit tests for Embedding Generator Service.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.embeddings.embedding_generator import EmbeddingGenerator
from app.exceptions import EmbeddingError


@pytest.fixture
def mock_sentence_transformer():
    with patch("app.embeddings.embedding_generator.SentenceTransformer") as mock:
        yield mock


@pytest.fixture
def embedding_generator(mock_sentence_transformer):
    return EmbeddingGenerator()


@pytest.mark.asyncio
async def test_generate_embedding_success(
    embedding_generator, mock_sentence_transformer
):
    """Test successful embedding generation."""
    mock_model = mock_sentence_transformer.return_value
    # Use numpy array since the real model returns numpy arrays
    mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])

    text = "test query"
    embedding = await embedding_generator.generate(text)

    assert embedding == [0.1, 0.2, 0.3]
    mock_model.encode.assert_called_once_with(text)


@pytest.mark.asyncio
async def test_generate_embedding_error(embedding_generator, mock_sentence_transformer):
    """Test error handling during embedding generation."""
    mock_model = mock_sentence_transformer.return_value
    mock_model.encode.side_effect = Exception("Model error")

    with pytest.raises(EmbeddingError):
        await embedding_generator.generate("test")


@pytest.mark.asyncio
async def test_generate_batch_success(embedding_generator, mock_sentence_transformer):
    """Test successful batch embedding generation."""
    mock_model = mock_sentence_transformer.return_value
    # Use numpy array since the real model returns numpy arrays
    mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])

    texts = ["test1", "test2"]
    embeddings = await embedding_generator.generate_batch(texts)

    assert len(embeddings) == 2
    assert embeddings[0] == [0.1, 0.2]
    assert embeddings[1] == [0.3, 0.4]
    mock_model.encode.assert_called_once_with(texts)
