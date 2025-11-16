"""
LLM context window management.

Sandi Metz Principles:
- Single Responsibility: Manage token limits
- Small methods: Each method < 10 lines
- Clear naming: Self-documenting code
"""

from dataclasses import dataclass

from app.exceptions import LLMProviderError
from app.llm.token_counter import TokenCounter
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ContextWindowConfig:
    """Configuration for context window limits."""

    # OpenAI context windows
    OPENAI_WINDOWS = {
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-3.5-turbo": 16385,
        "gpt-3.5-turbo-16k": 16385,
    }

    # Anthropic context windows
    ANTHROPIC_WINDOWS = {
        "claude-3-5-sonnet-20241022": 200000,
        "claude-3-5-sonnet-20240620": 200000,
        "claude-3-opus-20240229": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-haiku-20240307": 200000,
    }


class ContextWindowManager:
    """
    Manage LLM context window limits.

    Validates requests don't exceed model token limits.
    """

    def __init__(
        self,
        token_counter: TokenCounter | None = None,
        config: ContextWindowConfig | None = None,
    ):
        """
        Initialize context window manager.

        Args:
            token_counter: Token counter instance (creates default if None)
            config: Context window configuration (creates default if None)
        """
        self._counter = token_counter or TokenCounter()
        self._config = config or ContextWindowConfig()

    def validate_request(
        self,
        text: str,
        model: str,
        max_completion_tokens: int = 4000,
    ) -> None:
        """
        Validate request fits in context window.

        Args:
            text: Input text to validate
            model: Model name
            max_completion_tokens: Expected completion tokens

        Raises:
            LLMProviderError: If request exceeds context window
        """
        window_size = self._get_window_size(model)
        input_tokens = self._counter.count(text, model)
        total_tokens = input_tokens + max_completion_tokens

        if total_tokens > window_size:
            self._raise_window_error(
                input_tokens, max_completion_tokens, window_size, model
            )

        logger.debug(
            "Request within context window",
            model=model,
            input_tokens=input_tokens,
            total_tokens=total_tokens,
            window_size=window_size,
        )

    def get_max_completion_tokens(
        self,
        text: str,
        model: str,
        reserve_tokens: int = 100,
    ) -> int:
        """
        Calculate maximum completion tokens available.

        Args:
            text: Input text
            model: Model name
            reserve_tokens: Tokens to reserve for safety (default: 100)

        Returns:
            Maximum completion tokens available
        """
        window_size = self._get_window_size(model)
        input_tokens = self._counter.count(text, model)

        max_completion = window_size - input_tokens - reserve_tokens

        return max(0, max_completion)

    def _get_window_size(self, model: str) -> int:
        """
        Get context window size for model.

        Args:
            model: Model name

        Returns:
            Context window size in tokens
        """
        # Check OpenAI models (check longer names first)
        sorted_keys = sorted(self._config.OPENAI_WINDOWS.keys(), key=len, reverse=True)
        for model_key in sorted_keys:
            if model.startswith(model_key):
                return self._config.OPENAI_WINDOWS[model_key]

        # Check Anthropic models
        if model in self._config.ANTHROPIC_WINDOWS:
            return self._config.ANTHROPIC_WINDOWS[model]

        # Default fallback
        logger.warning(f"Unknown model {model}, using default window 4096")
        return 4096

    def _raise_window_error(
        self,
        input_tokens: int,
        completion_tokens: int,
        window_size: int,
        model: str,
    ) -> None:
        """
        Raise context window exceeded error.

        Args:
            input_tokens: Number of input tokens
            completion_tokens: Expected completion tokens
            window_size: Model's context window size
            model: Model name

        Raises:
            LLMProviderError: Always raises with details
        """
        total = input_tokens + completion_tokens
        error_msg = (
            f"Request exceeds context window for {model}. "
            f"Input: {input_tokens}, Completion: {completion_tokens}, "
            f"Total: {total}, Window: {window_size}"
        )

        logger.error(
            "Context window exceeded",
            model=model,
            input_tokens=input_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            window_size=window_size,
        )

        raise LLMProviderError(error_msg)

    def get_window_size(self, model: str) -> int:
        """
        Get context window size for model.

        Args:
            model: Model name

        Returns:
            Context window size in tokens
        """
        return self._get_window_size(model)

    def can_fit(
        self,
        text: str,
        model: str,
        max_completion_tokens: int = 4000,
    ) -> bool:
        """
        Check if request can fit in context window.

        Args:
            text: Input text
            model: Model name
            max_completion_tokens: Expected completion tokens

        Returns:
            True if request fits in window
        """
        try:
            self.validate_request(text, model, max_completion_tokens)
            return True
        except LLMProviderError:
            return False
