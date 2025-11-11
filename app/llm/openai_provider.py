"""
OpenAI LLM provider implementation.

Sandi Metz Principles:
- Single Responsibility: OpenAI API interaction
- Small methods: Each method < 10 lines
- Dependency Injection: API key injected
"""

from openai import AsyncOpenAI, OpenAIError

from app.config import config
from app.exceptions import LLMProviderError
from app.llm.provider import BaseLLMProvider
from app.models.llm import LLMResponse
from app.models.query import QueryRequest
from app.utils.logger import get_logger, log_llm_call

logger = get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI implementation of LLM provider.

    Handles communication with OpenAI API.
    """

    def __init__(self, api_key: str):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
        """
        self._api_key = api_key
        self._client: AsyncOpenAI | None = None

    async def complete(self, request: QueryRequest) -> LLMResponse:
        """
        Generate completion using OpenAI.

        Args:
            request: Query request

        Returns:
            LLM response

        Raises:
            LLMProviderError: If API call fails
        """
        client = self._get_client()

        try:
            response = await client.chat.completions.create(
                model=request.get_model(config.default_model),
                messages=[{"role": "user", "content": request.query}],
                max_tokens=request.get_max_tokens(config.default_max_tokens),
                temperature=request.get_temperature(config.default_temperature),
            )

            llm_response = LLMResponse(
                content=response.choices[0].message.content or "",
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                model=response.model,
            )

            log_llm_call(
                provider="openai",
                model=llm_response.model,
                tokens=llm_response.total_tokens
            )

            return llm_response

        except OpenAIError as e:
            error_msg = self._build_error_message(e, "OpenAI API call failed")
            logger.error("OpenAI error", error=str(e))
            raise LLMProviderError(error_msg) from e
        except Exception as e:
            error_msg = self._build_error_message(e, "Unexpected error in OpenAI provider")
            logger.error("Unexpected error", error=str(e))
            raise LLMProviderError(error_msg) from e

    def get_name(self) -> str:
        """
        Get provider name.

        Returns:
            Provider name
        """
        return "openai"

    def _get_client(self) -> AsyncOpenAI:
        """
        Get or create OpenAI client.

        Returns:
            OpenAI async client
        """
        if not self._client:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client
