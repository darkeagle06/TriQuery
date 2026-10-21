"""
Reciprocal Rank Fusion (RRF) implementation for TriQuery (Milestone 4).
Combines ranked result lists from Relational, Graph, and Vector engines
into an explainable, consensus-ranked unified result set.
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from src.core.types import EngineType


class RankedItem(BaseModel):
    """An individual entity ranked by an engine."""
    entity_id: str
    rank: int = Field(ge=1, description="1-indexed rank position")
    score: Optional[float] = Field(default=None, description="Raw engine score if applicable")
    engine: EngineType
    title: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FusedItem(BaseModel):
    """Unified record resulting from multi-engine RRF fusion."""
    entity_id: str
    title: str = ""
    rrf_score: float = Field(description="Combined reciprocal rank fusion score")
    final_rank: int = Field(ge=1, description="Final 1-indexed rank after fusion")
    participating_engines: List[EngineType] = Field(default_factory=list)
    engine_ranks: Dict[str, int] = Field(default_factory=dict)
    engine_scores: Dict[str, Optional[float]] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_filtered_out: bool = False
    filter_reason: Optional[str] = None


class ReciprocalRankFusion:
    """
    Computes Reciprocal Rank Fusion over multiple engine rankings.
    Standard formulation:
        RRF(d) = sum_{m in M} (1 / (k + rank_m(d)))
    where k is a positive constant (default: 60) and ranks start at 1.
    """

    def __init__(self, k: int = 60):
        if k <= 0:
            raise ValueError(f"RRF constant k must be positive (> 0), got {k}")
        self.k = k

    def fuse(
        self,
        rankings: Dict[EngineType, List[RankedItem]],
        mandatory_entity_ids: Optional[Set[str]] = None
    ) -> List[FusedItem]:
        """
        Fuses ranked lists from participating engines.

        Args:
            rankings: Mapping of EngineType to an ordered list of RankedItem.
            mandatory_entity_ids: If provided, entities absent from this set are
                                  filtered out (e.g. relational hard constraints).

        Returns:
            Sorted list of FusedItem ranked by descending RRF score.
        """
        if not rankings:
            return []

        # Deduplicate and aggregate across rankings
        aggregated: Dict[str, Dict[str, Any]] = {}

        for engine, items in rankings.items():
            seen_in_engine: Set[str] = set()

            for item in items:
                eid = item.entity_id
                # Safeguard against duplicate entity IDs within the same engine ranking:
                # Keep the best (lowest) rank
                if eid in seen_in_engine:
                    continue
                seen_in_engine.add(eid)

                if eid not in aggregated:
                    aggregated[eid] = {
                        "entity_id": eid,
                        "title": item.title,
                        "rrf_score": 0.0,
                        "participating_engines": [],
                        "engine_ranks": {},
                        "engine_scores": {},
                        "metadata": item.metadata.copy(),
                    }

                # Update title and metadata if earlier was empty
                if not aggregated[eid]["title"] and item.title:
                    aggregated[eid]["title"] = item.title
                aggregated[eid]["metadata"].update(item.metadata)

                # Compute RRF contribution: 1 / (k + rank)
                contribution = 1.0 / (self.k + item.rank)
                aggregated[eid]["rrf_score"] += contribution
                aggregated[eid]["participating_engines"].append(engine)
                aggregated[eid]["engine_ranks"][engine.value] = item.rank
                aggregated[eid]["engine_scores"][engine.value] = item.score

        # Apply mandatory relational filtering if specified
        valid_items: List[Dict[str, Any]] = []
        for eid, data in aggregated.items():
            if mandatory_entity_ids is not None and eid not in mandatory_entity_ids:
                # Excluded by hard relational predicate
                continue
            valid_items.append(data)

        # Sort items deterministically:
        # Primary: rrf_score (descending)
        # Secondary: number of participating engines (descending)
        # Tertiary: entity_id (ascending)
        valid_items.sort(
            key=lambda x: (-x["rrf_score"], -len(x["participating_engines"]), x["entity_id"])
        )

        # Build output FusedItem models with final sequential rank (1-indexed)
        results: List[FusedItem] = []
        for rank_idx, item in enumerate(valid_items, start=1):
            results.append(
                FusedItem(
                    entity_id=item["entity_id"],
                    title=item["title"],
                    rrf_score=round(item["rrf_score"], 6),
                    final_rank=rank_idx,
                    participating_engines=item["participating_engines"],
                    engine_ranks=item["engine_ranks"],
                    engine_scores=item["engine_scores"],
                    metadata=item["metadata"],
                )
            )

        return results

    @staticmethod
    def get_algorithm_explanation() -> Dict[str, Any]:
        """Provides theoretical justification and complexity for viva defense."""
        return {
            "name": "Reciprocal Rank Fusion (RRF)",
            "formula": "RRF(d) = sum_{m in M} (1 / (k + rank_m(d)))",
            "default_k": 60,
            "why_used": (
                "Relational queries produce unranked sets, Graph queries produce integer hop distances, "
                "and Vector search produces cosine similarities. Normalizing and summing these disparate scales "
                "is arbitrary and mathematically uncalibrated. RRF relies exclusively on ordinal rank positions, "
                "making it robust across incommensurable retrieval paradigms."
            ),
            "limitations": (
                "RRF ignores score magnitude (the difference between rank 1 and 2 is treated the same "
                "regardless of whether the score gap was 0.01 or 0.50). Additionally, unweighted RRF assumes "
                "all participating rankings carry equal reliability."
            ),
            "time_complexity": "O(M * N + N log N) where M is number of engines and N is candidate entity count",
            "space_complexity": "O(N) auxiliary hash table for entity deduplication"
        }
