"""
Token cost calculator for LLM providers.

Sandi Metz Principles:
- Single Responsibility: Calculate API costs
- Small methods: Each method < 10 lines
- Open/Closed: Easy to add new models and pricing
"""

from typing import Dict

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CostCalculator:
    """
    Calculate costs for LLM API usage.

    Supports OpenAI and Anthropic pricing (as of November 2024).
    """

    # OpenAI pricing per million tokens (USD)
    OPENAI_PRICING: Dict[str, Dict[str, float]] = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-4-32k": {"input": 60.00, "output": 120.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "gpt-3.5-turbo-16k": {"input": 3.00, "output": 4.00},
    }

    # Anthropic pricing per million tokens (USD)
    ANTHROPIC_PRICING: Dict[str, Dict[str, float]] = {
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }

    def calculate(
        self, prompt_tokens: int, completion_tokens: int, model: str
    ) -> float:
        """
        Calculate cost for API call.

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model: Model name

        Returns:
            Cost in USD
        """
        pricing = self._get_pricing(model)
        if not pricing:
            logger.warning(f"No pricing for model: {model}, returning 0")
            return 0.0

        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _get_pricing(self, model: str) -> Dict[str, float] | None:
        """
        Get pricing for model.

        Args:
            model: Model name

        Returns:
            Pricing dict or None if not found
        """
        # Check OpenAI models
        for model_key in self.OPENAI_PRICING:
            if model.startswith(model_key):
                return self.OPENAI_PRICING[model_key]

        # Check Anthropic models
        if model in self.ANTHROPIC_PRICING:
            return self.ANTHROPIC_PRICING[model]

        return None

    def get_input_cost(self, tokens: int, model: str) -> float:
        """
        Calculate input (prompt) cost only.

        Args:
            tokens: Number of input tokens
            model: Model name

        Returns:
            Input cost in USD
        """
        return self.calculate(tokens, 0, model)

    def get_output_cost(self, tokens: int, model: str) -> float:
        """
        Calculate output (completion) cost only.

        Args:
            tokens: Number of output tokens
            model: Model name

        Returns:
            Output cost in USD
        """
        return self.calculate(0, tokens, model)

    def estimate_cost(
        self, total_tokens: int, model: str, input_ratio: float = 0.5
    ) -> float:
        """
        Estimate cost from total tokens.

        Args:
            total_tokens: Total token count
            model: Model name
            input_ratio: Ratio of input to total tokens (default: 0.5)

        Returns:
            Estimated cost in USD
        """
        input_tokens = int(total_tokens * input_ratio)
        output_tokens = total_tokens - input_tokens

        return self.calculate(input_tokens, output_tokens, model)
