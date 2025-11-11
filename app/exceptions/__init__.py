"""
Custom exceptions for the application.

Sandi Metz Principles:
- Single Responsibility: Each exception type is specific
- Clear naming: Exception names describe the error
"""


class RAGCacheException(Exception):
    """Base exception for RAGCache application."""

    pass


class LLMProviderError(RAGCacheException):
    """Error occurred in LLM provider."""

    pass


class CacheError(RAGCacheException):
    """Error occurred in cache operations."""

    pass


class EmbeddingError(RAGCacheException):
    """Error occurred in embedding generation."""

    pass


class ConfigurationError(RAGCacheException):
    """Error in configuration."""

    pass
