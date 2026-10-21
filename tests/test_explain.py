"""
Automated Unit Tests for TriQuery Query Explainability (Milestone 4).
Validates:
- Construction of typed QueryExplanation models
- Engine selection rationale and plan breakdown
- Measured stage latencies vs. estimates
- Reciprocal rank fusion evidence and individual engine rank contributions
- Rich terminal UI rendering without exceptions
"""

import io
import unittest
from rich.console import Console

from src.core.query import FusionConfig, RelationalSubquery, UnifiedQuery, VectorSubquery
from src.core.types import EngineType, QueryPlan, QueryPlanStep
from src.explain.explainer import QueryExplainer
from src.fusion.rrf import FusedItem
from src.planner.planner import UnifiedExecutionResult


class TestQueryExplainer(unittest.TestCase):
    """Unit tests for QueryExplainer model building and rendering."""

    def setUp(self):
        self.query = UnifiedQuery(
            query_id="q-test-explain",
            name="Explain Verification Query",
            description="Test query for explainability layer",
            relational=RelationalSubquery(filters={"track": "Robotics & AI"}),
            vector=VectorSubquery(text="drone navigation", top_k=2),
            fusion=FusionConfig(k=60, mandatory_relational_filter=True),
        )

        self.plan = QueryPlan(
            query_id="q-test-explain",
            natural_query="Explain Verification Query",
            required_engines=[EngineType.RELATIONAL, EngineType.VECTOR],
            steps=[
                QueryPlanStep(
                    step_id=1,
                    engine=EngineType.RELATIONAL,
                    description="Filter projects by track",
                    target_operation="relational_filter",
                    parameters={"track": "Robotics & AI"},
                    depends_on_steps=[],
                ),
                QueryPlanStep(
                    step_id=2,
                    engine=EngineType.VECTOR,
                    description="Perform vector search",
                    target_operation="vector_search",
                    parameters={"text": "drone navigation", "top_k": 2},
                    depends_on_steps=[],
                ),
                QueryPlanStep(
                    step_id=3,
                    engine=EngineType.HYBRID,
                    description="Combine rankings via RRF (k=60)",
                    target_operation="rrf_fusion",
                    parameters={"k": 60},
                    depends_on_steps=[1, 2],
                ),
            ],
            estimated_cost_note="Plan targets 2 engine(s).",
        )

        self.fused_results = [
            FusedItem(
                entity_id="project:1",
                title="AeroGuard",
                rrf_score=0.032786,
                final_rank=1,
                participating_engines=[EngineType.RELATIONAL, EngineType.VECTOR],
                engine_ranks={"relational": 1, "vector": 1},
                engine_scores={"relational": 1.0, "vector": 0.88},
                metadata={"track": "Robotics & AI", "college_name": "IIT Bombay"},
            ),
            FusedItem(
                entity_id="project:6",
                title="AgroDrone",
                rrf_score=0.016129,
                final_rank=2,
                participating_engines=[EngineType.VECTOR],
                engine_ranks={"vector": 2},
                engine_scores={"vector": 0.72},
                metadata={"track": "Agritech"},
            ),
        ]

        self.result = UnifiedExecutionResult(
            query_id=self.query.query_id,
            query_name=self.query.name,
            success=True,
            plan=self.plan,
            fused_results=self.fused_results,
            raw_engine_results={"relational": {}, "vector": {}},
            stage_latencies_ms={"relational": 1.25, "vector": 3.40, "fusion": 0.15},
            stage_record_counts={"relational": 1, "vector": 2, "fusion": 2},
            total_latency_ms=4.80,
        )

    def test_build_explanation_model(self):
        """Validates that build_explanation populates all required fields in QueryExplanation."""
        explanation = QueryExplainer.build_explanation(self.result, self.query)

        self.assertEqual(explanation.query_id, "q-test-explain")
        self.assertEqual(explanation.query_text, "Test query for explainability layer")
        self.assertEqual(explanation.engines_used, [EngineType.RELATIONAL, EngineType.VECTOR])
        self.assertEqual(explanation.total_execution_time_ms, 4.80)
        self.assertEqual(explanation.engine_timings["vector"], 3.40)
        self.assertEqual(explanation.intermediate_counts["relational"], 1)

        # Plan explanation should detail all 3 steps with dependencies
        self.assertIn("Step 1 (relational): Filter projects by track [independent]", explanation.plan_explanation)
        self.assertIn("Step 3 (hybrid): Combine rankings via RRF (k=60) [depends on steps [1, 2]]", explanation.plan_explanation)

        # Ranking explanation should detail RRF formula and k parameter
        self.assertIn("Reciprocal Rank Fusion", explanation.ranking_explanation)
        self.assertIn("k=60", explanation.ranking_explanation)

        # Records should map from fused results
        self.assertEqual(len(explanation.records), 2)
        rec1 = explanation.records[0]
        self.assertEqual(rec1.entity_id, "project:1")
        self.assertEqual(rec1.title, "AeroGuard")
        self.assertTrue(rec1.relational_matched)
        self.assertFalse(rec1.graph_matched)
        self.assertEqual(rec1.vector_score, 0.88)
        self.assertAlmostEqual(rec1.final_rank_score, 0.032786, places=5)
        self.assertIn("Ranked #1 via RRF score", rec1.reason_for_inclusion)

    def test_single_engine_explanation_text(self):
        """Validates ranking explanation for a single-engine query."""
        single_query = UnifiedQuery(
            query_id="q-single",
            name="Single Engine",
            relational=RelationalSubquery(filters={"track": "AI"}),
        )
        single_plan = QueryPlan(
            query_id="q-single",
            natural_query="Single Engine",
            required_engines=[EngineType.RELATIONAL],
            steps=[
                QueryPlanStep(
                    step_id=1,
                    engine=EngineType.RELATIONAL,
                    description="Run SQL",
                    target_operation="sql_query",
                    parameters={},
                    depends_on_steps=[],
                )
            ],
        )
        single_result = UnifiedExecutionResult(
            query_id="q-single",
            query_name="Single Engine",
            success=True,
            plan=single_plan,
            fused_results=[],
            total_latency_ms=1.5,
        )

        explanation = QueryExplainer.build_explanation(single_result, single_query)
        self.assertIn("Single Engine Mode", explanation.ranking_explanation)
        self.assertIn("Ordinal ranking preserved directly", explanation.ranking_explanation)

    def test_render_rich_explanation_smoke(self):
        """Validates that render_rich_explanation prints all tables without exceptions."""
        buffer = io.StringIO()
        console = Console(file=buffer, color_system=None, width=120)

        # Execute rendering
        QueryExplainer.render_rich_explanation(self.result, self.query, console)
        output = buffer.getvalue()

        # Check section headings and content
        self.assertIn("TriQuery Unified Execution Plan & Explainability", output)
        self.assertIn("1. Engine Selection & Dispatch Rationale", output)
        self.assertIn("Relational (MySQL/SQLite)", output)
        self.assertIn("Vector (Similarity Search)", output)
        self.assertIn("2. Ordered Execution Plan Steps", output)
        self.assertIn("3. Measured Stage Latency & Intermediate Record Counts", output)
        self.assertIn("4. Reciprocal Rank Fusion (RRF) Evidence", output)
        self.assertIn("AeroGuard", output)
        self.assertIn("DBMS Viva Defense Note", output)


if __name__ == "__main__":
    unittest.main()
