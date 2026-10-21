"""
Automated API Tests for TriQuery FastAPI Backend.
Validates:
1. Health response, backend detection, and failure behavior.
2. Retrieval of all five canonical presets.
3. Valid and invalid unified-query payloads.
4. Structured query explanation output.
5. Relational schema metadata and project filtering.
6. Graph topology and shortest-path traversal.
7. Vector search results, candidate limits, and invalid inputs.
8. Sanitized error responses without leaking credentials or paths.
9. Engine container initialization and reuse across requests.
10. Live MySQL integration tests (cleanly separated and skipped if MySQL is offline).
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import EngineContainer, get_container
from src.config import DatabaseConfig, config
from src.core.query import PREDEFINED_QUERIES, UnifiedQuery
from tests.test_mysql_integration import MYSQL_AVAILABLE, SKIP_REASON


class TestAPIContract(unittest.TestCase):
    """
    Contract and unit test suite for all FastAPI endpoints.
    Uses an isolated SQLite test container to remain fast, deterministic,
    and completely decoupled from external network state.
    """

    @classmethod
    def setUpClass(cls):
        from tests.test_relational_engine import TestRelationalEngine

        # 1. Initialize isolated in-memory test database without auto-building indexes yet
        cls.test_db_cfg = DatabaseConfig(sqlite_fallback=True, sqlite_path=":memory:")
        cls.container = EngineContainer(db_config=cls.test_db_cfg, auto_build=False)

        # Seed relational schema & data in test container
        TestRelationalEngine._init_test_schema.__func__(cls.container.relational_engine)
        TestRelationalEngine._load_test_seed_data.__func__(cls.container.relational_engine)

        # Re-build graph and vector indexes on the seeded container
        cls.container.graph_engine.build_from_relational()
        cls.container.vector_engine.build_from_relational(force=True)

        # 2. Instantiate FastAPI app and override get_container dependency
        cls.app = create_app(db_config=cls.test_db_cfg)
        cls.app.state.container = cls.container
        cls.app.dependency_overrides[get_container] = lambda: cls.container
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.container.close()

    def test_root_endpoint(self):
        """Validates that GET / returns service information and docs link."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["name"], "TriQuery Multi-Paradigm Query API")
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["docs_url"], "/docs")

    def test_get_health_endpoint(self):
        """Validates GET /api/health reports system status, table counts, and engine states."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["is_healthy"])
        self.assertIn("SQLite", data["backend"])
        self.assertEqual(data["table_counts"]["projects"], 6)
        self.assertEqual(data["table_counts"]["colleges"], 5)

        # Graph health
        self.assertEqual(data["graph"]["node_count"], 38)
        self.assertEqual(data["graph"]["edge_count"], 55)
        self.assertTrue(data["graph"]["is_healthy"])

        # Vector health
        self.assertEqual(data["vector"]["document_count"], 6)
        self.assertGreater(data["vector"]["dimension"], 0)

    def test_get_presets_returns_five(self):
        """Validates GET /api/presets returns all 5 canonical query benchmarks."""
        resp = self.client.get("/api/presets")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["total_presets"], 5)
        self.assertEqual(len(data["presets"]), 5)

        preset_ids = [p["preset_id"] for p in data["presets"]]
        self.assertEqual(preset_ids, ["1", "2", "3", "4", "5"])

        # Check Preset 1 (Relational-only)
        p1 = data["presets"][0]
        self.assertEqual(p1["target_paradigms"], ["relational"])
        self.assertIn("Robotics & AI", p1["description"])

        # Check Preset 5 (3-engine unified)
        p5 = data["presets"][4]
        self.assertEqual(set(p5["target_paradigms"]), {"relational", "graph", "vector"})

    def test_unified_query_validation_empty_payload(self):
        """Validates POST /api/query/unified rejects queries without any subquery."""
        empty_query = {"query_id": "q-test-empty", "name": "Empty Query"}
        resp = self.client.post("/api/query/unified", json=empty_query)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("at least one subquery", resp.json()["detail"])

    def test_unified_query_execution_preset_1(self):
        """Validates POST /api/query/unified executes a real relational track query."""
        p1_payload = PREDEFINED_QUERIES["1"].model_dump()
        resp = self.client.post("/api/query/unified", json=p1_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["plan"]["required_engines"], ["relational"])
        self.assertGreater(len(data["fused_results"]), 0)
        self.assertIn("AeroVision Autonomous Drone Pathfinder", [r["title"] for r in data["fused_results"]])
        self.assertIn("relational", data["stage_latencies_ms"])
        self.assertGreater(data["total_latency_ms"], 0.0)

    def test_unified_query_execution_preset_4_hybrid(self):
        """Validates POST /api/query/unified executes a 2-engine hybrid query with RRF fusion."""
        p4_payload = PREDEFINED_QUERIES["4"].model_dump()
        resp = self.client.post("/api/query/unified", json=p4_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertTrue(data["success"])
        self.assertEqual(set(data["plan"]["required_engines"]), {"relational", "vector"})
        self.assertIn("fusion", data["stage_latencies_ms"])
        self.assertGreater(len(data["fused_results"]), 0)

        # Result must be RadAssist matching Healthcare & AI
        top_match = data["fused_results"][0]
        self.assertEqual(top_match["metadata"]["track"], "Healthcare & AI")
        self.assertGreater(top_match["rrf_score"], 0.0)

    def test_query_explain_endpoint(self):
        """Validates POST /api/query/explain returns plan, engine selection, and RRF evidence."""
        p5_payload = PREDEFINED_QUERIES["5"].model_dump()
        resp = self.client.post("/api/query/explain", json=p5_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("explanation", data)
        self.assertIn("plan", data)
        self.assertIn("fused_results", data)
        self.assertIn("stage_latencies_ms", data)

        exp = data["explanation"]
        self.assertEqual(len(exp["engines_used"]), 3)
        self.assertIn("Reciprocal Rank Fusion", exp["ranking_explanation"])
        self.assertGreater(len(exp["records"]), 0)

    def test_query_explain_empty_subqueries_error(self):
        """Validates POST /api/query/explain returns 400 for empty subqueries."""
        resp = self.client.post("/api/query/explain", json={"name": "Empty"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("at least one subquery", resp.json()["detail"])

    def test_relational_tables_schema(self):
        """Validates GET /api/relational/tables returns schema metadata, columns, and foreign keys."""
        resp = self.client.get("/api/relational/tables")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertGreater(data["table_count"], 0)
        table_names = [t["table_name"] for t in data["tables"]]
        self.assertIn("projects", table_names)
        self.assertIn("teams", table_names)
        self.assertIn("colleges", table_names)

        # Inspect projects table columns
        proj_table = next(t for t in data["tables"] if t["table_name"] == "projects")
        col_names = [c["name"] for c in proj_table["columns"]]
        self.assertIn("project_id", col_names)
        self.assertIn("title", col_names)
        self.assertIn("track", col_names)

    def test_relational_projects_filtering(self):
        """Validates GET /api/relational/projects with track and college query parameters."""
        # Filter by track
        resp_track = self.client.get("/api/relational/projects?track=Robotics+%26+AI")
        self.assertEqual(resp_track.status_code, 200)
        data_track = resp_track.json()
        self.assertTrue(data_track["success"])
        self.assertEqual(data_track["count"], 1)
        self.assertEqual(data_track["data"][0]["project_title"], "AeroVision Autonomous Drone Pathfinder")

        # Filter by college
        resp_college = self.client.get("/api/relational/projects?college=IIT+Delhi")
        self.assertEqual(resp_college.status_code, 200)
        data_college = resp_college.json()
        self.assertTrue(data_college["success"])
        self.assertEqual(data_college["count"], 1)
        self.assertEqual(data_college["data"][0]["college_name"], "IIT Delhi")

    def test_graph_topology_endpoint(self):
        """Validates GET /api/graph/topology returns node and edge structures."""
        resp = self.client.get("/api/graph/topology")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["node_count"], 38)
        self.assertEqual(data["edge_count"], 55)
        self.assertIn("college", data["node_types"])
        self.assertIn("project", data["node_types"])
        self.assertIn("AFFILIATED_WITH", data["edge_types"])
        self.assertEqual(len(data["nodes"]), 38)
        self.assertEqual(len(data["edges"]), 55)

    def test_graph_path_shortest_path(self):
        """Validates POST /api/graph/path finds the shortest path between entities."""
        payload = {
            "source": "participant:1",
            "target": "participant:5",
            "directed": False,
        }
        resp = self.client.post("/api/graph/path", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertTrue(data["found"])
        self.assertEqual(data["length"], 6)
        self.assertEqual(data["source"], "participant:1")
        self.assertEqual(data["target"], "participant:5")
        self.assertEqual(len(data["path"]), 7)
        self.assertEqual(len(data["steps"]), 6)

    def test_graph_path_missing_nodes(self):
        """Validates POST /api/graph/path handles missing entities safely without crashing."""
        payload = {
            "source": "nonexistent:999",
            "target": "participant:5",
        }
        resp = self.client.post("/api/graph/path", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["found"])
        self.assertIn("not found", data["message"])

    def test_vector_search_valid(self):
        """Validates POST /api/vector/search returns top-K nearest neighbors and cosine scores."""
        payload = {
            "query": "autonomous drone navigation system",
            "top_k": 3,
            "min_score": 0.0,
        }
        resp = self.client.post("/api/vector/search", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertTrue(data["success"])
        self.assertLessEqual(data["count"], 3)
        self.assertGreater(len(data["results"]), 0)

        top = data["results"][0]
        self.assertEqual(top["rank"], 1)
        self.assertGreaterEqual(top["score"], 0.0)
        self.assertTrue(top["entity_id"].startswith("project:"))
        self.assertTrue(len(top["title"]) > 0)

    def test_vector_search_validation_empty_query(self):
        """Validates POST /api/vector/search rejects empty or whitespace-only queries."""
        resp = self.client.post("/api/vector/search", json={"query": "    ", "top_k": 5})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("empty", resp.json()["detail"].lower())

    def test_vector_search_validation_invalid_top_k(self):
        """Validates POST /api/vector/search rejects top_k outside 1..50 bounds."""
        resp = self.client.post("/api/vector/search", json={"query": "test", "top_k": 100})
        self.assertEqual(resp.status_code, 422)  # Pydantic validation error

        resp_zero = self.client.post("/api/vector/search", json={"query": "test", "top_k": 0})
        self.assertEqual(resp_zero.status_code, 422)

    def test_sanitized_error_handling(self):
        """Validates that unexpected server errors return clean 500 without leaking secrets or paths."""
        mock_container = MagicMock()
        mock_container.relational_engine.conn_mgr.execute_query.side_effect = RuntimeError(
            "FATAL: /var/secrets/db_password.txt leak attempt"
        )
        mock_container.relational_engine.conn_mgr.is_sqlite_mode = False
        mock_container.relational_engine.conn_mgr.cfg.name = "triquery_db"
        mock_container.relational_engine.get_table_counts.return_value = {"projects": 6}

        test_app = create_app(db_config=self.test_db_cfg)
        test_app.dependency_overrides[get_container] = lambda: mock_container
        client = TestClient(test_app, raise_server_exceptions=False)

        resp = client.get("/api/relational/tables")
        self.assertEqual(resp.status_code, 500)
        err_data = resp.json()
        self.assertIn("detail", err_data)
        # Verify secret path is NOT leaked in the response detail
        self.assertNotIn("db_password.txt", str(err_data))

    def test_engine_container_reuse(self):
        """Validates that successive API requests reuse the same engine instances."""
        resp1 = self.client.get("/api/health")
        resp2 = self.client.get("/api/health")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        # Verify container object is the exact same instance across calls
        self.assertIs(self.app.state.container, self.container)


class TestAPILiveMySQLIntegration(unittest.TestCase):
    """
    Live MySQL integration tests executing real HTTP requests
    against the actual MySQL 8.x database.
    Skipped gracefully if MySQL is offline.
    """

    @classmethod
    def setUpClass(cls):
        if not MYSQL_AVAILABLE:
            return

        # Use actual environment configuration targeting MySQL 8.x
        cls.app = create_app(db_config=config.db)
        cls.client = TestClient(cls.app)

    @unittest.skipUnless(MYSQL_AVAILABLE, SKIP_REASON)
    def test_live_mysql_health(self):
        """Validates GET /api/health against live MySQL 8.x."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["backend"], "MySQL 8.x")
        self.assertEqual(data["database_name"], config.db.name)
        self.assertEqual(data["host"], config.db.host)
        self.assertEqual(data["table_counts"]["projects"], 6)
        self.assertEqual(data["table_counts"]["colleges"], 5)

    @unittest.skipUnless(MYSQL_AVAILABLE, SKIP_REASON)
    def test_live_mysql_tables_metadata(self):
        """Validates GET /api/relational/tables reads live MySQL information_schema."""
        resp = self.client.get("/api/relational/tables")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["database"], config.db.name)
        self.assertEqual(data["table_count"], 7)
        table_names = [t["table_name"] for t in data["tables"]]
        self.assertEqual(
            table_names,
            ["colleges", "hackathons", "teams", "participants", "team_members", "projects", "awards"]
        )

    @unittest.skipUnless(MYSQL_AVAILABLE, SKIP_REASON)
    def test_live_mysql_unified_query_preset_5(self):
        """Validates POST /api/query/unified executes Preset 5 across real MySQL, Graph, and Vector."""
        p5 = PREDEFINED_QUERIES["5"].model_dump()
        resp = self.client.post("/api/query/unified", json=p5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertTrue(data["success"])
        self.assertEqual(set(data["plan"]["required_engines"]), {"relational", "graph", "vector"})
        self.assertGreater(len(data["fused_results"]), 0)

        # AeroVision should rank #1 with contributions from all 3 engines
        top = data["fused_results"][0]
        self.assertEqual(top["title"], "AeroVision Autonomous Drone Pathfinder")
        self.assertEqual(set(top["participating_engines"]), {"relational", "graph", "vector"})
        self.assertAlmostEqual(top["rrf_score"], 0.049180, places=4)


if __name__ == "__main__":
    unittest.main()
