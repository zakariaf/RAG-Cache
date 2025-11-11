"""
API dependency injection.

Sandi Metz Principles:
- Single Responsibility: Dependency creation and injection
- Dependency Inversion: Create dependencies from abstractions
"""

from fastapi import Depends, Request

from app.cache.redis_cache import RedisCache
from app.config import config
from app.llm.openai_provider import OpenAIProvider
from app.repositories.redis_repository import RedisRepository
from app.services.query_service import QueryService


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
    request: Request, cache: RedisCache = Depends(get_redis_cache)
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
    return QueryService(cache, llm_provider)
