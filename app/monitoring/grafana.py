"""
Grafana dashboard configuration generator.

Generates JSON configuration for Grafana dashboards.

Sandi Metz Principles:
- Single Responsibility: Dashboard generation
- Configurable: Flexible panel configuration
- Exportable: JSON output for Grafana import
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GrafanaPanel:
    """
    Configuration for a Grafana panel.

    Represents a single visualization in the dashboard.
    """

    title: str
    panel_type: str = "stat"  # stat, graph, gauge, table, heatmap
    datasource: str = "Prometheus"
    targets: List[Dict[str, Any]] = field(default_factory=list)
    grid_pos: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 6, "h": 4})
    options: Dict[str, Any] = field(default_factory=dict)
    field_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, panel_id: int) -> Dict[str, Any]:
        """Convert to Grafana panel JSON."""
        return {
            "id": panel_id,
            "title": self.title,
            "type": self.panel_type,
            "datasource": {"type": "prometheus", "uid": self.datasource},
            "targets": self.targets,
            "gridPos": self.grid_pos,
            "options": self.options,
            "fieldConfig": self.field_config,
        }


@dataclass
class GrafanaDashboard:
    """
    Grafana dashboard configuration.

    Generates complete dashboard JSON for import.
    """

    title: str = "RAGCache Monitoring"
    uid: str = "ragcache-main"
    tags: List[str] = field(default_factory=lambda: ["ragcache", "monitoring"])
    refresh: str = "10s"
    panels: List[GrafanaPanel] = field(default_factory=list)
    time_from: str = "now-1h"
    time_to: str = "now"

    def add_panel(self, panel: GrafanaPanel) -> None:
        """Add a panel to the dashboard."""
        self.panels.append(panel)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Grafana dashboard JSON."""
        return {
            "dashboard": {
                "uid": self.uid,
                "title": self.title,
                "tags": self.tags,
                "timezone": "browser",
                "refresh": self.refresh,
                "time": {
                    "from": self.time_from,
                    "to": self.time_to,
                },
                "panels": [
                    panel.to_dict(i + 1)
                    for i, panel in enumerate(self.panels)
                ],
                "schemaVersion": 38,
                "version": 1,
            },
            "overwrite": True,
        }

    def to_json(self, indent: int = 2) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def create_ragcache_dashboard() -> GrafanaDashboard:
    """
    Create the default RAGCache monitoring dashboard.

    Returns:
        Configured GrafanaDashboard
    """
    dashboard = GrafanaDashboard()

    # Row 1: Overview Stats
    dashboard.add_panel(GrafanaPanel(
        title="Total Requests",
        panel_type="stat",
        targets=[{
            "expr": 'sum(ragcache_requests_total)',
            "legendFormat": "Total Requests",
        }],
        grid_pos={"x": 0, "y": 0, "w": 4, "h": 4},
        options={
            "colorMode": "value",
            "graphMode": "none",
            "textMode": "auto",
        },
    ))

    dashboard.add_panel(GrafanaPanel(
        title="Cache Hit Rate",
        panel_type="gauge",
        targets=[{
            "expr": 'ragcache_cache_hit_rate',
            "legendFormat": "Hit Rate",
        }],
        grid_pos={"x": 4, "y": 0, "w": 4, "h": 4},
        options={
            "showThresholdLabels": False,
            "showThresholdMarkers": True,
        },
        field_config={
            "defaults": {
                "unit": "percentunit",
                "min": 0,
                "max": 1,
                "thresholds": {
                    "mode": "percentage",
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "yellow", "value": 50},
                        {"color": "green", "value": 80},
                    ],
                },
            },
        },
    ))

    dashboard.add_panel(GrafanaPanel(
        title="LLM Cost",
        panel_type="stat",
        targets=[{
            "expr": 'sum(ragcache_llm_cost_total)',
            "legendFormat": "Total Cost",
        }],
        grid_pos={"x": 8, "y": 0, "w": 4, "h": 4},
        options={
            "colorMode": "value",
            "graphMode": "none",
        },
        field_config={
            "defaults": {
                "unit": "currencyUSD",
            },
        },
    ))

    dashboard.add_panel(GrafanaPanel(
        title="Error Rate",
        panel_type="stat",
        targets=[{
            "expr": 'sum(rate(ragcache_requests_errors_total[5m])) / sum(rate(ragcache_requests_total[5m]))',
            "legendFormat": "Error Rate",
        }],
        grid_pos={"x": 12, "y": 0, "w": 4, "h": 4},
        options={
            "colorMode": "value",
        },
        field_config={
            "defaults": {
                "unit": "percentunit",
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 0.01},
                        {"color": "red", "value": 0.05},
                    ],
                },
            },
        },
    ))

    dashboard.add_panel(GrafanaPanel(
        title="Uptime",
        panel_type="stat",
        targets=[{
            "expr": 'ragcache_uptime_seconds',
            "legendFormat": "Uptime",
        }],
        grid_pos={"x": 16, "y": 0, "w": 4, "h": 4},
        field_config={
            "defaults": {
                "unit": "s",
            },
        },
    ))

    dashboard.add_panel(GrafanaPanel(
        title="Tokens Saved",
        panel_type="stat",
        targets=[{
            "expr": 'sum(ragcache_tokens_saved_total)',
            "legendFormat": "Tokens Saved",
        }],
        grid_pos={"x": 20, "y": 0, "w": 4, "h": 4},
    ))

    # Row 2: Request Metrics
    dashboard.add_panel(GrafanaPanel(
        title="Request Rate",
        panel_type="timeseries",
        targets=[{
            "expr": 'sum(rate(ragcache_requests_total[1m])) by (method)',
            "legendFormat": "{{method}}",
        }],
        grid_pos={"x": 0, "y": 4, "w": 12, "h": 6},
        options={
            "tooltip": {"mode": "multi"},
            "legend": {"displayMode": "table", "placement": "right"},
        },
    ))

    dashboard.add_panel(GrafanaPanel(
        title="Request Latency",
        panel_type="timeseries",
        targets=[
            {
                "expr": 'histogram_quantile(0.50, sum(rate(ragcache_request_duration_seconds_bucket[5m])) by (le))',
                "legendFormat": "p50",
            },
            {
                "expr": 'histogram_quantile(0.95, sum(rate(ragcache_request_duration_seconds_bucket[5m])) by (le))',
                "legendFormat": "p95",
            },
            {
                "expr": 'histogram_quantile(0.99, sum(rate(ragcache_request_duration_seconds_bucket[5m])) by (le))',
                "legendFormat": "p99",
            },
        ],
        grid_pos={"x": 12, "y": 4, "w": 12, "h": 6},
        field_config={
            "defaults": {
                "unit": "s",
            },
        },
    ))

    # Row 3: Cache Metrics
    dashboard.add_panel(GrafanaPanel(
        title="Cache Operations",
        panel_type="timeseries",
        targets=[
            {
                "expr": 'sum(rate(ragcache_cache_hits_total[1m])) by (type)',
                "legendFormat": "Hits ({{type}})",
            },
            {
                "expr": 'sum(rate(ragcache_cache_misses_total[1m]))',
                "legendFormat": "Misses",
            },
        ],
        grid_pos={"x": 0, "y": 10, "w": 12, "h": 6},
    ))

    dashboard.add_panel(GrafanaPanel(
        title="Cache Hit Rate Over Time",
        panel_type="timeseries",
        targets=[{
            "expr": 'ragcache_cache_hit_rate',
            "legendFormat": "Hit Rate",
        }],
        grid_pos={"x": 12, "y": 10, "w": 12, "h": 6},
        field_config={
            "defaults": {
                "unit": "percentunit",
                "min": 0,
                "max": 1,
            },
        },
    ))

    # Row 4: LLM Metrics
    dashboard.add_panel(GrafanaPanel(
        title="LLM Requests by Provider",
        panel_type="timeseries",
        targets=[{
            "expr": 'sum(rate(ragcache_llm_requests_total[1m])) by (provider)',
            "legendFormat": "{{provider}}",
        }],
        grid_pos={"x": 0, "y": 16, "w": 8, "h": 6},
    ))

    dashboard.add_panel(GrafanaPanel(
        title="LLM Latency by Provider",
        panel_type="timeseries",
        targets=[{
            "expr": 'histogram_quantile(0.95, sum(rate(ragcache_llm_latency_seconds_bucket[5m])) by (le, provider))',
            "legendFormat": "{{provider}} p95",
        }],
        grid_pos={"x": 8, "y": 16, "w": 8, "h": 6},
        field_config={
            "defaults": {
                "unit": "s",
            },
        },
    ))

    dashboard.add_panel(GrafanaPanel(
        title="Token Usage",
        panel_type="timeseries",
        targets=[{
            "expr": 'sum(rate(ragcache_llm_tokens_total[5m])) by (provider)',
            "legendFormat": "{{provider}}",
        }],
        grid_pos={"x": 16, "y": 16, "w": 8, "h": 6},
    ))

    # Row 5: Cost Analysis
    dashboard.add_panel(GrafanaPanel(
        title="Cost by Provider",
        panel_type="piechart",
        targets=[{
            "expr": 'sum(ragcache_llm_cost_total) by (provider)',
            "legendFormat": "{{provider}}",
        }],
        grid_pos={"x": 0, "y": 22, "w": 8, "h": 6},
    ))

    dashboard.add_panel(GrafanaPanel(
        title="Cost Over Time",
        panel_type="timeseries",
        targets=[{
            "expr": 'sum(increase(ragcache_llm_cost_total[1h])) by (provider)',
            "legendFormat": "{{provider}}",
        }],
        grid_pos={"x": 8, "y": 22, "w": 16, "h": 6},
        field_config={
            "defaults": {
                "unit": "currencyUSD",
            },
        },
    ))

    return dashboard


def export_dashboard_to_file(
    dashboard: GrafanaDashboard,
    filepath: str
) -> None:
    """
    Export dashboard to JSON file.

    Args:
        dashboard: Dashboard to export
        filepath: Output file path
    """
    with open(filepath, "w") as f:
        f.write(dashboard.to_json())

    logger.info("Dashboard exported", filepath=filepath)

