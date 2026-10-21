"""
Vector Engine API Routes.
Performs top-K nearest-neighbor similarity search over hackathon project descriptions
using the verified in-memory Scikit-Learn TF-IDF vector engine.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_vector_engine
from src.api.schemas import (
    VectorSearchItem,
    VectorSearchRequest,
    VectorSearchResponse,
)
from src.engines.vector.engine import VectorEngine

logger = logging.getLogger("triquery.api.vector")

router = APIRouter(prefix="/api/vector", tags=["Vector Engine"])


@router.post("/search", response_model=VectorSearchResponse)
def search_vectors(
    req: VectorSearchRequest,
    vec_engine: VectorEngine = Depends(get_vector_engine),
):
    """
    Executes top-K cosine similarity search against L2-normalized project embeddings.
    Applies configurable top-K candidate bounds (1-50) and minimum score thresholds.
    """
    clean_q = req.query.strip()
    if not clean_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty or whitespace only."
        )

    if not vec_engine.is_healthy() or vec_engine.document_count == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector engine index is not initialized or contains zero documents."
        )

    try:
        result = vec_engine.search(
            query_text=clean_q,
            top_k=req.top_k,
            min_score=req.min_score,
        )
    except Exception as exc:
        logger.error(f"Vector search error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute vector similarity search."
        )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error or "Vector search returned an error."
        )

    items = []
    for r in result.data:
        items.append(
            VectorSearchItem(
                rank=r.get("rank", 0),
                score=round(float(r.get("score", 0.0)), 6),
                entity_id=r.get("entity_id", ""),
                project_id=r.get("project_id"),
                title=r.get("title", ""),
                track=r.get("track"),
                short_summary=r.get("short_summary"),
                tech_stack=r.get("tech_stack"),
            )
        )

    meta = result.metadata
    provider_str = getattr(vec_engine.provider, "description", "TF-IDF Vectorizer")

    return VectorSearchResponse(
        success=True,
        count=len(items),
        query=clean_q,
        execution_time_ms=meta.execution_time_ms if meta else 0.0,
        provider=provider_str,
        results=items,
        notes=meta.notes if meta else [],
    )
