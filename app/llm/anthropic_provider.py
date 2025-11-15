"""
Anthropic LLM provider implementation.

Sandi Metz Principles:
- Single Responsibility: Anthropic API interaction
- Small methods: Each method < 10 lines
- Dependency Injection: API key injected
"""

from anthropic import AnthropicError, AsyncAnthropic

from app.config import config
from app.exceptions import LLMProviderError
from app.llm.provider import BaseLLMProvider
from app.llm.rate_limiter import RateLimitConfig, RateLimiter
from app.llm.retry import RetryHandler
from app.models.llm import LLMResponse
from app.models.query import QueryRequest
from app.utils.logger import get_logger, log_llm_call

logger = get_logger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic/Claude implementation of LLM provider.

    Handles communication with Anthropic API with rate limiting and retry.
    """

    def __init__(
        self,
        api_key: str,
        rate_limiter: RateLimiter | None = None,
        retry_handler: RetryHandler | None = None,
        requests_per_minute: int = 50,
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            rate_limiter: Optional rate limiter (creates default if None)
            retry_handler: Optional retry handler (creates default if None)
            requests_per_minute: Rate limit (default: 50 RPM for tier 1)
        """
        self._api_key = api_key
        self._client: AsyncAnthropic | None = None
        self._rate_limiter = rate_limiter or RateLimiter(
            RateLimitConfig(requests_per_minute=requests_per_minute)
        )
        self._retry_handler = retry_handler or RetryHandler()

    async def complete(self, request: QueryRequest) -> LLMResponse:
        """
        Generate completion using Anthropic.

        Args:
            request: Query request

        Returns:
            LLM response

        Raises:
            LLMProviderError: If API call fails
        """
        await self._rate_limiter.acquire()

        try:
            return await self._retry_handler.execute(
                lambda: self._make_api_call(request)
            )
        except AnthropicError as e:
            error_msg = self._build_error_message(e, "Anthropic API call failed")
            logger.error("Anthropic error", error=str(e))
            raise LLMProviderError(error_msg) from e
        except Exception as e:
            error_msg = self._build_error_message(
                e, "Unexpected error in Anthropic provider"
            )
            logger.error("Unexpected error", error=str(e))
            raise LLMProviderError(error_msg) from e

    async def _make_api_call(self, request: QueryRequest) -> LLMResponse:
        """
        Make Anthropic API call.

        Args:
            request: Query request

        Returns:
            LLM response
        """
        client = self._get_client()
        model = request.get_model(config.default_model)

        # Use Claude 3.5 Sonnet if no model specified
        if model == config.default_model:
            model = "claude-3-5-sonnet-20241022"

        response = await client.messages.create(
            model=model,
            max_tokens=request.get_max_tokens(config.default_max_tokens),
            temperature=request.get_temperature(config.default_temperature),
            messages=[{"role": "user", "content": request.query}],
        )

        llm_response = LLMResponse(
            content=response.content[0].text,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            model=response.model,
        )

        log_llm_call(
            provider="anthropic",
            model=llm_response.model,
            tokens=llm_response.total_tokens,
        )

        return llm_response

    def get_name(self) -> str:
        """
        Get provider name.

        Returns:
            Provider name
        """
        return "anthropic"

    def _get_client(self) -> AsyncAnthropic:
        """
        Get or create Anthropic client.

        Returns:
            Anthropic async client
        """
        if not self._client:
            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client
