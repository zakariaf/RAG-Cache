"""
Metrics endpoint for monitoring.

Exposes application metrics for Prometheus/Grafana.

Sandi Metz Principles:
- Single Responsibility: Metrics exposure
- Observable: All key metrics tracked
- Standard format: Prometheus compatible
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, Request

from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/metrics")
async def get_metrics(request: Request) -> Dict[str, Any]:
    """
    Get application metrics.

    Returns:
        Dictionary of metrics
    """
    # Get pipeline performance monitor if available
    try:
        from app.pipeline.performance_monitor import get_monitor

        monitor = get_monitor()
        pipeline_metrics = monitor.get_summary()
    except Exception:
        pipeline_metrics = {}

    # Get Redis metrics if available
    redis_metrics = {}
    try:
        if hasattr(request.app.state, "app_state"):
            app_state = request.app.state.app_state
            if app_state.redis_pool:
                from app.cache.redis_cache import RedisCache
                from app.repositories.redis_repository import RedisRepository

                repo = RedisRepository(app_state.redis_pool)
                cache = RedisCache(repo)
                metrics = await cache.get_metrics()
                if metrics:
                    redis_metrics = {
                        "total_keys": metrics.total_keys,
                        "memory_used_bytes": metrics.memory_used_bytes,
                        "hits": metrics.hits,
                        "misses": metrics.misses,
                        "hit_rate": metrics.hit_rate,
                    }
    except Exception as e:
        logger.debug("Could not get Redis metrics", error=str(e))

    return {
        "application": {
            "name": config.app_name,
            "environment": config.app_env,
            "version": "0.1.0",
        },
        "pipeline": pipeline_metrics,
        "cache": redis_metrics,
        "config": {
            "semantic_cache_enabled": config.enable_semantic_cache,
            "exact_cache_enabled": config.enable_exact_cache,
            "similarity_threshold": config.semantic_similarity_threshold,
            "cache_ttl_seconds": config.cache_ttl_seconds,
        },
    }


@router.get("/metrics/prometheus")
async def get_prometheus_metrics(request: Request) -> str:
    """
    Get metrics in Prometheus format.

    Returns:
        Prometheus-formatted metrics string
    """
    metrics = await get_metrics(request)
    lines = []

    # Application info
    lines.append(
        f'# HELP ragcache_info Application information'
    )
    lines.append(
        f'# TYPE ragcache_info gauge'
    )
    lines.append(
        f'ragcache_info{{version="0.1.0",environment="{config.app_env}"}} 1'
    )

    # Pipeline metrics
    pipeline = metrics.get("pipeline", {})
    if pipeline:
        lines.append(f'# HELP ragcache_requests_total Total requests processed')
        lines.append(f'# TYPE ragcache_requests_total counter')
        lines.append(
            f'ragcache_requests_total {pipeline.get("total_requests", 0)}'
        )

        lines.append(f'# HELP ragcache_cache_hits_total Total cache hits')
        lines.append(f'# TYPE ragcache_cache_hits_total counter')
        lines.append(f'ragcache_cache_hits_total {pipeline.get("cache_hits", 0)}')

        lines.append(f'# HELP ragcache_cache_hit_rate Cache hit rate')
        lines.append(f'# TYPE ragcache_cache_hit_rate gauge')
        lines.append(
            f'ragcache_cache_hit_rate {pipeline.get("cache_hit_rate", 0)}'
        )

        lines.append(f'# HELP ragcache_avg_latency_ms Average latency in ms')
        lines.append(f'# TYPE ragcache_avg_latency_ms gauge')
        lines.append(
            f'ragcache_avg_latency_ms {pipeline.get("avg_latency_ms", 0)}'
        )

    # Redis metrics
    cache = metrics.get("cache", {})
    if cache:
        lines.append(f'# HELP ragcache_redis_keys Total Redis keys')
        lines.append(f'# TYPE ragcache_redis_keys gauge')
        lines.append(f'ragcache_redis_keys {cache.get("total_keys", 0)}')

        lines.append(f'# HELP ragcache_redis_memory_bytes Redis memory usage')
        lines.append(f'# TYPE ragcache_redis_memory_bytes gauge')
        lines.append(
            f'ragcache_redis_memory_bytes {cache.get("memory_used_bytes", 0)}'
        )

    return "\n".join(lines)

