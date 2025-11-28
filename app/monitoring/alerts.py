"""
Alert rules and management for monitoring.

Sandi Metz Principles:
- Single Responsibility: Alert definition and evaluation
- Configurable: Flexible alert rules
- Clear naming: Descriptive alert names
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(str, Enum):
    """Alert states."""

    OK = "ok"
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class AlertRule:
    """
    Definition of an alert rule.

    Evaluates conditions and triggers alerts.
    """

    name: str
    description: str
    level: AlertLevel
    condition: Callable[[], bool]  # Returns True if alert should fire
    threshold: float = 0.0
    for_duration_seconds: int = 60  # How long condition must be true
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    # Internal state
    _state: AlertState = AlertState.OK
    _first_triggered: Optional[float] = None
    _last_triggered: Optional[float] = None
    _resolved_at: Optional[float] = None

    def evaluate(self) -> AlertState:
        """
        Evaluate the alert condition.

        Returns:
            Current alert state
        """
        try:
            condition_met = self.condition()
        except Exception as e:
            logger.error("Alert evaluation failed", alert=self.name, error=str(e))
            return self._state

        now = time.time()

        if condition_met:
            if self._state == AlertState.OK:
                # Condition just became true
                self._first_triggered = now
                self._state = AlertState.PENDING
                logger.info("Alert pending", alert=self.name)

            elif self._state == AlertState.PENDING:
                # Check if we've been pending long enough
                if now - self._first_triggered >= self.for_duration_seconds:
                    self._state = AlertState.FIRING
                    self._last_triggered = now
                    logger.warning(
                        "Alert firing", alert=self.name, level=self.level.value
                    )

            elif self._state == AlertState.FIRING:
                self._last_triggered = now

        else:
            if self._state in (AlertState.PENDING, AlertState.FIRING):
                self._state = AlertState.RESOLVED
                self._resolved_at = now
                logger.info("Alert resolved", alert=self.name)
            elif self._state == AlertState.RESOLVED:
                # After being resolved, go back to OK
                self._state = AlertState.OK
                self._first_triggered = None
                self._resolved_at = None

        return self._state

    @property
    def is_firing(self) -> bool:
        """Check if alert is currently firing."""
        return self._state == AlertState.FIRING

    @property
    def state(self) -> AlertState:
        """Get current state."""
        return self._state

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "level": self.level.value,
            "state": self._state.value,
            "threshold": self.threshold,
            "for_duration_seconds": self.for_duration_seconds,
            "labels": self.labels,
            "annotations": self.annotations,
            "first_triggered": self._first_triggered,
            "last_triggered": self._last_triggered,
            "resolved_at": self._resolved_at,
        }


@dataclass
class Alert:
    """
    An active alert instance.

    Created when an AlertRule fires.
    """

    rule_name: str
    level: AlertLevel
    message: str
    fired_at: float
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    resolved_at: Optional[float] = None

    @property
    def is_resolved(self) -> bool:
        """Check if alert is resolved."""
        return self.resolved_at is not None

    @property
    def duration_seconds(self) -> float:
        """Get alert duration."""
        end_time = self.resolved_at or time.time()
        return end_time - self.fired_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_name": self.rule_name,
            "level": self.level.value,
            "message": self.message,
            "fired_at": self.fired_at,
            "labels": self.labels,
            "annotations": self.annotations,
            "resolved_at": self.resolved_at,
            "duration_seconds": self.duration_seconds,
        }


class AlertManager:
    """
    Manages alert rules and active alerts.

    Evaluates rules and tracks alert history.
    """

    def __init__(self):
        """Initialize alert manager."""
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._max_history = 1000
        self._handlers: List[Callable[[Alert], None]] = []

    def register_rule(self, rule: AlertRule) -> None:
        """
        Register an alert rule.

        Args:
            rule: Alert rule to register
        """
        self._rules[rule.name] = rule
        logger.info("Alert rule registered", rule=rule.name)

    def unregister_rule(self, name: str) -> bool:
        """
        Unregister an alert rule.

        Args:
            name: Rule name to unregister

        Returns:
            True if rule was removed
        """
        if name in self._rules:
            del self._rules[name]
            logger.info("Alert rule unregistered", rule=name)
            return True
        return False

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        Add an alert handler.

        Args:
            handler: Callable that receives Alert objects
        """
        self._handlers.append(handler)

    def evaluate_all(self) -> List[Alert]:
        """
        Evaluate all rules and return new/updated alerts.

        Returns:
            List of alerts that changed state
        """
        changed_alerts = []

        for name, rule in self._rules.items():
            previous_state = rule.state
            current_state = rule.evaluate()

            # Check for state changes
            if (
                current_state == AlertState.FIRING
                and previous_state != AlertState.FIRING
            ):
                # New alert
                alert = Alert(
                    rule_name=name,
                    level=rule.level,
                    message=rule.description,
                    fired_at=time.time(),
                    labels=rule.labels,
                    annotations=rule.annotations,
                )
                self._active_alerts[name] = alert
                changed_alerts.append(alert)
                self._notify_handlers(alert)

            elif current_state == AlertState.RESOLVED and name in self._active_alerts:
                # Alert resolved
                alert = self._active_alerts[name]
                alert.resolved_at = time.time()
                changed_alerts.append(alert)

                # Move to history
                self._alert_history.append(alert)
                if len(self._alert_history) > self._max_history:
                    self._alert_history.pop(0)

                del self._active_alerts[name]
                self._notify_handlers(alert)

        return changed_alerts

    def _notify_handlers(self, alert: Alert) -> None:
        """Notify all handlers of an alert."""
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(
                    "Alert handler failed", handler=handler.__name__, error=str(e)
                )

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self._active_alerts.values())

    def get_firing_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """
        Get currently firing alerts.

        Args:
            level: Optional level filter

        Returns:
            List of firing alerts
        """
        alerts = self.get_active_alerts()
        if level:
            alerts = [a for a in alerts if a.level == level]
        return alerts

    def get_alert_history(
        self, limit: int = 100, level: Optional[AlertLevel] = None
    ) -> List[Alert]:
        """
        Get alert history.

        Args:
            limit: Maximum alerts to return
            level: Optional level filter

        Returns:
            List of historical alerts
        """
        history = self._alert_history[-limit:]
        if level:
            history = [a for a in history if a.level == level]
        return history

    def get_summary(self) -> Dict[str, Any]:
        """Get alert summary."""
        active = self.get_active_alerts()
        return {
            "total_rules": len(self._rules),
            "active_alerts": len(active),
            "critical_alerts": len(
                [a for a in active if a.level == AlertLevel.CRITICAL]
            ),
            "error_alerts": len([a for a in active if a.level == AlertLevel.ERROR]),
            "warning_alerts": len([a for a in active if a.level == AlertLevel.WARNING]),
            "history_count": len(self._alert_history),
        }

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all registered rules."""
        return [rule.to_dict() for rule in self._rules.values()]


def create_default_alerts(aggregator) -> AlertManager:
    """
    Create default alert rules.

    Args:
        aggregator: MetricsAggregator instance

    Returns:
        Configured AlertManager
    """
    manager = AlertManager()

    # High error rate alert
    manager.register_rule(
        AlertRule(
            name="high_error_rate",
            description="Error rate exceeds 5%",
            level=AlertLevel.ERROR,
            condition=lambda: aggregator.requests.error_rate > 0.05,
            threshold=0.05,
            for_duration_seconds=60,
            labels={"category": "availability"},
        )
    )

    # Low cache hit rate alert
    manager.register_rule(
        AlertRule(
            name="low_cache_hit_rate",
            description="Cache hit rate below 20%",
            level=AlertLevel.WARNING,
            condition=lambda: (
                aggregator.cache.total_operations > 100
                and aggregator.cache.hit_rate < 0.2
            ),
            threshold=0.2,
            for_duration_seconds=300,
            labels={"category": "performance"},
        )
    )

    # High LLM latency alert
    manager.register_rule(
        AlertRule(
            name="high_llm_latency",
            description="Average LLM latency exceeds 5 seconds",
            level=AlertLevel.WARNING,
            condition=lambda: aggregator.llm.avg_latency_ms > 5000,
            threshold=5000,
            for_duration_seconds=120,
            labels={"category": "performance"},
        )
    )

    # LLM failure rate alert
    manager.register_rule(
        AlertRule(
            name="high_llm_failure_rate",
            description="LLM failure rate exceeds 10%",
            level=AlertLevel.ERROR,
            condition=lambda: (
                aggregator.llm.total_requests > 10 and aggregator.llm.success_rate < 0.9
            ),
            threshold=0.1,
            for_duration_seconds=60,
            labels={"category": "availability"},
        )
    )

    # High cost alert
    manager.register_rule(
        AlertRule(
            name="high_llm_cost",
            description="LLM cost exceeds $10",
            level=AlertLevel.WARNING,
            condition=lambda: aggregator.llm.total_cost > 10.0,
            threshold=10.0,
            for_duration_seconds=0,  # Immediate
            labels={"category": "cost"},
        )
    )

    return manager
