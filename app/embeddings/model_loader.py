"""
Embedding model loader.

Loads and caches sentence-transformer models.

Sandi Metz Principles:
- Single Responsibility: Load and cache models
- Small class: Focused on model loading
- Clear naming: Descriptive method names
"""

import time

# from pathlib import Path
from typing import Optional

from sentence_transformers import SentenceTransformer

from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ModelLoadError(Exception):
    """Model loading error."""

    pass


class EmbeddingModelLoader:
    """
    Loads and caches sentence-transformer models.

    Implements singleton pattern to ensure model is loaded once
    and reused across the application.
    """

    _instance: Optional["EmbeddingModelLoader"] = None
    _model: Optional[SentenceTransformer] = None
    _model_name: Optional[str] = None

    def __new__(cls) -> "EmbeddingModelLoader":
        """
        Create singleton instance.

        Returns:
            Singleton instance of model loader
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(
        cls,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        cache_folder: Optional[str] = None,
    ) -> SentenceTransformer:
        """
        Load sentence-transformer model.

        Model is cached after first load. Subsequent calls return
        the cached model if the same model_name is requested.

        Args:
            model_name: Model identifier (default from config)
            device: Compute device 'cpu' or 'cuda' (default from config)
            cache_folder: Directory to cache downloaded models

        Returns:
            Loaded sentence transformer model

        Raises:
            ModelLoadError: If model loading fails
        """
        # Use defaults from config if not provided
        model_name = model_name or config.embedding_model
        device = device or config.embedding_device

        # Return cached model if already loaded and same model requested
        if cls._model is not None and cls._model_name == model_name:
            logger.info("Using cached embedding model", model=model_name)
            return cls._model

        try:
            logger.info(
                "Loading embedding model",
                model=model_name,
                device=device,
                cache_folder=cache_folder,
            )

            start_time = time.time()

            # Load model
            model = SentenceTransformer(
                model_name_or_path=model_name,
                device=device,
                cache_folder=cache_folder,
            )

            load_time = time.time() - start_time

            # Cache the model
            cls._model = model
            cls._model_name = model_name

            logger.info(
                "Embedding model loaded successfully",
                model=model_name,
                device=device,
                dimensions=model.get_sentence_embedding_dimension(),
                load_time_seconds=round(load_time, 2),
            )

            return model

        except Exception as e:
            logger.error(
                "Failed to load embedding model",
                model=model_name,
                error=str(e),
            )
            raise ModelLoadError(
                f"Failed to load model '{model_name}': {str(e)}"
            ) from e

    @classmethod
    def get_cached_model(cls) -> Optional[SentenceTransformer]:
        """
        Get cached model if available.

        Returns:
            Cached model or None if not loaded
        """
        return cls._model

    @classmethod
    def get_model_name(cls) -> Optional[str]:
        """
        Get name of currently loaded model.

        Returns:
            Model name or None if not loaded
        """
        return cls._model_name

    @classmethod
    def is_model_loaded(cls) -> bool:
        """
        Check if model is loaded.

        Returns:
            True if model is cached
        """
        return cls._model is not None

    @classmethod
    def get_model_info(cls) -> dict:
        """
        Get information about loaded model.

        Returns:
            Dictionary with model information
        """
        if cls._model is None:
            return {
                "loaded": False,
                "model_name": None,
                "dimensions": None,
                "device": None,
            }

        return {
            "loaded": True,
            "model_name": cls._model_name,
            "dimensions": cls._model.get_sentence_embedding_dimension(),
            "device": str(cls._model.device),
            "max_seq_length": cls._model.max_seq_length,
        }

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear cached model to free memory.

        Useful for testing or when switching models.
        """
        if cls._model is not None:
            logger.info("Clearing cached embedding model", model=cls._model_name)
            cls._model = None
            cls._model_name = None

    @classmethod
    def reload(
        cls,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        cache_folder: Optional[str] = None,
    ) -> SentenceTransformer:
        """
        Force reload of embedding model.

        Clears cache and loads model again.

        Args:
            model_name: Model identifier (default from config)
            device: Compute device 'cpu' or 'cuda' (default from config)
            cache_folder: Directory to cache downloaded models

        Returns:
            Freshly loaded sentence transformer model

        Raises:
            ModelLoadError: If model loading fails
        """
        logger.info("Force reloading embedding model")
        cls.clear_cache()
        return cls.load(model_name=model_name, device=device, cache_folder=cache_folder)

    @classmethod
    def preload(cls) -> None:
        """
        Preload model using default configuration.

        Useful for application startup to avoid lazy loading delays.

        Raises:
            ModelLoadError: If model loading fails
        """
        logger.info("Preloading embedding model with default config")
        cls.load()


# Convenience function for simple model loading
def load_embedding_model(
    model_name: Optional[str] = None,
    device: Optional[str] = None,
    cache_folder: Optional[str] = None,
) -> SentenceTransformer:
    """
    Load embedding model (convenience function).

    Args:
        model_name: Model identifier (default from config)
        device: Compute device 'cpu' or 'cuda' (default from config)
        cache_folder: Directory to cache downloaded models

    Returns:
        Loaded sentence transformer model

    Raises:
        ModelLoadError: If model loading fails
    """
    return EmbeddingModelLoader.load(
        model_name=model_name, device=device, cache_folder=cache_folder
    )
