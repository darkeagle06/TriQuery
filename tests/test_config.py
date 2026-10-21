"""
Unit tests for TriQuery configuration loader.
"""

import unittest
from src.config import AppConfig, DatabaseConfig, VectorConfig


class TestConfig(unittest.TestCase):
    def test_default_config_properties(self):
        cfg = AppConfig()
        self.assertIsNotNone(cfg.db)
        self.assertIsNotNone(cfg.vector)
        self.assertEqual(cfg.db.port, 3306)
        self.assertEqual(cfg.db.name, "triquery_db")
        self.assertIn(cfg.vector.backend, ["tfidf", "sentence_transformer"])
        self.assertGreater(cfg.vector.top_k, 0)
        self.assertTrue(cfg.base_dir.exists())
        self.assertTrue(cfg.database_dir.exists())


if __name__ == "__main__":
    unittest.main()
