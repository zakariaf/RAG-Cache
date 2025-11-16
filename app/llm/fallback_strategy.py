"""
LLM fallback strategy.

Sandi Metz Principles:
- Single Responsibility: Handle provider failover
- Small methods: Each method < 10 lines
- Clear naming: Self-documenting code
"""

from typing import List

from app.exceptions import LLMProviderError
from app.llm.provider import BaseLLMProvider
from app.models.llm import LLMResponse
from app.models.query import QueryRequest
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FallbackConfig:
    """Configuration for fallback strategy."""

    def __init__(
        self,
        max_retries: int = 3,
        retry_on_timeout: bool = True,
        retry_on_error: bool = True,
    ):
        """
        Initialize fallback configuration.

        Args:
            max_retries: Maximum retry attempts across providers (default: 3)
            retry_on_timeout: Retry with different provider on timeout (default: True)
            retry_on_error: Retry with different provider on error (default: True)
        """
        self.max_retries = max_retries
        self.retry_on_timeout = retry_on_timeout
        self.retry_on_error = retry_on_error


class LLMFallbackStrategy:
    """
    Fallback strategy for LLM providers.

    Automatically fails over to alternative providers on errors.
    """

    def __init__(self, config: FallbackConfig | None = None):
        """
        Initialize fallback strategy.

        Args:
            config: Fallback configuration (creates default if None)
        """
        self._config = config or FallbackConfig()

    async def execute_with_fallback(
        self,
        providers: List[BaseLLMProvider],
        request: QueryRequest,
    ) -> LLMResponse:
        """
        Execute request with automatic fallback.

        Args:
            providers: Ordered list of providers to try
            request: Query request

        Returns:
            LLM response from first successful provider

        Raises:
            LLMProviderError: If all providers fail
        """
        if not providers:
            raise LLMProviderError("No providers available")

        last_error: Exception | None = None
        attempts = 0

        for provider in providers:
            if attempts >= self._config.max_retries:
                break

            try:
                logger.info(
                    "Attempting request",
                    provider=provider.get_name(),
                    attempt=attempts + 1,
                )

                response = await provider.complete(request)

                logger.info(
                    "Request successful",
                    provider=provider.get_name(),
                    attempts=attempts + 1,
                )

                return response

            except Exception as e:
                last_error = e
                attempts += 1

                logger.warning(
                    "Provider failed, trying next",
                    provider=provider.get_name(),
                    error=str(e),
                    attempts=attempts,
                )

                if not self._should_retry(e):
                    raise

        # All providers failed
        error_msg = self._build_error_message(attempts, last_error)
        logger.error("All providers failed", attempts=attempts)
        raise LLMProviderError(error_msg) from last_error

    def _should_retry(self, error: Exception) -> bool:
        """
        Check if error should trigger retry.

        Args:
            error: Exception that occurred

        Returns:
            True if should retry with next provider
        """
        error_msg = str(error).lower()

        if self._config.retry_on_timeout and "timeout" in error_msg:
            return True

        if self._config.retry_on_error:
            return True

        return False

    def _build_error_message(self, attempts: int, last_error: Exception | None) -> str:
        """
        Build error message for all providers failing.

        Args:
            attempts: Number of attempts made
            last_error: Last error encountered

        Returns:
            Formatted error message
        """
        base_msg = f"All providers failed after {attempts} attempts"

        if last_error:
            return f"{base_msg}. Last error: {str(last_error)}"

        return base_msg

    async def execute_with_single_fallback(
        self,
        primary_provider: BaseLLMProvider,
        fallback_provider: BaseLLMProvider,
        request: QueryRequest,
    ) -> LLMResponse:
        """
        Execute with single fallback provider.

        Args:
            primary_provider: Primary provider to try first
            fallback_provider: Fallback provider if primary fails
            request: Query request

        Returns:
            LLM response from primary or fallback

        Raises:
            LLMProviderError: If both providers fail
        """
        try:
            logger.info("Trying primary provider", provider=primary_provider.get_name())
            return await primary_provider.complete(request)
        except Exception as e:
            logger.warning(
                "Primary provider failed, using fallback",
                primary=primary_provider.get_name(),
                fallback=fallback_provider.get_name(),
                error=str(e),
            )

            try:
                return await fallback_provider.complete(request)
            except Exception as fallback_error:
                error_msg = (
                    f"Both providers failed. "
                    f"Primary ({primary_provider.get_name()}): {str(e)}. "
                    f"Fallback ({fallback_provider.get_name()}): {str(fallback_error)}"
                )
                logger.error("Both providers failed", error=error_msg)
                raise LLMProviderError(error_msg) from fallback_error
