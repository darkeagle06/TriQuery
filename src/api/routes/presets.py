"""
Predefined Query Presets API Routes.
Exposes the 5 canonical reproducible multi-paradigm benchmark queries.
"""

from typing import List
from fastapi import APIRouter

from src.api.schemas import PresetItem, PresetsResponse
from src.core.query import PREDEFINED_QUERIES

router = APIRouter(prefix="/api", tags=["Presets"])


def _extract_paradigms(q) -> List[str]:
    paradigms = []
    if q.relational is not None:
        paradigms.append("relational")
    if q.graph is not None:
        paradigms.append("graph")
    if q.vector is not None:
        paradigms.append("vector")
    return paradigms


@router.get("/presets", response_model=PresetsResponse)
def list_presets():
    """
    Returns the 5 canonical reproducible demonstration query presets:
    1. Relational-only SQL track filter
    2. Graph-only collaborator pathfinding
    3. Vector-only natural language semantic search
    4. 2-engine hybrid (Relational + Vector with RRF fusion)
    5. 3-way multi-paradigm query (Relational + Graph + Vector with RRF fusion)
    """
    items = []
    for pid, q in PREDEFINED_QUERIES.items():
        items.append(
            PresetItem(
                preset_id=pid,
                name=q.name,
                description=q.description or q.name,
                target_paradigms=_extract_paradigms(q),
                query=q,
            )
        )

    # Sort numerically by preset_id
    items.sort(key=lambda x: int(x.preset_id) if x.preset_id.isdigit() else 99)

    return PresetsResponse(
        total_presets=len(items),
        presets=items,
    )
