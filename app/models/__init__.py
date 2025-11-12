"""
Models package for RAG Cache.

Exports all model classes for easy imports throughout the application.
"""

# Audit logging models
from app.models.audit import AuditLogEntry, AuditLogSummary, EventType

# Cache models
from app.models.cache_entry import CacheEntry, SemanticMatch

# Embedding models
from app.models.embedding import EmbeddingResult, EmbeddingVector

# Error models
from app.models.error import ErrorCode, ErrorResponse

# LLM models
from app.models.llm import LLMProvider, LLMResponse

# Provider configuration models
from app.models.provider import ProviderConfig, ProviderRegistry

# Query models
from app.models.query import QueryRequest

# Rate limiting models
from app.models.ratelimit import RateLimitConfig, RateLimitExceeded, RateLimitInfo

# Response models
from app.models.response import CacheInfo, HealthResponse, QueryResponse, UsageMetrics

# Statistics models
from app.models.statistics import CacheStatistics

__all__ = [
    # Audit
    "AuditLogEntry",
    "AuditLogSummary",
    "EventType",
    # Cache
    "CacheEntry",
    "SemanticMatch",
    # Embedding
    "EmbeddingResult",
    "EmbeddingVector",
    # Error
    "ErrorCode",
    "ErrorResponse",
    # LLM
    "LLMProvider",
    "LLMResponse",
    # Provider
    "ProviderConfig",
    "ProviderRegistry",
    # Query
    "QueryRequest",
    # Rate Limiting
    "RateLimitConfig",
    "RateLimitExceeded",
    "RateLimitInfo",
    # Response
    "CacheInfo",
    "HealthResponse",
    "QueryResponse",
    "UsageMetrics",
    # Statistics
    "CacheStatistics",
]
