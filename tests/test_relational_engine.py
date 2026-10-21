"""
Automated tests for TriQuery Relational Engine.
Validates table creation, constraint checks, multi-table JOINs,
aggregations, query timing, and explainability output.
"""

import json
import unittest
from src.config import DatabaseConfig
from src.engines.relational.connection import DatabaseConnectionManager
from src.engines.relational.engine import RelationalEngine


class TestRelationalEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure isolated in-memory SQLite test database with foreign key enforcement
        cls.db_config = DatabaseConfig(sqlite_fallback=True, sqlite_path=":memory:")
        cls.conn_mgr = DatabaseConnectionManager(cls.db_config)
        cls.engine = RelationalEngine(cls.conn_mgr)

        # Initialize schema in test database
        cls._init_test_schema()
        cls._load_test_seed_data()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn_mgr") and cls.conn_mgr:
            cls.conn_mgr.close()

    @classmethod
    def _init_test_schema(cls):
        """Creates normalized tables in isolated test database."""
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS colleges (
                college_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                country TEXT NOT NULL DEFAULT 'India',
                established_year INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS hackathons (
                hackathon_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                edition_year INTEGER NOT NULL,
                organizer TEXT NOT NULL,
                city TEXT NOT NULL,
                theme TEXT NOT NULL,
                total_prize_pool REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (name, edition_year)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS teams (
                team_id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                college_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (college_id) REFERENCES colleges (college_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                UNIQUE (team_name, college_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS participants (
                participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                college_id INTEGER NOT NULL,
                graduation_year INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (college_id) REFERENCES colleges (college_id) ON UPDATE CASCADE ON DELETE RESTRICT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS team_members (
                team_id INTEGER NOT NULL,
                participant_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'Developer',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_id, participant_id),
                FOREIGN KEY (team_id) REFERENCES teams (team_id) ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY (participant_id) REFERENCES participants (participant_id) ON UPDATE CASCADE ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                hackathon_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                track TEXT NOT NULL,
                short_summary TEXT NOT NULL,
                description TEXT NOT NULL,
                tech_stack TEXT NOT NULL,
                github_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (team_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                FOREIGN KEY (hackathon_id) REFERENCES hackathons (hackathon_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                UNIQUE (team_id, hackathon_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS awards (
                award_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                hackathon_id INTEGER NOT NULL,
                prize_category TEXT NOT NULL,
                rank_position INTEGER NOT NULL,
                cash_prize REAL NOT NULL DEFAULT 0.0,
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (project_id) ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY (hackathon_id) REFERENCES hackathons (hackathon_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                UNIQUE (hackathon_id, project_id, prize_category)
            )
            """
        ]
        for statement in ddl_statements:
            cls.conn_mgr.execute_non_query(statement)

    @classmethod
    def _load_test_seed_data(cls):
        """Loads data from seed_data.json into the test database."""
        from src.config import config
        with open(config.database_dir / "seed_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        for c in data["colleges"]:
            cls.conn_mgr.execute_non_query(
                "INSERT INTO colleges (college_id, name, city, state, country, established_year) VALUES (?, ?, ?, ?, ?, ?)",
                (c["college_id"], c["name"], c["city"], c["state"], c["country"], c["established_year"])
            )
        for h in data["hackathons"]:
            cls.conn_mgr.execute_non_query(
                "INSERT INTO hackathons (hackathon_id, name, edition_year, organizer, city, theme, total_prize_pool) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (h["hackathon_id"], h["name"], h["edition_year"], h["organizer"], h["city"], h["theme"], h["total_prize_pool"])
            )
        for t in data["teams"]:
            cls.conn_mgr.execute_non_query(
                "INSERT INTO teams (team_id, team_name, college_id) VALUES (?, ?, ?)",
                (t["team_id"], t["team_name"], t["college_id"])
            )
        for p in data["participants"]:
            cls.conn_mgr.execute_non_query(
                "INSERT INTO participants (participant_id, full_name, email, college_id, graduation_year) VALUES (?, ?, ?, ?, ?)",
                (p["participant_id"], p["full_name"], p["email"], p["college_id"], p["graduation_year"])
            )
        for tm in data["team_members"]:
            cls.conn_mgr.execute_non_query(
                "INSERT INTO team_members (team_id, participant_id, role) VALUES (?, ?, ?)",
                (tm["team_id"], tm["participant_id"], tm["role"])
            )
        for pr in data["projects"]:
            cls.conn_mgr.execute_non_query(
                "INSERT INTO projects (project_id, team_id, hackathon_id, title, track, short_summary, description, tech_stack, github_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pr["project_id"], pr["team_id"], pr["hackathon_id"], pr["title"], pr["track"], pr["short_summary"], pr["description"], pr["tech_stack"], pr["github_url"])
            )
        for a in data["awards"]:
            cls.conn_mgr.execute_non_query(
                "INSERT INTO awards (award_id, project_id, hackathon_id, prize_category, rank_position, cash_prize) VALUES (?, ?, ?, ?, ?, ?)",
                (a["award_id"], a["project_id"], a["hackathon_id"], a["prize_category"], a["rank_position"], a["cash_prize"])
            )

    def test_health_check(self):
        self.assertTrue(self.engine.is_healthy())

    def test_table_counts(self):
        counts = self.engine.get_table_counts()
        self.assertEqual(counts["colleges"], 5)
        self.assertEqual(counts["hackathons"], 3)
        self.assertEqual(counts["teams"], 6)
        self.assertEqual(counts["participants"], 12)
        self.assertEqual(counts["projects"], 6)
        self.assertEqual(counts["awards"], 6)

    def test_multi_table_join_projects_with_details(self):
        result = self.engine.get_projects_with_details()
        self.assertTrue(result.success)
        self.assertGreater(result.metadata.execution_time_ms, 0.0)
        self.assertEqual(len(result.data), 6)
        # Verify columns from distinct joined tables exist
        first_row = result.data[0]
        self.assertIn("project_title", first_row)
        self.assertIn("team_name", first_row)
        self.assertIn("college_name", first_row)
        self.assertIn("hackathon_name", first_row)
        self.assertIn("prize_category", first_row)

    def test_filter_by_college(self):
        result = self.engine.find_projects_by_college("IIT Delhi")
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0]["title"], "AeroVision Autonomous Drone Pathfinder")

    def test_analytical_aggregation_awards(self):
        result = self.engine.find_top_award_winning_colleges()
        self.assertTrue(result.success)
        self.assertGreater(len(result.data), 0)
        # Top winning colleges should have positive prize money
        top_college = result.data[0]
        self.assertGreater(top_college["total_prize_money"], 0.0)

    def test_hackathon_summary_metrics(self):
        result = self.engine.get_hackathon_summary_metrics()
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 3)
        top_hackathon = result.data[0]
        self.assertIn("hackathon_name", top_hackathon)
        self.assertIn("total_projects_submitted", top_hackathon)
        self.assertIn("total_awards_won", top_hackathon)

    def test_filter_participants_by_role_and_college(self):
        result = self.engine.filter_participants_by_role_and_college(college_name="IIT Delhi")
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)
        names = [p["full_name"] for p in result.data]
        self.assertIn("Aarav Sharma", names)
        self.assertIn("Diya Patel", names)

    def test_explain_plan(self):
        explain_res = self.engine.explain("SELECT * FROM projects WHERE track = 'Robotics & AI'")
        self.assertTrue(explain_res["success"])
        self.assertIn("explain_plan", explain_res)


if __name__ == "__main__":
    unittest.main()
