"""Test embedding model loader."""

from unittest.mock import Mock, patch

import pytest

from app.embeddings.model_loader import (
    EmbeddingModelLoader,
    ModelLoadError,
    load_embedding_model,
)


@pytest.fixture(autouse=True)
def clear_singleton():
    """Clear singleton cache before each test."""
    EmbeddingModelLoader.clear_cache()
    yield
    EmbeddingModelLoader.clear_cache()


@pytest.fixture
def mock_sentence_transformer():
    """Create mock sentence transformer."""
    model = Mock()
    model.get_sentence_embedding_dimension = Mock(return_value=384)
    model.device = "cpu"
    model.max_seq_length = 512
    return model


class TestEmbeddingModelLoader:
    """Test EmbeddingModelLoader class."""

    def test_singleton_pattern(self):
        """Test that loader implements singleton pattern."""
        loader1 = EmbeddingModelLoader()
        loader2 = EmbeddingModelLoader()

        assert loader1 is loader2

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_load_model(self, mock_st_class, mock_sentence_transformer):
        """Test loading a model."""
        mock_st_class.return_value = mock_sentence_transformer

        model = EmbeddingModelLoader.load(
            model_name="test-model",
            device="cpu",
        )

        assert model == mock_sentence_transformer
        mock_st_class.assert_called_once()

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_load_caches_model(self, mock_st_class, mock_sentence_transformer):
        """Test that model is cached after first load."""
        mock_st_class.return_value = mock_sentence_transformer

        # Load first time
        model1 = EmbeddingModelLoader.load(model_name="test-model")

        # Load second time
        model2 = EmbeddingModelLoader.load(model_name="test-model")

        # Should return cached model
        assert model1 is model2
        # Should only call SentenceTransformer constructor once
        assert mock_st_class.call_count == 1

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_load_different_model_clears_cache(
        self, mock_st_class, mock_sentence_transformer
    ):
        """Test loading different model clears cache."""
        mock_st_class.return_value = mock_sentence_transformer

        # Load first model
        EmbeddingModelLoader.load(model_name="model1")

        # Load different model
        EmbeddingModelLoader.load(model_name="model2")

        # Should have loaded twice
        assert mock_st_class.call_count == 2

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_load_with_cache_folder(self, mock_st_class, mock_sentence_transformer):
        """Test loading with custom cache folder."""
        mock_st_class.return_value = mock_sentence_transformer

        EmbeddingModelLoader.load(
            model_name="test-model",
            cache_folder="/tmp/models",
        )

        call_kwargs = mock_st_class.call_args[1]
        assert call_kwargs["cache_folder"] == "/tmp/models"

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_load_error_handling(self, mock_st_class):
        """Test error handling when loading fails."""
        mock_st_class.side_effect = Exception("Load failed")

        with pytest.raises(ModelLoadError, match="Failed to load model"):
            EmbeddingModelLoader.load(model_name="test-model")

    def test_get_cached_model_when_not_loaded(self):
        """Test getting cached model when none loaded."""
        model = EmbeddingModelLoader.get_cached_model()

        assert model is None

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_get_cached_model_when_loaded(
        self, mock_st_class, mock_sentence_transformer
    ):
        """Test getting cached model when loaded."""
        mock_st_class.return_value = mock_sentence_transformer

        EmbeddingModelLoader.load(model_name="test-model")
        model = EmbeddingModelLoader.get_cached_model()

        assert model == mock_sentence_transformer

    def test_get_model_name_when_not_loaded(self):
        """Test getting model name when none loaded."""
        name = EmbeddingModelLoader.get_model_name()

        assert name is None

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_get_model_name_when_loaded(self, mock_st_class, mock_sentence_transformer):
        """Test getting model name when loaded."""
        mock_st_class.return_value = mock_sentence_transformer

        EmbeddingModelLoader.load(model_name="test-model")
        name = EmbeddingModelLoader.get_model_name()

        assert name == "test-model"

    def test_is_model_loaded_when_not_loaded(self):
        """Test checking if model loaded when none loaded."""
        assert EmbeddingModelLoader.is_model_loaded() is False

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_is_model_loaded_when_loaded(
        self, mock_st_class, mock_sentence_transformer
    ):
        """Test checking if model loaded when loaded."""
        mock_st_class.return_value = mock_sentence_transformer

        EmbeddingModelLoader.load(model_name="test-model")

        assert EmbeddingModelLoader.is_model_loaded() is True

    def test_get_model_info_when_not_loaded(self):
        """Test getting model info when none loaded."""
        info = EmbeddingModelLoader.get_model_info()

        assert info["loaded"] is False
        assert info["model_name"] is None
        assert info["dimensions"] is None
        assert info["device"] is None

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_get_model_info_when_loaded(self, mock_st_class, mock_sentence_transformer):
        """Test getting model info when loaded."""
        mock_st_class.return_value = mock_sentence_transformer

        EmbeddingModelLoader.load(model_name="test-model")
        info = EmbeddingModelLoader.get_model_info()

        assert info["loaded"] is True
        assert info["model_name"] == "test-model"
        assert info["dimensions"] == 384
        assert info["device"] == "cpu"
        assert info["max_seq_length"] == 512

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_clear_cache(self, mock_st_class, mock_sentence_transformer):
        """Test clearing cache."""
        mock_st_class.return_value = mock_sentence_transformer

        # Load model
        EmbeddingModelLoader.load(model_name="test-model")
        assert EmbeddingModelLoader.is_model_loaded() is True

        # Clear cache
        EmbeddingModelLoader.clear_cache()
        assert EmbeddingModelLoader.is_model_loaded() is False

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_reload(self, mock_st_class, mock_sentence_transformer):
        """Test reloading model."""
        mock_st_class.return_value = mock_sentence_transformer

        # Load first time
        EmbeddingModelLoader.load(model_name="test-model")

        # Reload
        EmbeddingModelLoader.reload(model_name="test-model")

        # Should have loaded twice (once + reload)
        assert mock_st_class.call_count == 2

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_preload(self, mock_st_class, mock_sentence_transformer):
        """Test preloading with default config."""
        mock_st_class.return_value = mock_sentence_transformer

        EmbeddingModelLoader.preload()

        assert EmbeddingModelLoader.is_model_loaded() is True
        mock_st_class.assert_called_once()


class TestLoadEmbeddingModelFunction:
    """Test load_embedding_model convenience function."""

    @patch("app.embeddings.model_loader.SentenceTransformer")
    def test_load_function(self, mock_st_class, mock_sentence_transformer):
        """Test convenience function for loading."""
        mock_st_class.return_value = mock_sentence_transformer

        model = load_embedding_model(model_name="test-model")

        assert model == mock_sentence_transformer
        mock_st_class.assert_called_once()
