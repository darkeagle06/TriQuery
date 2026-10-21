"""
MySQL 8.x Live Integration Test Suite for TriQuery.
Specifically tests actual connection, DDL execution, seed loading,
and relational operations against a live MySQL 8.x server.

Separated from offline unit tests:
Skips gracefully if MySQL is not running or credentials/drivers are not configured.
"""

import os
import unittest
from pathlib import Path
from src.config import DatabaseConfig, config
from src.engines.relational.connection import DatabaseConnectionManager
from src.engines.relational.engine import RelationalEngine


def is_mysql_available() -> bool:
    """Checks whether a live MySQL server is reachable with the configured credentials."""
    # Check if a MySQL driver is installed
    driver_available = False
    try:
        import pymysql
        driver_available = True
    except ImportError:
        try:
            import mysql.connector
            driver_available = True
        except ImportError:
            driver_available = False

    if not driver_available:
        return False

    # Check network reachability and credentials
    try:
        mysql_cfg = DatabaseConfig(
            driver="mysql",
            sqlite_fallback=False
        )
        conn_mgr = DatabaseConnectionManager(mysql_cfg)
        healthy, _ = conn_mgr.test_connection()
        return healthy
    except Exception:
        return False


MYSQL_AVAILABLE = is_mysql_available()
SKIP_REASON = (
    "Live MySQL 8.x server not detected or driver (pymysql) not installed. "
    "To run live MySQL tests: ensure MySQL 8 is running on port 3306, "
    "install pymysql ('pip install pymysql'), and set DB_PASSWORD in .env."
)


@unittest.skipUnless(MYSQL_AVAILABLE, SKIP_REASON)
class TestMySQLIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mysql_cfg = DatabaseConfig(
            driver="mysql",
            sqlite_fallback=False
        )
        cls.conn_mgr = DatabaseConnectionManager(cls.mysql_cfg)
        cls.conn_mgr.ensure_database_exists()
        cls.engine = RelationalEngine(cls.conn_mgr)

        # Execute schema and seed data safely against live MySQL
        cls.engine.execute_script_file(config.database_dir / "schema.sql")
        cls.engine.execute_script_file(config.database_dir / "seed_data.sql")

    def test_mysql_health_and_version(self):
        result = self.conn_mgr.execute_query("SELECT VERSION() AS ver, DATABASE() AS db")
        self.assertTrue(len(result) > 0)
        version_str = result[0]["ver"]
        db_name = result[0]["db"]
        self.assertIn("8.", version_str, f"Expected MySQL 8.x, found: {version_str}")
        self.assertEqual(db_name, self.mysql_cfg.name)

    def test_mysql_table_counts(self):
        counts = self.engine.get_table_counts()
        self.assertEqual(counts["colleges"], 5)
        self.assertEqual(counts["hackathons"], 3)
        self.assertEqual(counts["teams"], 6)
        self.assertEqual(counts["participants"], 12)
        self.assertEqual(counts["team_members"], 13)
        self.assertEqual(counts["projects"], 6)
        self.assertEqual(counts["awards"], 6)

    def test_mysql_multi_table_join(self):
        result = self.engine.get_projects_with_details()
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 6)
        first = result.data[0]
        self.assertIn("project_title", first)
        self.assertIn("team_name", first)
        self.assertIn("college_name", first)
        self.assertIn("hackathon_name", first)
        self.assertIn("prize_category", first)

    def test_mysql_aggregation_and_ordering(self):
        result = self.engine.find_top_award_winning_colleges()
        self.assertTrue(result.success)
        self.assertGreater(len(result.data), 0)
        # Check that ordering is descending by prize money
        prizes = [float(r["total_prize_money"]) for r in result.data]
        self.assertEqual(prizes, sorted(prizes, reverse=True))

    def test_mysql_foreign_key_constraint_enforcement(self):
        """Verifies that MySQL InnoDB strictly rejects orphaned foreign key insertions."""
        invalid_project_sql = """
            INSERT INTO projects (team_id, hackathon_id, title, track, short_summary, description, tech_stack)
            VALUES (99999, 1, 'Orphan Project', 'Test', 'Short', 'Detailed description', 'Python')
        """
        with self.assertRaises(Exception):
            self.conn_mgr.execute_non_query(invalid_project_sql)

    def test_mysql_parameterized_query_safety(self):
        """Verifies that SQL injection attempts via parameters are safely escaped by driver."""
        injection_attempt = "' OR '1'='1"
        result = self.engine.find_projects_by_college(injection_attempt)
        self.assertTrue(result.success)
        # Should return 0 records because no college is named literally "' OR '1'='1"
        self.assertEqual(len(result.data), 0)

    def test_mysql_explain_plan(self):
        explain_res = self.engine.explain("SELECT * FROM projects WHERE track = 'Robotics & AI'")
        self.assertTrue(explain_res["success"])
        self.assertEqual(explain_res["backend"], "mysql8")
        self.assertIn("explain_plan", explain_res)


if __name__ == "__main__":
    unittest.main()
