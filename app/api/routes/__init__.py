"""
API Routes module.

Contains all API endpoint routers.
"""

from app.api.routes import docs, health, metrics, query

__all__ = ["health", "query", "metrics", "docs"]

