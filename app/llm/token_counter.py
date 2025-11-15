"""
Token counter for LLM providers.

Sandi Metz Principles:
- Single Responsibility: Count tokens
- Small methods: Each method < 10 lines
- Open/Closed: Easy to add new models
"""

from typing import Dict

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore

from app.utils.logger import get_logger

logger = get_logger(__name__)


class TokenCounter:
    """
    Count tokens for different LLM models.

    Supports both OpenAI and Anthropic models.
    """

    # Model-specific encodings
    OPENAI_ENCODINGS: Dict[str, str] = {
        "gpt-4": "cl100k_base",
        "gpt-4-32k": "cl100k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-4o": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "text-embedding-ada-002": "cl100k_base",
        "text-embedding-3-small": "cl100k_base",
        "text-embedding-3-large": "cl100k_base",
    }

    # Anthropic uses ~4 chars per token as approximation
    CHARS_PER_TOKEN_ANTHROPIC = 4

    def count(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Count tokens in text for given model.

        Args:
            text: Text to count tokens
            model: Model name

        Returns:
            Estimated token count
        """
        if self._is_openai_model(model):
            return self._count_openai_tokens(text, model)
        return self._count_anthropic_tokens(text)

    def _is_openai_model(self, model: str) -> bool:
        """
        Check if model is OpenAI.

        Args:
            model: Model name

        Returns:
            True if OpenAI model
        """
        return any(model.startswith(key) for key in self.OPENAI_ENCODINGS.keys())

    def _count_openai_tokens(self, text: str, model: str) -> int:
        """
        Count tokens for OpenAI models using tiktoken.

        Args:
            text: Text to count
            model: Model name

        Returns:
            Token count
        """
        if not tiktoken:
            logger.warning("tiktoken not available, using approximation")
            return self._approximate_count(text)

        try:
            encoding_name = self._get_encoding_name(model)
            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}, using approximation")
            return self._approximate_count(text)

    def _get_encoding_name(self, model: str) -> str:
        """
        Get encoding name for model.

        Args:
            model: Model name

        Returns:
            Encoding name
        """
        for model_prefix, encoding in self.OPENAI_ENCODINGS.items():
            if model.startswith(model_prefix):
                return encoding
        return "cl100k_base"  # default

    def _count_anthropic_tokens(self, text: str) -> int:
        """
        Count tokens for Anthropic models.

        Args:
            text: Text to count

        Returns:
            Estimated token count
        """
        # Anthropic approximation: ~4 characters per token
        return len(text) // self.CHARS_PER_TOKEN_ANTHROPIC

    def _approximate_count(self, text: str) -> int:
        """
        Approximate token count when exact counting unavailable.

        Args:
            text: Text to count

        Returns:
            Approximate token count (words / 0.75)
        """
        words = len(text.split())
        # Approximate: 1 token ~= 0.75 words
        return int(words / 0.75)
