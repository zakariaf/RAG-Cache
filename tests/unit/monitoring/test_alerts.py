"""Tests for alert management."""

import pytest
import time
from unittest.mock import MagicMock

from app.monitoring.alerts import (
    AlertRule,
    Alert,
    AlertManager,
    AlertLevel,
    AlertState,
    create_default_alerts,
)


class TestAlertRule:
    """Test alert rule functionality."""

    def test_alert_rule_creation(self):
        """Test creating alert rule."""
        rule = AlertRule(
            name="test_alert",
            description="Test alert description",
            level=AlertLevel.WARNING,
            condition=lambda: True,
        )

        assert rule.name == "test_alert"
        assert rule.level == AlertLevel.WARNING
        assert rule.state == AlertState.OK

    def test_evaluate_condition_true(self):
        """Test evaluating when condition is true."""
        rule = AlertRule(
            name="test_alert",
            description="Test",
            level=AlertLevel.WARNING,
            condition=lambda: True,
            for_duration_seconds=0,
        )

        state = rule.evaluate()

        assert state == AlertState.PENDING

    def test_evaluate_condition_false(self):
        """Test evaluating when condition is false."""
        rule = AlertRule(
            name="test_alert",
            description="Test",
            level=AlertLevel.WARNING,
            condition=lambda: False,
        )

        state = rule.evaluate()

        assert state == AlertState.OK

    def test_evaluate_firing_after_duration(self):
        """Test alert fires after duration."""
        rule = AlertRule(
            name="test_alert",
            description="Test",
            level=AlertLevel.WARNING,
            condition=lambda: True,
            for_duration_seconds=0,  # Immediate
        )

        rule.evaluate()  # PENDING
        state = rule.evaluate()  # FIRING

        assert state == AlertState.FIRING

    def test_evaluate_resolved(self):
        """Test alert resolves when condition becomes false."""
        condition_value = [True]  # Use list to allow mutation in closure

        rule = AlertRule(
            name="test_alert",
            description="Test",
            level=AlertLevel.WARNING,
            condition=lambda: condition_value[0],
            for_duration_seconds=0,
        )

        rule.evaluate()  # PENDING
        rule.evaluate()  # FIRING

        condition_value[0] = False
        state = rule.evaluate()

        assert state == AlertState.RESOLVED

    def test_is_firing(self):
        """Test is_firing property."""
        rule = AlertRule(
            name="test_alert",
            description="Test",
            level=AlertLevel.WARNING,
            condition=lambda: True,
            for_duration_seconds=0,
        )

        assert rule.is_firing is False

        rule.evaluate()
        rule.evaluate()

        assert rule.is_firing is True

    def test_to_dict(self):
        """Test conversion to dict."""
        rule = AlertRule(
            name="test_alert",
            description="Test",
            level=AlertLevel.WARNING,
            condition=lambda: False,
        )

        result = rule.to_dict()

        assert result["name"] == "test_alert"
        assert result["level"] == "warning"
        assert result["state"] == "ok"


class TestAlert:
    """Test alert instance."""

    def test_alert_creation(self):
        """Test creating alert."""
        alert = Alert(
            rule_name="test_alert",
            level=AlertLevel.ERROR,
            message="Test message",
            fired_at=time.time(),
        )

        assert alert.rule_name == "test_alert"
        assert alert.level == AlertLevel.ERROR
        assert alert.is_resolved is False

    def test_alert_resolved(self):
        """Test resolved alert."""
        alert = Alert(
            rule_name="test_alert",
            level=AlertLevel.ERROR,
            message="Test",
            fired_at=time.time() - 60,
            resolved_at=time.time(),
        )

        assert alert.is_resolved is True
        assert alert.duration_seconds >= 60

    def test_to_dict(self):
        """Test conversion to dict."""
        alert = Alert(
            rule_name="test_alert",
            level=AlertLevel.WARNING,
            message="Test",
            fired_at=time.time(),
        )

        result = alert.to_dict()

        assert "rule_name" in result
        assert "level" in result
        assert "duration_seconds" in result


