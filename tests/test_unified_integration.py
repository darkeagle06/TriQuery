"""
Integration Tests for TriQuery Milestone 4: Unified Planner and Result Fusion.

Validates end-to-end execution with real engine instances:
- RelationalEngine (SQLite in-memory with normalized seed schema)
- GraphEngine (NetworkX graph built from relational tables)
- VectorEngine (Deterministic provider with VectorIndex)
- UnifiedQueryPlanner and ReciprocalRankFusion
- QueryExplainer formatting and viva telemetry

Verifies:
1. Relational-only execution (Preset 1)
2. Graph-only execution (Preset 2)
3. Vector-only execution (Preset 3)
4. Multi-engine hybrid execution (Preset 4)
5. 3-way multi-paradigm execution (Preset 5)
6. Non-matching query graceful handling
"""

import unittest

from src.config import DatabaseConfig
from src.core.query import (
    PREDEFINED_QUERIES,
    FusionConfig,
    GraphSubquery,
    RelationalSubquery,
    UnifiedQuery,
    VectorSubquery,
)
from src.core.types import EngineType
from src.engines.graph.engine import GraphEngine
from src.engines.relational.connection import DatabaseConnectionManager
from src.engines.relational.engine import RelationalEngine
from src.engines.vector.engine import VectorEngine
from src.engines.vector.providers import DeterministicTestProvider
from src.explain.explainer import QueryExplainer
from src.planner.planner import UnifiedQueryPlanner


