"""
TriQuery API Package.
Exposes FastAPI REST endpoints over Relational, Graph, Vector, and Unified Planner engines.
"""

from src.api.app import app, create_app

__all__ = ["app", "create_app"]