class TestAlertManager:
    """Test alert manager."""

    @pytest.fixture
    def manager(self):
        """Create alert manager."""
        return AlertManager()

    def test_register_rule(self, manager):
        """Test registering alert rule."""
        rule = AlertRule(
            name="test_alert",
            description="Test",
            level=AlertLevel.WARNING,
            condition=lambda: False,
        )

        manager.register_rule(rule)

        assert "test_alert" in manager._rules

    def test_unregister_rule(self, manager):
        """Test unregistering alert rule."""
        rule = AlertRule(
            name="test_alert",
            description="Test",
            level=AlertLevel.WARNING,
            condition=lambda: False,
        )

        manager.register_rule(rule)
        result = manager.unregister_rule("test_alert")

        assert result is True
        assert "test_alert" not in manager._rules

    def test_evaluate_all_creates_alerts(self, manager):
        """Test evaluating all rules creates alerts."""
        rule = AlertRule(
            name="test_alert",
            description="Test alert",
            level=AlertLevel.WARNING,
            condition=lambda: True,
            for_duration_seconds=0,
        )

        manager.register_rule(rule)
        manager.evaluate_all()  # PENDING
        alerts = manager.evaluate_all()  # FIRING

        assert len(alerts) == 1
        assert alerts[0].rule_name == "test_alert"

    def test_get_active_alerts(self, manager):
        """Test getting active alerts."""
        rule = AlertRule(
            name="test_alert",
            description="Test",
            level=AlertLevel.WARNING,
            condition=lambda: True,
            for_duration_seconds=0,
        )

        manager.register_rule(rule)
        manager.evaluate_all()
        manager.evaluate_all()

        active = manager.get_active_alerts()

        assert len(active) == 1

    def test_get_firing_alerts_by_level(self, manager):
        """Test filtering firing alerts by level."""
        manager.register_rule(
            AlertRule(
                name="warning_alert",
                description="Warning",
                level=AlertLevel.WARNING,
                condition=lambda: True,
                for_duration_seconds=0,
            )
        )
        manager.register_rule(
            AlertRule(
                name="error_alert",
                description="Error",
                level=AlertLevel.ERROR,
                condition=lambda: True,
                for_duration_seconds=0,
            )
        )

        manager.evaluate_all()
        manager.evaluate_all()

        warnings = manager.get_firing_alerts(AlertLevel.WARNING)
        errors = manager.get_firing_alerts(AlertLevel.ERROR)

        assert len(warnings) == 1
        assert len(errors) == 1

    def test_alert_handler(self, manager):
        """Test alert handler notification."""
        handler = MagicMock()
        manager.add_handler(handler)

        rule = AlertRule(
            name="test_alert",
            description="Test",
            level=AlertLevel.WARNING,
            condition=lambda: True,
            for_duration_seconds=0,
        )

        manager.register_rule(rule)
        manager.evaluate_all()
        manager.evaluate_all()

        handler.assert_called_once()

    def test_get_summary(self, manager):
        """Test getting alert summary."""
        summary = manager.get_summary()

        assert "total_rules" in summary
        assert "active_alerts" in summary
        assert "critical_alerts" in summary


class TestCreateDefaultAlerts:
    """Test default alert creation."""

    def test_creates_default_alerts(self):
        """Test creating default alerts."""
        from app.monitoring.aggregator import MetricsAggregator

        aggregator = MetricsAggregator()
        manager = create_default_alerts(aggregator)

        assert len(manager._rules) > 0
        assert "high_error_rate" in manager._rules
        assert "low_cache_hit_rate" in manager._rules

    def test_default_alerts_evaluate(self):
        """Test default alerts can be evaluated."""
        from app.monitoring.aggregator import MetricsAggregator

        aggregator = MetricsAggregator()
        manager = create_default_alerts(aggregator)

        # Should not raise
        alerts = manager.evaluate_all()

        assert isinstance(alerts, list)
