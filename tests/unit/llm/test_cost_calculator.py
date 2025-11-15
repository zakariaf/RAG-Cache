"""
Tests for cost calculator.
"""

import pytest

from app.llm.cost_calculator import CostCalculator


class TestCostCalculator:
    """Test cost calculator functionality."""

    @pytest.fixture
    def calculator(self) -> CostCalculator:
        """Create cost calculator instance."""
        return CostCalculator()

    def test_calculate_gpt35_turbo_cost(self, calculator: CostCalculator) -> None:
        """Test calculating cost for GPT-3.5 Turbo."""
        # 1000 input tokens, 500 output tokens
        cost = calculator.calculate(1000, 500, "gpt-3.5-turbo")

        # Input: 1000/1M * $0.50 = $0.0005
        # Output: 500/1M * $1.50 = $0.00075
        # Total: $0.00125
        assert abs(cost - 0.00125) < 0.00001

    def test_calculate_gpt4_cost(self, calculator: CostCalculator) -> None:
        """Test calculating cost for GPT-4."""
        cost = calculator.calculate(1000, 1000, "gpt-4")

        # Input: 1000/1M * $30 = $0.03
        # Output: 1000/1M * $60 = $0.06
        # Total: $0.09
        assert abs(cost - 0.09) < 0.00001

    def test_calculate_gpt4o_cost(self, calculator: CostCalculator) -> None:
        """Test calculating cost for GPT-4o."""
        cost = calculator.calculate(1000, 1000, "gpt-4o")

        # Input: 1000/1M * $2.50 = $0.0025
        # Output: 1000/1M * $10.00 = $0.01
        # Total: $0.0125
        assert abs(cost - 0.0125) < 0.00001

    def test_calculate_claude_cost(self, calculator: CostCalculator) -> None:
        """Test calculating cost for Claude 3.5 Sonnet."""
        cost = calculator.calculate(1000, 1000, "claude-3-5-sonnet-20241022")

        # Input: 1000/1M * $3.00 = $0.003
        # Output: 1000/1M * $15.00 = $0.015
        # Total: $0.018
        assert abs(cost - 0.018) < 0.00001

    def test_calculate_zero_tokens(self, calculator: CostCalculator) -> None:
        """Test calculating cost with zero tokens."""
        cost = calculator.calculate(0, 0, "gpt-3.5-turbo")
        assert cost == 0.0

    def test_calculate_unknown_model(self, calculator: CostCalculator) -> None:
        """Test calculating cost for unknown model."""
        cost = calculator.calculate(1000, 1000, "unknown-model")
        assert cost == 0.0

    def test_get_input_cost(self, calculator: CostCalculator) -> None:
        """Test calculating input cost only."""
        cost = calculator.get_input_cost(1000, "gpt-3.5-turbo")

        # 1000/1M * $0.50 = $0.0005
        assert abs(cost - 0.0005) < 0.00001

    def test_get_output_cost(self, calculator: CostCalculator) -> None:
        """Test calculating output cost only."""
        cost = calculator.get_output_cost(1000, "gpt-3.5-turbo")

        # 1000/1M * $1.50 = $0.0015
        assert abs(cost - 0.0015) < 0.00001

    def test_estimate_cost_default_ratio(self, calculator: CostCalculator) -> None:
        """Test estimating cost with default 50/50 ratio."""
        cost = calculator.estimate_cost(2000, "gpt-3.5-turbo")

        # 1000 input, 1000 output (50/50 split)
        # Input: $0.0005, Output: $0.0015
        # Total: $0.002
        assert abs(cost - 0.002) < 0.00001

    def test_estimate_cost_custom_ratio(self, calculator: CostCalculator) -> None:
        """Test estimating cost with custom ratio."""
        cost = calculator.estimate_cost(
            2000, "gpt-3.5-turbo", input_ratio=0.7  # 70% input, 30% output
        )

        # 1400 input, 600 output
        # Input: 1400/1M * $0.50 = $0.0007
        # Output: 600/1M * $1.50 = $0.0009
        # Total: $0.0016
        assert abs(cost - 0.0016) < 0.00001

    def test_get_pricing_openai(self, calculator: CostCalculator) -> None:
        """Test getting pricing for OpenAI models."""
        pricing = calculator._get_pricing("gpt-3.5-turbo")
        assert pricing is not None
        assert "input" in pricing
        assert "output" in pricing

    def test_get_pricing_anthropic(self, calculator: CostCalculator) -> None:
        """Test getting pricing for Anthropic models."""
        pricing = calculator._get_pricing("claude-3-5-sonnet-20241022")
        assert pricing is not None
        assert "input" in pricing
        assert "output" in pricing

    def test_get_pricing_unknown(self, calculator: CostCalculator) -> None:
        """Test getting pricing for unknown model."""
        pricing = calculator._get_pricing("unknown-model")
        assert pricing is None

    def test_large_token_count(self, calculator: CostCalculator) -> None:
        """Test calculating cost for large token count."""
        # 1 million tokens
        cost = calculator.calculate(1_000_000, 1_000_000, "gpt-3.5-turbo")

        # Input: $0.50, Output: $1.50
        # Total: $2.00
        assert abs(cost - 2.0) < 0.01

    def test_model_prefix_matching(self, calculator: CostCalculator) -> None:
        """Test that model prefix matching works."""
        # Should match "gpt-4" pricing even with version suffix
        cost = calculator.calculate(1000, 1000, "gpt-4-0613")

        # Should use gpt-4 pricing
        assert cost > 0