class TestUnifiedIntegration(unittest.TestCase):
    """End-to-end integration tests combining all three real engines."""

    @classmethod
    def setUpClass(cls):
        from tests.test_relational_engine import TestRelationalEngine
        # 1. Initialize real isolated relational engine with seed data
        cls.db_config = DatabaseConfig(sqlite_fallback=True, sqlite_path=":memory:")
        cls.conn_mgr = DatabaseConnectionManager(cls.db_config)
        cls.rel_engine = RelationalEngine(cls.conn_mgr)

        TestRelationalEngine._init_test_schema.__func__(cls)
        TestRelationalEngine._load_test_seed_data.__func__(cls)

        # 2. Initialize real GraphEngine from relational data
        cls.graph_engine = GraphEngine(relational_engine=cls.rel_engine, auto_build=True)

        # 3. Initialize real VectorEngine with deterministic provider
        cls.vec_provider = DeterministicTestProvider(dimension=64)
        cls.vec_engine = VectorEngine(
            relational_engine=cls.rel_engine,
            provider=cls.vec_provider,
            auto_build=True,
        )

        # 4. Construct UnifiedQueryPlanner with real engines
        cls.planner = UnifiedQueryPlanner(
            relational_engine=cls.rel_engine,
            graph_engine=cls.graph_engine,
            vector_engine=cls.vec_engine,
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn_mgr") and cls.conn_mgr:
            cls.conn_mgr.close()

    def test_preset_1_relational_only_real_execution(self):
        """Validates Preset 1: Relational SQL filter on track 'Robotics & AI'."""
        q = PREDEFINED_QUERIES["1"]
        result = self.planner.execute_plan(q)

        self.assertTrue(result.success)
        self.assertEqual(result.plan.required_engines, [EngineType.RELATIONAL])
        self.assertGreater(len(result.fused_results), 0)

        # Verify AeroVision is found and matches track
        matched_titles = [r.title for r in result.fused_results]
        self.assertIn("AeroVision Autonomous Drone Pathfinder", matched_titles)

        # Stage telemetry
        self.assertIn("relational", result.stage_latencies_ms)
        self.assertNotIn("graph", result.stage_latencies_ms)
        self.assertNotIn("vector", result.stage_latencies_ms)
        self.assertGreater(result.total_latency_ms, 0.0)

    def test_preset_2_graph_only_real_execution(self):
        """Validates Preset 2: Graph traversal of team nodes and connected entities."""
        q = PREDEFINED_QUERIES["2"]
        result = self.planner.execute_plan(q)

        self.assertTrue(result.success)
        self.assertEqual(result.plan.required_engines, [EngineType.GRAPH])
        self.assertGreater(len(result.fused_results), 0)

        # Telemetry should only record graph stage
        self.assertIn("graph", result.stage_latencies_ms)
        self.assertNotIn("relational", result.stage_latencies_ms)
        self.assertNotIn("vector", result.stage_latencies_ms)

    def test_preset_3_vector_only_real_execution(self):
        """Validates Preset 3: Vector similarity search across project descriptions."""
        q = PREDEFINED_QUERIES["3"]
        result = self.planner.execute_plan(q)

        self.assertTrue(result.success)
        self.assertEqual(result.plan.required_engines, [EngineType.VECTOR])
        self.assertLessEqual(len(result.fused_results), 5)

        # Check that top result has valid entity ID and title
        top_match = result.fused_results[0]
        self.assertTrue(top_match.entity_id.startswith("project:"))
        self.assertTrue(len(top_match.title) > 0)
        self.assertIn("vector", top_match.engine_ranks)
        self.assertEqual(top_match.engine_ranks["vector"], 1)

    def test_preset_4_relational_and_vector_hybrid_fusion(self):
        """Validates Preset 4: 2-engine hybrid query with RRF combination and mandatory filtering."""
        q = PREDEFINED_QUERIES["4"]
        result = self.planner.execute_plan(q)

        self.assertTrue(result.success)
        self.assertEqual(
            set(result.plan.required_engines),
            {EngineType.RELATIONAL, EngineType.VECTOR},
        )
        self.assertIn("fusion", result.stage_latencies_ms)

        # Verify that all fused results satisfy the relational filter
        for item in result.fused_results:
            self.assertEqual(item.metadata.get("track"), "Healthcare & AI")
            self.assertIn(EngineType.RELATIONAL, item.participating_engines)

        # Verify RRF score ordering
        if len(result.fused_results) > 1:
            for i in range(len(result.fused_results) - 1):
                self.assertGreaterEqual(
                    result.fused_results[i].rrf_score,
                    result.fused_results[i + 1].rrf_score,
                )

    def test_preset_5_three_way_unified_real_execution(self):
        """Validates Preset 5: Full 3-paradigm query executing relational, graph, and vector."""
        q = PREDEFINED_QUERIES["5"]
        result = self.planner.execute_plan(q)

        self.assertTrue(result.success)
        self.assertEqual(
            set(result.plan.required_engines),
            {EngineType.RELATIONAL, EngineType.GRAPH, EngineType.VECTOR},
        )
        self.assertIn("relational", result.stage_latencies_ms)
        self.assertIn("graph", result.stage_latencies_ms)
        self.assertIn("vector", result.stage_latencies_ms)
        self.assertIn("fusion", result.stage_latencies_ms)

        # Check explainability integration
        explanation = QueryExplainer.build_explanation(result, q)
        self.assertEqual(len(explanation.engines_used), 3)
        self.assertIn("AeroVision Autonomous Drone Pathfinder", [r.title for r in explanation.records])

    def test_empty_results_graceful_handling(self):
        """Validates that a query matching no relational records produces 0 fused results without crashing."""
        no_match_q = UnifiedQuery(
            query_id="q-no-match",
            name="No Match Query",
            relational=RelationalSubquery(filters={"track": "NonExistentTrack12345"}),
            vector=VectorSubquery(text="irrelevant search term", top_k=2),
            fusion=FusionConfig(k=60, mandatory_relational_filter=True),
        )
        result = self.planner.execute_plan(no_match_q)

        self.assertTrue(result.success)
        self.assertEqual(len(result.fused_results), 0)
        self.assertEqual(result.stage_record_counts.get("relational"), 0)


if __name__ == "__main__":
    unittest.main()
