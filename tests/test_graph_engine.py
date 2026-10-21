"""
Automated Unit Tests for TriQuery Graph Engine (NetworkX).
Validates graph construction, node/edge type integrity, BFS, DFS,
shortest paths, disconnected components, missing nodes, and consistency with relational source data.
"""

import unittest
from src.config import DatabaseConfig
from src.engines.graph.engine import GraphEngine
from src.engines.graph.types import EdgeType, NodeType
from src.engines.relational.connection import DatabaseConnectionManager
from src.engines.relational.engine import RelationalEngine
from tests.test_relational_engine import TestRelationalEngine


class TestGraphEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use isolated in-memory test relational database initialized with seed data
        cls.db_config = DatabaseConfig(sqlite_fallback=True, sqlite_path=":memory:")
        cls.conn_mgr = DatabaseConnectionManager(cls.db_config)
        cls.rel_engine = RelationalEngine(cls.conn_mgr)

        # Initialize schema and seed data in test database
        TestRelationalEngine._init_test_schema.__func__(cls)
        TestRelationalEngine._load_test_seed_data.__func__(cls)

        # Build GraphEngine from the initialized relational engine
        cls.graph_engine = GraphEngine(relational_engine=cls.rel_engine, auto_build=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn_mgr") and cls.conn_mgr:
            cls.conn_mgr.close()

    def test_graph_health(self):
        self.assertTrue(self.graph_engine.is_healthy())
        self.assertGreater(self.graph_engine.node_count, 0)
        self.assertGreater(self.graph_engine.edge_count, 0)

    def test_node_and_edge_counts(self):
        # 5 colleges + 3 hackathons + 6 teams + 12 participants + 6 projects + 6 awards = 38 nodes
        self.assertEqual(self.graph_engine.node_count, 38)
        # 6 affiliated + 6 competed + 12 enrolled + 13 member_of + 6 presented + 6 submitted + 6 won_award = 55 edges
        self.assertEqual(self.graph_engine.edge_count, 55)

    def test_node_types_and_identifiers(self):
        expected_types = {
            NodeType.COLLEGE.value: 5,
            NodeType.HACKATHON.value: 3,
            NodeType.TEAM.value: 6,
            NodeType.PARTICIPANT.value: 12,
            NodeType.PROJECT.value: 6,
            NodeType.AWARD.value: 6,
        }
        actual_types = {}
        for node_id, data in self.graph_engine.graph.nodes(data=True):
            # Check ID format: "type:id"
            self.assertIn(":", node_id)
            prefix, raw_id = node_id.split(":", 1)
            self.assertTrue(raw_id.isdigit())
            nt = data.get("node_type")
            actual_types[nt] = actual_types.get(nt, 0) + 1

        self.assertEqual(actual_types, expected_types)

    def test_edge_types_and_attributes(self):
        edge_types_found = set()
        for u, v, data in self.graph_engine.graph.edges(data=True):
            et = data.get("edge_type")
            edge_types_found.add(et)
            if et == EdgeType.MEMBER_OF.value:
                self.assertIn("role", data)
                self.assertTrue(u.startswith("participant:"))
                self.assertTrue(v.startswith("team:"))
            elif et == EdgeType.AFFILIATED_WITH.value:
                self.assertTrue(u.startswith("team:"))
                self.assertTrue(v.startswith("college:"))
            elif et == EdgeType.SUBMITTED.value:
                self.assertTrue(u.startswith("team:"))
                self.assertTrue(v.startswith("project:"))
            elif et == EdgeType.COMPETED_AT.value:
                self.assertTrue(u.startswith("project:"))
                self.assertTrue(v.startswith("hackathon:"))
            elif et == EdgeType.WON_AWARD.value:
                self.assertIn("rank", data)
                self.assertTrue(u.startswith("project:"))
                self.assertTrue(v.startswith("award:"))

        expected_edges = {e.value for e in EdgeType}
        self.assertEqual(edge_types_found, expected_edges)

    def test_get_team_members(self):
        result = self.graph_engine.get_team_members("NeuralVanguard")
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)
        names = {m["full_name"] for m in result.data}
        self.assertEqual(names, {"Aarav Sharma", "Diya Patel"})
        roles = {m["role"] for m in result.data}
        self.assertEqual(roles, {"ML Lead", "Systems Engineer"})

    def test_get_college_projects(self):
        result = self.graph_engine.get_college_projects("IIT Delhi")
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        proj = result.data[0]
        self.assertEqual(proj["title"], "AeroVision Autonomous Drone Pathfinder")
        self.assertIn("1st Place Grand Winner", proj["award"])

    def test_shortest_path_existing(self):
        # Collaborator path: Participant 3 -> (College 2 or Team 2) -> Participant 4 (guest) -> Team 4 -> Participant 7
        path_res = self.graph_engine.find_shortest_path("participant:3", "participant:7")
        self.assertTrue(path_res.found)
        self.assertEqual(path_res.length, 4)
        self.assertEqual(path_res.path[0], "participant:3")
        self.assertIn(path_res.path[1], ["college:2", "team:2"])
        self.assertEqual(path_res.path[2:], ["participant:4", "team:4", "participant:7"])
        self.assertEqual(len(path_res.steps), 4)

    def test_shortest_path_same_node(self):
        path_res = self.graph_engine.find_shortest_path("participant:1", "participant:1")
        self.assertTrue(path_res.found)
        self.assertEqual(path_res.length, 0)
        self.assertEqual(path_res.path, ["participant:1"])

    def test_shortest_path_disconnected(self):
        # Participant 1 and College 5 belong to disconnected components
        path_res = self.graph_engine.find_shortest_path("participant:1", "college:5")
        self.assertFalse(path_res.found)
        self.assertEqual(path_res.length, 0)
        self.assertEqual(len(path_res.path), 0)
        self.assertIn("No relationship path exists", path_res.message)

    def test_missing_entities_handling(self):
        path_res = self.graph_engine.find_shortest_path("participant:9999", "college:1")
        self.assertFalse(path_res.found)
        self.assertIn("Source entity not found", path_res.message)

        target_missing = self.graph_engine.find_shortest_path("college:1", "unknown_node")
        self.assertFalse(target_missing.found)
        self.assertIn("Target entity not found", target_missing.message)

        missing_team = self.graph_engine.get_team_members("NonExistentTeam")
        self.assertFalse(missing_team.success)
        self.assertEqual(len(missing_team.data), 0)

    def test_bfs_traversal(self):
        visited = self.graph_engine.bfs_traversal("team:1", max_depth=1)
        self.assertGreater(len(visited), 0)
        # Root node at depth 0
        self.assertEqual(visited[0]["node_id"], "team:1")
        self.assertEqual(visited[0]["depth"], 0)
        # Depth 1 nodes should only be immediate neighbors
        depths = {n["depth"] for n in visited}
        self.assertTrue(depths.issubset({0, 1}))

    def test_dfs_traversal(self):
        visited = self.graph_engine.dfs_traversal("team:1", max_depth=2)
        self.assertGreater(len(visited), 0)
        self.assertEqual(visited[0]["node_id"], "team:1")
        self.assertEqual(visited[0]["depth"], 0)
        for node in visited:
            self.assertLessEqual(node["depth"], 2)

    def test_consistency_with_relational_records(self):
        # Relational check: count members of team 1
        rel_res = self.rel_engine.conn_mgr.execute_query(
            "SELECT COUNT(*) AS total FROM team_members WHERE team_id = 1"
        )
        sql_count = rel_res[0]["total"]

        # Graph check: count members of team:1
        graph_res = self.graph_engine.get_team_members("team:1")
        graph_count = len(graph_res.data)

        self.assertEqual(sql_count, graph_count)

    def test_empty_dataset_handling(self):
        # Create an isolated connection with empty tables
        empty_cfg = DatabaseConfig(sqlite_fallback=True, sqlite_path=":memory:")
        empty_mgr = DatabaseConnectionManager(empty_cfg)
        TestRelationalEngine._init_test_schema.__func__(type("EmptyTest", (), {"conn_mgr": empty_mgr}))

        empty_graph = GraphEngine(relational_engine=RelationalEngine(empty_mgr), auto_build=True)
        self.assertEqual(empty_graph.node_count, 0)
        self.assertEqual(empty_graph.edge_count, 0)

        # Ensure methods handle empty graph gracefully
        res = empty_graph.get_team_members("team:1")
        self.assertFalse(res.success)
        self.assertEqual(len(res.data), 0)

        path_res = empty_graph.find_shortest_path("college:1", "project:1")
        self.assertFalse(path_res.found)

    def test_explain_complexity(self):
        bfs_exp = self.graph_engine.explain("bfs")
        self.assertIn("O(|V| + |E|)", bfs_exp["time_complexity"])
        self.assertIn("comparison_with_sql", bfs_exp)

        dfs_exp = self.graph_engine.explain("dfs")
        self.assertIn("O(|V| + |E|)", dfs_exp["time_complexity"])

        sp_exp = self.graph_engine.explain("shortest_path")
        self.assertIn("O(|V| + |E|)", sp_exp["time_complexity"])


if __name__ == "__main__":
    unittest.main()
