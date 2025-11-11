"""
Query processing service.

Orchestrates cache checking and LLM calls.

Sandi Metz Principles:
- Single Responsibility: Query orchestration
- Small methods: Each method < 10 lines
- Dependency Injection: Cache and LLM injected
"""

import time
from typing import Optional

from app.cache.redis_cache import RedisCache
from app.llm.provider import BaseLLMProvider
from app.models.cache_entry import CacheEntry
from app.models.query import QueryRequest
from app.models.response import CacheInfo, QueryResponse, UsageMetrics
from app.utils.hasher import generate_cache_key
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueryService:
    """
    Main query processing service.

    Coordinates cache and LLM operations.
    """

    def __init__(self, cache: RedisCache, llm_provider: BaseLLMProvider):
        """
        Initialize service.

        Args:
            cache: Redis cache service
            llm_provider: LLM provider
        """
        self._cache = cache
        self._llm = llm_provider

    async def process(self, request: QueryRequest) -> QueryResponse:
        """
        Process query with caching.

        Args:
            request: Query request

        Returns:
            Query response
        """
        start_time = time.time()

        # Try cache if enabled
        if request.use_cache:
            cached = await self._check_cache(request)
            if cached:
                return self._build_cached_response(cached, start_time)

        # Call LLM
        llm_response = await self._call_llm(request)

        # Store in cache
        if request.use_cache:
            await self._store_in_cache(request, llm_response)

        # Build response
        return self._build_response(llm_response, start_time)

    async def _check_cache(self, request: QueryRequest) -> Optional[CacheEntry]:
        """
        Check cache for query.

        Args:
            request: Query request

        Returns:
            Cache entry if found
        """
        try:
            return await self._cache.get(request.query)
        except Exception as e:
            logger.error("Cache check failed", error=str(e))
            return None

    async def _call_llm(self, request: QueryRequest):
        """
        Call LLM provider.

        Args:
            request: Query request

        Returns:
            LLM response
        """
        return await self._llm.complete(request)

    async def _store_in_cache(self, request: QueryRequest, llm_response):
        """
        Store response in cache.

        Args:
            request: Query request
            llm_response: LLM response
        """
        entry = CacheEntry(
            query_hash=generate_cache_key(request.query),
            original_query=request.query,
            response=llm_response.content,
            provider=self._llm.get_name(),
            model=llm_response.model,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            embedding=None,
        )

        try:
            await self._cache.set(entry)
        except Exception as e:
            logger.error("Cache store failed", error=str(e))

    def _build_cached_response(
        self, entry: CacheEntry, start_time: float
    ) -> QueryResponse:
        """
        Build response from cache entry.

        Args:
            entry: Cache entry
            start_time: Request start time

        Returns:
            Query response
        """
        latency = (time.time() - start_time) * 1000

        return QueryResponse(
            response=entry.response,
            provider=entry.provider,
            model=entry.model,
            usage=UsageMetrics.create(entry.prompt_tokens, entry.completion_tokens),
            cache_info=CacheInfo.exact_hit(),
            latency_ms=latency,
        )

    def _build_response(self, llm_response, start_time: float) -> QueryResponse:
        """
        Build response from LLM.

        Args:
            llm_response: LLM response
            start_time: Request start time

        Returns:
            Query response
        """
        latency = (time.time() - start_time) * 1000

        return QueryResponse(
            response=llm_response.content,
            provider=self._llm.get_name(),
            model=llm_response.model,
            usage=UsageMetrics.create(
                llm_response.prompt_tokens, llm_response.completion_tokens
            ),
            cache_info=CacheInfo.miss(),
            latency_ms=latency,
        )
