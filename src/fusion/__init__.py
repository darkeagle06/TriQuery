"""
TriQuery Result Fusion Package (Milestone 4).
Provides Reciprocal Rank Fusion (RRF) for combining multi-engine search rankings.
"""

from src.fusion.rrf import FusedItem, RankedItem, ReciprocalRankFusion

__all__ = [
    "ReciprocalRankFusion",
    "RankedItem",
    "FusedItem",
]
