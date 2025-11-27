"""
Query processing service.

Orchestrates cache checking (exact + semantic) and LLM calls.

Sandi Metz Principles:
- Single Responsibility: Query orchestration
- Small methods: Each method < 10 lines
- Dependency Injection: Cache, semantic matcher, and LLM injected
"""

import time
from typing import Optional

from app.cache.redis_cache import RedisCache
from app.config import config
from app.llm.provider import BaseLLMProvider
from app.models.cache_entry import CacheEntry
from app.models.query import QueryRequest
from app.models.response import CacheInfo, QueryResponse, UsageMetrics
from app.pipeline.request_context import RequestContextManager
from app.pipeline.semantic_matcher import SemanticMatch, SemanticMatcher
from app.utils.hasher import generate_cache_key
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueryService:
    """
    Main query processing service.

    Coordinates exact cache, semantic cache, and LLM operations.
    """

    def __init__(
        self,
        cache: RedisCache,
        llm_provider: BaseLLMProvider,
        semantic_matcher: Optional[SemanticMatcher] = None,
    ):
        """
        Initialize service.

        Args:
            cache: Redis cache service for exact matching
            llm_provider: LLM provider
            semantic_matcher: Optional semantic matcher for semantic cache
        """
        self._cache = cache
        self._llm = llm_provider
        self._semantic = semantic_matcher
        self._enable_semantic = config.enable_semantic_cache and semantic_matcher

    async def process(self, request: QueryRequest) -> QueryResponse:
        """
        Process query with caching.

        Order: Exact cache -> Semantic cache -> LLM

        Args:
            request: Query request

        Returns:
            Query response
        """
        start_time = time.time()

        # Start request context
        ctx = RequestContextManager.start(query=request.query)

        try:
            # Try exact cache if enabled
            if request.use_cache:
                cached = await self._check_exact_cache(request)
                if cached:
                    ctx.mark_cache_checked(hit=True)
                    return self._build_cached_response(cached, start_time)
                ctx.mark_cache_checked(hit=False)

            # Try semantic cache if enabled
            if request.use_cache and self._enable_semantic:
                match = await self._check_semantic_cache(request)
                if match:
                    ctx.mark_semantic_checked(hit=True)
                    return self._build_semantic_response(match, start_time)
                ctx.mark_semantic_checked(hit=False)

            # Call LLM
            ctx.mark_llm_called()
            llm_response = await self._call_llm(request)

            # Store in caches
            if request.use_cache:
                await self._store_in_caches(request, llm_response)

            # Build response
            return self._build_response(llm_response, start_time)

        finally:
            # End request context
            RequestContextManager.end()

    async def _check_exact_cache(self, request: QueryRequest) -> Optional[CacheEntry]:
        """
        Check exact cache for query.

        Args:
            request: Query request

        Returns:
            Cache entry if found
        """
        try:
            return await self._cache.get(request.query)
        except Exception as e:
            logger.error("Exact cache check failed", error=str(e))
            return None

    async def _check_semantic_cache(
        self, request: QueryRequest
    ) -> Optional[SemanticMatch]:
        """
        Check semantic cache for similar queries.

        Args:
            request: Query request

        Returns:
            Semantic match if found above threshold
        """
        if not self._semantic:
            return None

        try:
            return await self._semantic.find_match(request.query)
        except Exception as e:
            logger.error("Semantic cache check failed", error=str(e))
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

    async def _store_in_caches(self, request: QueryRequest, llm_response):
        """
        Store response in both exact and semantic caches.

        Args:
            request: Query request
            llm_response: LLM response
        """
        query_hash = generate_cache_key(request.query)

        # Store in exact cache
        entry = CacheEntry(
            query_hash=query_hash,
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
            logger.error("Exact cache store failed", error=str(e))

        # Store in semantic cache
        if self._semantic:
            try:
                await self._semantic.store_for_matching(
                    query=request.query,
                    query_hash=query_hash,
                    response=llm_response.content,
                    provider=self._llm.get_name(),
                    model=llm_response.model,
                )
            except Exception as e:
                logger.error("Semantic cache store failed", error=str(e))

    def _build_cached_response(
        self, entry: CacheEntry, start_time: float
    ) -> QueryResponse:
        """
        Build response from exact cache entry.

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

    def _build_semantic_response(
        self, match: SemanticMatch, start_time: float
    ) -> QueryResponse:
        """
        Build response from semantic cache match.

        Args:
            match: Semantic match
            start_time: Request start time

        Returns:
            Query response
        """
        latency = (time.time() - start_time) * 1000

        return QueryResponse(
            response=match.cached_response,
            provider=match.provider,
            model=match.model,
            usage=UsageMetrics.create(0, 0),  # No new tokens used
            cache_info=CacheInfo.semantic_hit(match.similarity_score),
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
