"""
Embedding generation service.

Generates vector embeddings for text using sentence-transformers.

Sandi Metz Principles:
- Single Responsibility: Generate embeddings
- Small methods: Each method < 10 lines
- Dependency Injection: Model loader injected
"""

import time
from typing import List, Optional

from sentence_transformers import SentenceTransformer

from app.config import config
from app.models.embedding import EmbeddingResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingGeneratorError(Exception):
    """Embedding generation error."""

    pass


class EmbeddingGenerator:
    """
    Service for generating text embeddings.

    Uses sentence-transformers to convert text into vector embeddings
    for semantic similarity matching.
    """

    def __init__(self, model: Optional[SentenceTransformer] = None):
        """
        Initialize embedding generator.

        Args:
            model: Pre-loaded sentence transformer model (optional)
        """
        self._model = model
        self._model_name = config.embedding_model
        self._device = config.embedding_device

    @property
    def model(self) -> SentenceTransformer:
        """
        Get or load the embedding model.

        Returns:
            Loaded sentence transformer model

        Raises:
            EmbeddingGeneratorError: If model loading fails
        """
        if self._model is None:
            raise EmbeddingGeneratorError(
                "Model not loaded. Use model loader to initialize."
            )
        return self._model

    def set_model(self, model: SentenceTransformer) -> None:
        """
        Set the embedding model.

        Args:
            model: Sentence transformer model
        """
        self._model = model
        logger.info("Embedding model set", model=self._model_name)

    async def generate(self, text: str, normalize: bool = True) -> EmbeddingResult:
        """
        Generate embedding for single text.

        Args:
            text: Text to embed
            normalize: Whether to normalize the embedding vector

        Returns:
            Embedding result with vector and metadata

        Raises:
            EmbeddingGeneratorError: If generation fails
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            start_time = time.time()

            # Generate embedding
            vector = self.model.encode(
                text,
                normalize_embeddings=normalize,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            # Convert numpy array to list
            vector_list = vector.tolist()

            # Estimate token count (rough approximation)
            tokens = self._estimate_tokens(text)

            # Calculate generation time
            generation_time = time.time() - start_time

            logger.info(
                "Generated embedding",
                text_length=len(text),
                tokens=tokens,
                dimensions=len(vector_list),
                generation_time_ms=round(generation_time * 1000, 2),
            )

            return EmbeddingResult.create(
                text=text,
                vector=vector_list,
                model=self._model_name,
                tokens=tokens,
                normalized=normalize,
            )

        except Exception as e:
            logger.error("Embedding generation failed", error=str(e), text=text[:100])
            raise EmbeddingGeneratorError(f"Failed to generate embedding: {str(e)}")

    async def generate_batch(
        self, texts: List[str], normalize: bool = True
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed
            normalize: Whether to normalize the embedding vectors

        Returns:
            List of embedding results

        Raises:
            EmbeddingGeneratorError: If generation fails
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        try:
            start_time = time.time()

            # Generate embeddings in batch
            vectors = self.model.encode(
                texts,
                normalize_embeddings=normalize,
                show_progress_bar=False,
                convert_to_numpy=True,
                batch_size=config.embedding_batch_size,
            )

            # Convert to embedding results
            results = []
            for text, vector in zip(texts, vectors):
                vector_list = vector.tolist()
                tokens = self._estimate_tokens(text)

                result = EmbeddingResult.create(
                    text=text,
                    vector=vector_list,
                    model=self._model_name,
                    tokens=tokens,
                    normalized=normalize,
                )
                results.append(result)

            # Calculate generation time
            generation_time = time.time() - start_time

            logger.info(
                "Generated batch embeddings",
                batch_size=len(texts),
                total_tokens=sum(r.tokens for r in results),
                generation_time_ms=round(generation_time * 1000, 2),
                avg_time_per_text_ms=round((generation_time * 1000) / len(texts), 2),
            )

            return results

        except Exception as e:
            logger.error("Batch embedding generation failed", error=str(e))
            raise EmbeddingGeneratorError(
                f"Failed to generate batch embeddings: {str(e)}"
            )

    def get_embedding_dimensions(self) -> int:
        """
        Get the dimension size of embeddings.

        Returns:
            Number of dimensions in embedding vectors
        """
        return self.model.get_sentence_embedding_dimension()

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        Estimate token count for text.

        Uses simple heuristic: ~4 characters per token.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        # Simple heuristic: average 4 characters per token
        return max(1, len(text) // 4)

    def supports_batch_processing(self) -> bool:
        """
        Check if model supports batch processing.

        Returns:
            True (sentence-transformers always supports batching)
        """
        return True

    async def health_check(self) -> bool:
        """
        Check if embedding generator is healthy.

        Returns:
            True if model is loaded and functional
        """
        try:
            # Check if model is loaded
            if self._model is None:
                return False

            # Try generating a simple embedding
            test_vector = self.model.encode(
                "test", show_progress_bar=False, convert_to_numpy=True
            )

            # Verify output
            return len(test_vector) > 0

        except Exception as e:
            logger.error("Embedding generator health check failed", error=str(e))
            return False
