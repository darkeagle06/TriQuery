"""
Unified Query Execution & Explainability API Routes.
Dispatches queries through UnifiedQueryPlanner and coordinates RRF result fusion.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_planner
from src.core.query import UnifiedQuery
from src.core.types import QueryExplanation
from src.explain.explainer import QueryExplainer
from src.planner.planner import UnifiedExecutionResult, UnifiedQueryPlanner

logger = logging.getLogger("triquery.api.query")

router = APIRouter(prefix="/api/query", tags=["Unified Query Execution"])


@router.post("/unified", response_model=UnifiedExecutionResult)
def execute_unified_query(
    query: UnifiedQuery,
    planner: UnifiedQueryPlanner = Depends(get_planner),
):
    """
    Validates and executes a multi-paradigm UnifiedQuery across Relational, Graph, and Vector engines.
    Returns fused entity results (RRF), per-stage latency telemetry, and record counts.
    """
    # 1. Validation: At least one engine must be selected
    if not any([query.relational, query.graph, query.vector]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UnifiedQuery must specify at least one subquery: 'relational', 'graph', or 'vector'."
        )

    # 2. Execution
    try:
        result = planner.execute_plan(query)
    except Exception as exc:
        logger.error(f"Plan execution failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute query plan across backend engines."
        )

    if not result.success and result.error:
        # Check if error is due to user query error vs system failure
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query execution error: {result.error}"
        )

    return result


@router.post("/explain", response_model=Dict[str, Any])
def explain_unified_query(
    query: UnifiedQuery,
    planner: UnifiedQueryPlanner = Depends(get_planner),
):
    """
    Executes a UnifiedQuery and generates a comprehensive explainability report detailing:
    - Selected engines and selection triggers
    - Ordered plan steps with explicit dependencies
    - Per-stage latency metrics and record counts
    - Reciprocal Rank Fusion parameters and ranking evidence
    - Structured final records with inclusion reasons
    """
    if not any([query.relational, query.graph, query.vector]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UnifiedQuery must specify at least one subquery: 'relational', 'graph', or 'vector'."
        )

    try:
        result = planner.execute_plan(query)
        if not result.success and result.error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query execution error: {result.error}"
            )

        explanation = QueryExplainer.build_explanation(result, query)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Explain generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate query explanation."
        )

    # Combine typed explanation with the full execution plan for deep UI visualization
    return {
        "explanation": explanation.model_dump(),
        "plan": result.plan.model_dump(),
        "stage_latencies_ms": result.stage_latencies_ms,
        "stage_record_counts": result.stage_record_counts,
        "total_latency_ms": result.total_latency_ms,
        "fused_results": [item.model_dump() for item in result.fused_results],
    }
