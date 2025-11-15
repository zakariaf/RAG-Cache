"""
LLM response parser.

Sandi Metz Principles:
- Single Responsibility: Parse and normalize LLM responses
- Small methods: Each method < 10 lines
- Clear naming: Self-documenting code
"""

from typing import Any, Dict

from app.models.llm import LLMResponse


class LLMResponseParser:
    """
    Parser for LLM provider responses.

    Converts provider-specific responses into standardized LLMResponse format.
    """

    @staticmethod
    def parse_openai_response(response: Any, provider: str = "openai") -> LLMResponse:
        """
        Parse OpenAI API response.

        Args:
            response: OpenAI ChatCompletion response
            provider: Provider name (default: "openai")

        Returns:
            Standardized LLM response
        """
        content = LLMResponseParser._extract_openai_content(response)
        usage = LLMResponseParser._extract_openai_usage(response)

        return LLMResponse(
            content=content,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            model=response.model,
        )

    @staticmethod
    def parse_anthropic_response(
        response: Any, provider: str = "anthropic"
    ) -> LLMResponse:
        """
        Parse Anthropic API response.

        Args:
            response: Anthropic Messages response
            provider: Provider name (default: "anthropic")

        Returns:
            Standardized LLM response
        """
        content = LLMResponseParser._extract_anthropic_content(response)
        usage = LLMResponseParser._extract_anthropic_usage(response)

        return LLMResponse(
            content=content,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            model=response.model,
        )

    @staticmethod
    def _extract_openai_content(response: Any) -> str:
        """
        Extract content from OpenAI response.

        Args:
            response: OpenAI response

        Returns:
            Response content text
        """
        if not response.choices:
            return ""

        message = response.choices[0].message
        return message.content or ""

    @staticmethod
    def _extract_openai_usage(response: Any) -> Dict[str, int]:
        """
        Extract token usage from OpenAI response.

        Args:
            response: OpenAI response

        Returns:
            Dict with prompt_tokens and completion_tokens
        """
        if not response.usage:
            return {"prompt_tokens": 0, "completion_tokens": 0}

        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        }

    @staticmethod
    def _extract_anthropic_content(response: Any) -> str:
        """
        Extract content from Anthropic response.

        Args:
            response: Anthropic response

        Returns:
            Response content text
        """
        if not response.content:
            return ""

        # Anthropic returns list of content blocks
        return response.content[0].text

    @staticmethod
    def _extract_anthropic_usage(response: Any) -> Dict[str, int]:
        """
        Extract token usage from Anthropic response.

        Args:
            response: Anthropic response

        Returns:
            Dict with prompt_tokens and completion_tokens
        """
        usage = response.usage

        return {
            "prompt_tokens": usage.input_tokens,
            "completion_tokens": usage.output_tokens,
        }

    @staticmethod
    def create_empty_response(model: str = "unknown") -> LLMResponse:
        """
        Create empty response for error cases.

        Args:
            model: Model name

        Returns:
            Empty LLM response
        """
        return LLMResponse(
            content="",
            prompt_tokens=0,
            completion_tokens=0,
            model=model,
        )
