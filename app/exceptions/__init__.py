"""
Custom exceptions for the application.
"""


class AppError(Exception):
    """Base exception for application errors."""

    pass


class LLMProviderError(AppError):
    """Raised when LLM provider fails."""

    pass


class EmbeddingError(AppError):
    """Raised when embedding generation fails."""

    pass


class ValidationError(AppError):
    """Raised when validation fails."""

    pass


class CacheError(AppError):
    """Raised when cache operations fail."""

    pass


class SemanticMatchError(AppError):
    """Raised when semantic matching fails."""

    pass


class ConfigurationError(AppError):
    """Raised when configuration is invalid."""

    pass
