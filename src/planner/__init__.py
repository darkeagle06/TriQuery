"""
TriQuery Query Planner Package (Milestone 4).
Generates multi-engine execution plans, enforces dependency ordering, and dispatches subqueries.
"""

from src.planner.planner import UnifiedExecutionResult, UnifiedQueryPlanner

__all__ = [
    "UnifiedQueryPlanner",
    "UnifiedExecutionResult",
]
