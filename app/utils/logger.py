"""
Structured logging configuration.

Following Sandi Metz principles:
- Single Responsibility: Logging setup and configuration
- Small functions: Each setup step isolated
- Clear naming: Descriptive function names
"""

import logging
import sys
from typing import Any

import structlog


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structured logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structured logger
    """
    return structlog.get_logger(name)


def log_request(method: str, path: str, **kwargs: Any) -> None:
    """
    Log HTTP request.

    Args:
        method: HTTP method
        path: Request path
        **kwargs: Additional context
    """
    logger = get_logger("http")
    logger.info("request", method=method, path=path, **kwargs)


def log_response(status_code: int, latency_ms: float, **kwargs: Any) -> None:
    """
    Log HTTP response.

    Args:
        status_code: Response status code
        latency_ms: Request latency in milliseconds
        **kwargs: Additional context
    """
    logger = get_logger("http")
    logger.info("response", status_code=status_code, latency_ms=latency_ms, **kwargs)


def log_cache_hit(query: str, source: str, **kwargs: Any) -> None:
    """
    Log cache hit.

    Args:
        query: Query text
        source: Cache source (exact/semantic)
        **kwargs: Additional context
    """
    logger = get_logger("cache")
    logger.info("cache_hit", query=query[:100], source=source, **kwargs)


def log_cache_miss(query: str, **kwargs: Any) -> None:
    """
    Log cache miss.

    Args:
        query: Query text
        **kwargs: Additional context
    """
    logger = get_logger("cache")
    logger.info("cache_miss", query=query[:100], **kwargs)


def log_llm_call(provider: str, model: str, tokens: int, **kwargs: Any) -> None:
    """
    Log LLM API call.

    Args:
        provider: LLM provider name
        model: Model name
        tokens: Total tokens used
        **kwargs: Additional context
    """
    logger = get_logger("llm")
    logger.info("llm_call", provider=provider, model=model, tokens=tokens, **kwargs)


def log_error(error: Exception, context: str, **kwargs: Any) -> None:
    """
    Log error with context.

    Args:
        error: Exception that occurred
        context: Error context
        **kwargs: Additional context
    """
    logger = get_logger("error")
    logger.error(
        "error_occurred",
        error=str(error),
        error_type=type(error).__name__,
        context=context,
        **kwargs
    )
