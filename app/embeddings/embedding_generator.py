"""
Embedding Generator Service.

Sandi Metz Principles:
- Single Responsibility: Generate embeddings from text
- Small methods: Each method < 10 lines
- Dependency Injection: Model loaded via config
"""
from typing import List

from sentence_transformers import SentenceTransformer

from app.config import config
from app.exceptions import EmbeddingError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingGenerator:
    """
    Service to generate vector embeddings from text.

    Uses SentenceTransformers for local embedding generation.
    """

    def __init__(self, model_name: str | None = None):
        """
        Initialize embedding generator.

        Args:
            model_name: Optional model name (uses config default if None)
        """
        self.model_name = model_name or config.embedding_model
        try:
            self._model = SentenceTransformer(self.model_name)
        except Exception as e:
            logger.error("Failed to load embedding model", error=str(e))
            raise EmbeddingError(f"Failed to load model {self.model_name}: {str(e)}")

    async def generate(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.

        Args:
            text: Input text

        Returns:
            Vector embedding as list of floats

        Raises:
            EmbeddingError: If generation fails
        """
        try:
            # encode returns numpy array, convert to list
            embedding = self._model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")

    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of input texts

        Returns:
            List of vector embeddings
        """
        try:
            embeddings = self._model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logger.error("Batch embedding generation failed", error=str(e))
            raise EmbeddingError(f"Failed to generate batch embeddings: {str(e)}")
