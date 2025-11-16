"""Tests for LLM cost tracker."""

from unittest.mock import Mock

from app.llm.cost_tracker import CostEntry, CostSummary, LLMCostTracker


class TestCostTracker:
    """Test LLM cost tracker."""

    def test_track_request(self):
        """Test tracking a single request."""
        tracker = LLMCostTracker()

        cost = tracker.track_request(
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
        )

        assert cost > 0
        assert tracker.get_request_count() == 1
        assert tracker.get_total_tokens() == 150

    def test_track_multiple_requests(self):
        """Test tracking multiple requests."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("anthropic", "claude-3-sonnet", 150, 75)
        tracker.track_request("openai", "gpt-4", 200, 100)

        assert tracker.get_request_count() == 3
        assert tracker.get_total_tokens() == 675

    def test_get_summary_empty(self):
        """Test getting summary with no entries."""
        tracker = LLMCostTracker()

        summary = tracker.get_summary()

        assert summary.total_cost == 0.0
        assert summary.total_requests == 0
        assert summary.total_tokens == 0
        assert summary.provider_costs == {}
        assert summary.model_costs == {}

    def test_get_summary_with_entries(self):
        """Test getting summary with tracked entries."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("openai", "gpt-4", 100, 50)

        summary = tracker.get_summary()

        assert summary.total_cost > 0
        assert summary.total_requests == 2
        assert summary.total_tokens == 300
        assert "openai" in summary.provider_costs
        assert "gpt-3.5-turbo" in summary.model_costs
        assert "gpt-4" in summary.model_costs

    def test_get_summary_provider_costs(self):
        """Test provider cost aggregation in summary."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("anthropic", "claude-3-sonnet", 100, 50)
        tracker.track_request("openai", "gpt-4", 100, 50)

        summary = tracker.get_summary()

        assert "openai" in summary.provider_costs
        assert "anthropic" in summary.provider_costs
        assert summary.provider_costs["openai"] > summary.provider_costs["anthropic"]

    def test_get_summary_model_costs(self):
        """Test model cost aggregation in summary."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("openai", "gpt-4", 100, 50)

        summary = tracker.get_summary()

        assert "gpt-3.5-turbo" in summary.model_costs
        assert "gpt-4" in summary.model_costs

    def test_get_entries_by_provider(self):
        """Test getting entries filtered by provider."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("anthropic", "claude-3-sonnet", 100, 50)
        tracker.track_request("openai", "gpt-4", 100, 50)

        openai_entries = tracker.get_entries_by_provider("openai")
        anthropic_entries = tracker.get_entries_by_provider("anthropic")

        assert len(openai_entries) == 2
        assert len(anthropic_entries) == 1
        assert all(e.provider == "openai" for e in openai_entries)
        assert all(e.provider == "anthropic" for e in anthropic_entries)

    def test_get_entries_by_model(self):
        """Test getting entries filtered by model."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("openai", "gpt-3.5-turbo", 200, 100)
        tracker.track_request("openai", "gpt-4", 150, 75)

        gpt35_entries = tracker.get_entries_by_model("gpt-3.5-turbo")
        gpt4_entries = tracker.get_entries_by_model("gpt-4")

        assert len(gpt35_entries) == 2
        assert len(gpt4_entries) == 1
        assert all(e.model == "gpt-3.5-turbo" for e in gpt35_entries)
        assert all(e.model == "gpt-4" for e in gpt4_entries)

    def test_get_total_cost(self):
        """Test getting total cost."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("openai", "gpt-4", 100, 50)

        total_cost = tracker.get_total_cost()

        assert total_cost > 0
        assert total_cost == tracker.get_summary().total_cost

    def test_get_total_tokens(self):
        """Test getting total tokens."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("openai", "gpt-4", 200, 100)

        total_tokens = tracker.get_total_tokens()

        assert total_tokens == 450  # (100+50) + (200+100)

    def test_get_request_count(self):
        """Test getting request count."""
        tracker = LLMCostTracker()

        assert tracker.get_request_count() == 0

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        assert tracker.get_request_count() == 1

        tracker.track_request("anthropic", "claude-3-sonnet", 100, 50)
        assert tracker.get_request_count() == 2

    def test_reset(self):
        """Test resetting tracker."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("anthropic", "claude-3-sonnet", 100, 50)

        assert tracker.get_request_count() == 2

        tracker.reset()

        assert tracker.get_request_count() == 0
        assert tracker.get_total_cost() == 0.0
        assert tracker.get_total_tokens() == 0

    def test_get_all_entries(self):
        """Test getting all entries."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("anthropic", "claude-3-sonnet", 100, 50)

        entries = tracker.get_all_entries()

        assert len(entries) == 2
        assert isinstance(entries[0], CostEntry)
        assert isinstance(entries[1], CostEntry)

    def test_get_all_entries_returns_copy(self):
        """Test that get_all_entries returns a copy."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)

        entries = tracker.get_all_entries()
        entries.clear()

        # Original entries should not be affected
        assert tracker.get_request_count() == 1

    def test_cost_entry_structure(self):
        """Test cost entry contains correct data."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)

        entries = tracker.get_all_entries()
        entry = entries[0]

        assert entry.provider == "openai"
        assert entry.model == "gpt-3.5-turbo"
        assert entry.prompt_tokens == 100
        assert entry.completion_tokens == 50
        assert entry.cost > 0
        assert entry.timestamp is not None

    def test_cost_summary_structure(self):
        """Test cost summary contains correct structure."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        tracker.track_request("anthropic", "claude-3-sonnet", 150, 75)

        summary = tracker.get_summary()

        assert isinstance(summary, CostSummary)
        assert isinstance(summary.total_cost, float)
        assert isinstance(summary.total_requests, int)
        assert isinstance(summary.total_tokens, int)
        assert isinstance(summary.provider_costs, dict)
        assert isinstance(summary.model_costs, dict)

    def test_tracker_with_custom_calculator(self):
        """Test tracker with custom cost calculator."""
        mock_calculator = Mock()
        mock_calculator.calculate.return_value = 0.05

        tracker = LLMCostTracker(cost_calculator=mock_calculator)

        cost = tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)

        assert cost == 0.05
        mock_calculator.calculate.assert_called_once_with(
            prompt_tokens=100, completion_tokens=50, model="gpt-3.5-turbo"
        )

    def test_get_entries_by_provider_empty(self):
        """Test getting entries for non-existent provider."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)

        entries = tracker.get_entries_by_provider("nonexistent")

        assert len(entries) == 0

    def test_get_entries_by_model_empty(self):
        """Test getting entries for non-existent model."""
        tracker = LLMCostTracker()

        tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)

        entries = tracker.get_entries_by_model("nonexistent")

        assert len(entries) == 0

    def test_multiple_providers_same_model(self):
        """Test tracking same model from different providers."""
        tracker = LLMCostTracker()

        # Note: This is hypothetical - just testing the tracker logic
        tracker.track_request("provider1", "model-x", 100, 50)
        tracker.track_request("provider2", "model-x", 100, 50)

        summary = tracker.get_summary()

        assert len(summary.provider_costs) == 2
        assert "provider1" in summary.provider_costs
        assert "provider2" in summary.provider_costs

    def test_accumulation_over_time(self):
        """Test that costs accumulate correctly."""
        tracker = LLMCostTracker()

        # Track multiple requests
        cost1 = tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        total_after_1 = tracker.get_total_cost()

        cost2 = tracker.track_request("openai", "gpt-3.5-turbo", 100, 50)
        total_after_2 = tracker.get_total_cost()

        assert total_after_1 == cost1
        assert total_after_2 == cost1 + cost2
        assert total_after_2 > total_after_1
