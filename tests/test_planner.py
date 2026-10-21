"""
Automated Unit Tests for TriQuery Unified Query Planner (Milestone 4).
Validates:
- Engine selection for 1, 2, and 3-engine queries
- Execution plan step creation and dependency ordering
- Selective engine dispatch (only needed engines are invoked)
- Error handling on empty queries and engine failures
- Per-stage latency and record count telemetry
"""

import unittest
from unittest.mock import MagicMock

from src.core.query import (
    FusionConfig,
    GraphSubquery,
    RelationalSubquery,
    UnifiedQuery,
    VectorSubquery,
)
from src.core.types import EngineType
from src.planner.planner import UnifiedQueryPlanner


class TestUnifiedQueryPlanner(unittest.TestCase):
    """Unit tests for the UnifiedQueryPlanner class."""

    def setUp(self):
        self.mock_relational = MagicMock()
        self.mock_graph = MagicMock()
        self.mock_vector = MagicMock()
        self.planner = UnifiedQueryPlanner(
            relational_engine=self.mock_relational,
            graph_engine=self.mock_graph,
            vector_engine=self.mock_vector,
        )

    def test_plan_empty_query_raises_error(self):
        """Validates that a query with no subqueries raises ValueError."""
        empty_q = UnifiedQuery(query_id="empty-1", name="Empty")
        with self.assertRaises(ValueError) as ctx:
            self.planner.create_plan(empty_q)
        self.assertIn("at least one subquery", str(ctx.exception))

    def test_plan_creation_relational_only(self):
        """Validates that a relational-only query has 1 step, 1 engine, and no fusion step."""
        q = UnifiedQuery(
            query_id="q-rel",
            name="Relational Only",
            relational=RelationalSubquery(filters={"track": "Robotics & AI"}),
        )
        plan = self.planner.create_plan(q)

        self.assertEqual(plan.required_engines, [EngineType.RELATIONAL])
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].engine, EngineType.RELATIONAL)
        self.assertEqual(plan.steps[0].depends_on_steps, [])
        self.assertIn("Robotics & AI", plan.steps[0].description)

    def test_plan_creation_graph_only(self):
        """Validates that a graph-only query has 1 step, 1 engine, and no fusion step."""
        q = UnifiedQuery(
            query_id="q-graph",
            name="Graph Only",
            graph=GraphSubquery(operation="neighbors", source_entity="team:1", max_depth=1),
        )
        plan = self.planner.create_plan(q)

        self.assertEqual(plan.required_engines, [EngineType.GRAPH])
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].engine, EngineType.GRAPH)
        self.assertEqual(plan.steps[0].depends_on_steps, [])

    def test_plan_creation_vector_only(self):
        """Validates that a vector-only query has 1 step, 1 engine, and no fusion step."""
        q = UnifiedQuery(
            query_id="q-vec",
            name="Vector Only",
            vector=VectorSubquery(text="autonomous drone navigation", top_k=5),
        )
        plan = self.planner.create_plan(q)

        self.assertEqual(plan.required_engines, [EngineType.VECTOR])
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].engine, EngineType.VECTOR)
        self.assertEqual(plan.steps[0].depends_on_steps, [])

    def test_plan_creation_two_engines_includes_fusion_step(self):
        """Validates that a 2-engine query creates 2 search steps and 1 fusion step depending on both."""
        q = UnifiedQuery(
            query_id="q-2way",
            name="Relational + Vector",
            relational=RelationalSubquery(filters={"track": "AI"}),
            vector=VectorSubquery(text="smart grid energy optimization", top_k=3),
            fusion=FusionConfig(k=60),
        )
        plan = self.planner.create_plan(q)

        self.assertEqual(set(plan.required_engines), {EngineType.RELATIONAL, EngineType.VECTOR})
        self.assertEqual(len(plan.steps), 3)

        # Step 1: Relational
        self.assertEqual(plan.steps[0].step_id, 1)
        self.assertEqual(plan.steps[0].engine, EngineType.RELATIONAL)
        self.assertEqual(plan.steps[0].depends_on_steps, [])

        # Step 2: Vector
        self.assertEqual(plan.steps[1].step_id, 2)
        self.assertEqual(plan.steps[1].engine, EngineType.VECTOR)
        self.assertEqual(plan.steps[1].depends_on_steps, [])

        # Step 3: Fusion
        self.assertEqual(plan.steps[2].step_id, 3)
        self.assertEqual(plan.steps[2].engine, EngineType.HYBRID)
        self.assertEqual(plan.steps[2].target_operation, "rrf_fusion")
        self.assertEqual(plan.steps[2].depends_on_steps, [1, 2])

    def test_plan_creation_three_engines_dependencies(self):
        """Validates that a 3-engine query creates 3 search steps and 1 fusion step depending on [1, 2, 3]."""
        q = UnifiedQuery(
            query_id="q-3way",
            name="Three Paradigm Query",
            relational=RelationalSubquery(college_name="IIT Bombay"),
            graph=GraphSubquery(operation="shortest_path", source_entity="college:1", target_entity="project:1"),
            vector=VectorSubquery(text="quantum cryptography", top_k=4),
            fusion=FusionConfig(k=40),
        )
        plan = self.planner.create_plan(q)

        self.assertEqual(
            set(plan.required_engines),
            {EngineType.RELATIONAL, EngineType.GRAPH, EngineType.VECTOR},
        )
        self.assertEqual(len(plan.steps), 4)
        fusion_step = plan.steps[3]
        self.assertEqual(fusion_step.engine, EngineType.HYBRID)
        self.assertEqual(fusion_step.depends_on_steps, [1, 2, 3])
        self.assertEqual(fusion_step.parameters["k"], 40)

    def test_planner_selective_engine_dispatch(self):
        """Validates that running a relational-only query never invokes graph or vector engines."""
        mock_res = MagicMock()
        mock_res.success = True
        mock_res.data = [{"project_id": 1, "title": "AeroGuard", "track": "Robotics & AI"}]
        self.mock_relational.get_projects_with_details.return_value = mock_res

        q = UnifiedQuery(
            query_id="q-rel-only",
            name="Relational Only",
            relational=RelationalSubquery(filters={"track": "Robotics & AI"}),
        )
        result = self.planner.execute_plan(q)

        self.assertTrue(result.success)
        self.mock_relational.get_projects_with_details.assert_called_once_with(track="Robotics & AI")
        # Verify graph and vector engines were NEVER invoked
        self.mock_graph.bfs_traversal.assert_not_called()
        self.mock_graph.dfs_traversal.assert_not_called()
        self.mock_graph.shortest_path.assert_not_called()
        self.mock_vector.search.assert_not_called()

    def test_planner_records_stage_latencies_and_counts(self):
        """Validates that UnifiedExecutionResult records per-stage telemetry."""
        mock_res = MagicMock()
        mock_res.success = True
        mock_res.data = [
            {"project_id": 1, "title": "AeroGuard"},
            {"project_id": 2, "title": "EcoPulse"},
        ]
        self.mock_relational.get_projects_with_details.return_value = mock_res

        q = UnifiedQuery(
            query_id="q-telemetry",
            name="Telemetry Test",
            relational=RelationalSubquery(filters={"track": "AI"}),
        )
        result = self.planner.execute_plan(q)

        self.assertTrue(result.success)
        self.assertIn("relational", result.stage_latencies_ms)
        self.assertGreaterEqual(result.stage_latencies_ms["relational"], 0.0)
        self.assertEqual(result.stage_record_counts.get("relational"), 2)
        self.assertGreaterEqual(result.total_latency_ms, 0.0)
        self.assertEqual(len(result.fused_results), 2)

    def test_planner_handles_engine_exception_safely(self):
        """Validates that engine errors return a failed result without raising an unhandled exception."""
        self.mock_relational.get_projects_with_details.side_effect = RuntimeError("Database connection lost")

        q = UnifiedQuery(
            query_id="q-error",
            name="Error Test",
            relational=RelationalSubquery(filters={"track": "AI"}),
        )
        result = self.planner.execute_plan(q)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn("Database connection lost", result.error)


if __name__ == "__main__":
    unittest.main()
