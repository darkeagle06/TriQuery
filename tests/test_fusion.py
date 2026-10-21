"""
Unit Tests for TriQuery Reciprocal Rank Fusion (Milestone 4).

Validates:
- Mathematical correctness of RRF: sum(1 / (k + rank))
- Deduplication of stable entity IDs
- Handling of documents absent from one or more rankings
- Deterministic tie-breaking behavior
- Mandatory relational filter pruning
- Empty ranking lists and invalid k parameters
"""

import unittest
from src.core.types import EngineType
from src.fusion.rrf import FusedItem, RankedItem, ReciprocalRankFusion


class TestReciprocalRankFusion(unittest.TestCase):
    """Unit tests for ReciprocalRankFusion algorithm."""

    def setUp(self):
        self.fusion = ReciprocalRankFusion(k=60)

    def test_rrf_mathematical_formulation(self):
        """
        Validates exact RRF calculation against worked manual arithmetic.
        Doc A: Rank 1 in Relational, Rank 2 in Vector (k=60)
        Expected: 1/(60+1) + 1/(60+2) = 1/61 + 1/62 = 0.01639344 + 0.01612903 = 0.03252247
        """
        item_rel = RankedItem(entity_id="project:1", rank=1, engine=EngineType.RELATIONAL, title="Project 1")
        item_vec = RankedItem(entity_id="project:1", rank=2, score=0.88, engine=EngineType.VECTOR, title="Project 1")

        rankings = {
            EngineType.RELATIONAL: [item_rel],
            EngineType.VECTOR: [item_vec],
        }

        results = self.fusion.fuse(rankings)
        self.assertEqual(len(results), 1)

        fused = results[0]
        self.assertEqual(fused.entity_id, "project:1")
        self.assertEqual(fused.final_rank, 1)

        expected_rrf = (1.0 / 61.0) + (1.0 / 62.0)
        self.assertAlmostEqual(fused.rrf_score, expected_rrf, places=5)
        self.assertEqual(set(fused.participating_engines), {EngineType.RELATIONAL, EngineType.VECTOR})
        self.assertEqual(fused.engine_ranks["relational"], 1)
        self.assertEqual(fused.engine_ranks["vector"], 2)

    def test_rrf_missing_rankings_contribute_zero(self):
        """Validates that a document absent from an engine contributes 0 from that engine."""
        doc_a = RankedItem(entity_id="project:A", rank=1, engine=EngineType.RELATIONAL)
        doc_b = RankedItem(entity_id="project:B", rank=1, engine=EngineType.VECTOR)

        rankings = {
            EngineType.RELATIONAL: [doc_a],
            EngineType.VECTOR: [doc_b],
        }

        results = self.fusion.fuse(rankings)
        self.assertEqual(len(results), 2)

        # Both have score 1/61, sorted by entity_id
        score_61 = round(1.0 / 61.0, 6)
        self.assertEqual(results[0].rrf_score, score_61)
        self.assertEqual(results[1].rrf_score, score_61)

    def test_rrf_deduplication_within_same_engine(self):
        """Validates that duplicate entity IDs in the same engine list are deduplicated to the best rank."""
        item1 = RankedItem(entity_id="project:1", rank=1, engine=EngineType.VECTOR)
        item1_duplicate = RankedItem(entity_id="project:1", rank=4, engine=EngineType.VECTOR)

        rankings = {
            EngineType.VECTOR: [item1, item1_duplicate]
        }

        results = self.fusion.fuse(rankings)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].engine_ranks["vector"], 1)
        self.assertAlmostEqual(results[0].rrf_score, 1.0 / 61.0, places=5)

    def test_rrf_deterministic_tie_breaking(self):
        """Validates that exact score ties are broken deterministically."""
        # Two docs with identical score 1/61, single engine each
        doc_z = RankedItem(entity_id="project:Z", rank=1, engine=EngineType.VECTOR)
        doc_a = RankedItem(entity_id="project:A", rank=1, engine=EngineType.VECTOR)

        results = self.fusion.fuse({EngineType.VECTOR: [doc_z, doc_a]})
        self.assertEqual(len(results), 2)
        # Lexicographical ordering breaks tie: project:A before project:Z
        self.assertEqual(results[0].entity_id, "project:A")
        self.assertEqual(results[1].entity_id, "project:Z")

    def test_rrf_mandatory_relational_filter(self):
        """Validates that mandatory_entity_ids prunes entities not satisfying SQL constraints."""
        doc_allowed = RankedItem(entity_id="project:1", rank=2, engine=EngineType.VECTOR)
        doc_pruned = RankedItem(entity_id="project:99", rank=1, engine=EngineType.VECTOR)

        rankings = {
            EngineType.VECTOR: [doc_pruned, doc_allowed]
        }

        # Only project:1 passed the relational filter
        mandatory_ids = {"project:1"}
        results = self.fusion.fuse(rankings, mandatory_entity_ids=mandatory_ids)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entity_id, "project:1")
        self.assertEqual(results[0].final_rank, 1)

    def test_rrf_empty_inputs(self):
        """Validates behavior on empty ranking dictionaries and empty lists."""
        self.assertEqual(self.fusion.fuse({}), [])
        self.assertEqual(self.fusion.fuse({EngineType.RELATIONAL: []}), [])

    def test_rrf_invalid_k_parameter(self):
        """Validates that non-positive k values raise ValueError."""
        with self.assertRaises(ValueError):
            ReciprocalRankFusion(k=0)
        with self.assertRaises(ValueError):
            ReciprocalRankFusion(k=-10)


if __name__ == "__main__":
    unittest.main()
