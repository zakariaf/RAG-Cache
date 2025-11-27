"""
API dependency injection.

Sandi Metz Principles:
- Single Responsibility: Dependency creation and injection
- Dependency Inversion: Create dependencies from abstractions
"""

from typing import Optional

from fastapi import Depends, Request
from qdrant_client import AsyncQdrantClient

from app.cache.redis_cache import RedisCache
from app.config import config
from app.embeddings.embedding_generator import EmbeddingGenerator
from app.llm.openai_provider import OpenAIProvider
from app.pipeline.semantic_matcher import SemanticMatcher
from app.repositories.qdrant_repository import QdrantRepository
from app.repositories.redis_repository import RedisRepository
from app.services.query_service import QueryService
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global instances for reuse
_embedding_generator: Optional[EmbeddingGenerator] = None
_qdrant_client: Optional[AsyncQdrantClient] = None


async def get_redis_cache(request: Request) -> RedisCache:
    """
    Get Redis cache service.

    Args:
        request: FastAPI request

    Returns:
        Redis cache service
    """
    app_state = request.app.state.app_state
    redis_repo = RedisRepository(app_state.redis_pool)
    return RedisCache(redis_repo)


async def get_embedding_generator() -> EmbeddingGenerator:
    """
    Get embedding generator (singleton).

    Returns:
        EmbeddingGenerator instance
    """
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
        logger.info("Embedding generator initialized")
    return _embedding_generator


async def get_qdrant_client() -> AsyncQdrantClient:
    """
    Get Qdrant client (singleton).

    Returns:
        AsyncQdrantClient instance
    """
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = AsyncQdrantClient(
            host=config.qdrant_host,
            port=config.qdrant_port,
        )
        logger.info("Qdrant client initialized")
    return _qdrant_client


async def get_semantic_matcher() -> Optional[SemanticMatcher]:
    """
    Get semantic matcher if enabled.

    Returns:
        SemanticMatcher instance or None
    """
    if not config.enable_semantic_cache:
        return None

    try:
        embedding_gen = await get_embedding_generator()
        qdrant_client = await get_qdrant_client()
        qdrant_repo = QdrantRepository(qdrant_client)

        # Ensure collection exists
        await qdrant_repo.create_collection()

        return SemanticMatcher(
            embedding_generator=embedding_gen,
            qdrant_repository=qdrant_repo,
            similarity_threshold=config.semantic_similarity_threshold,
        )
    except Exception as e:
        logger.error("Failed to initialize semantic matcher", error=str(e))
        return None


async def get_llm_provider(provider_name: str | None = None):
    """
    Get LLM provider.

    Args:
        provider_name: Provider name (defaults to config)

    Returns:
        LLM provider instance
    """
    provider = provider_name or config.default_llm_provider

    if provider == "openai":
        return OpenAIProvider(config.openai_api_key)
    # Add other providers here in the future
    # elif provider == "anthropic":
    #     return AnthropicProvider(config.anthropic_api_key)

    # Default to OpenAI
    return OpenAIProvider(config.openai_api_key)


async def get_query_service(
    request: Request, cache: RedisCache = Depends(get_redis_cache)  # noqa: B008
) -> QueryService:
    """
    Get query service with dependencies.

    Args:
        request: FastAPI request
        cache: Redis cache (injected)

    Returns:
        Query service instance
    """
    llm_provider = await get_llm_provider()
    semantic_matcher = await get_semantic_matcher()

    return QueryService(
        cache=cache,
        llm_provider=llm_provider,
        semantic_matcher=semantic_matcher,
    )
