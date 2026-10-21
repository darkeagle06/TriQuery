"""
Tests for schema definitions and seed data integrity.
Ensures no broken foreign keys, missing columns, or malformed JSON payloads.
"""

import json
import unittest
from pathlib import Path
from src.config import config


class TestSchemaAndSeedData(unittest.TestCase):
    def setUp(self):
        self.db_dir = config.database_dir
        self.schema_path = self.db_dir / "schema.sql"
        self.seed_sql_path = self.db_dir / "seed_data.sql"
        self.seed_json_path = self.db_dir / "seed_data.json"

    def test_schema_file_exists_and_contains_core_tables(self):
        self.assertTrue(self.schema_path.exists(), "schema.sql must exist")
        content = self.schema_path.read_text(encoding="utf-8")
        expected_tables = [
            "colleges",
            "hackathons",
            "teams",
            "participants",
            "team_members",
            "projects",
            "awards",
        ]
        for tbl in expected_tables:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {tbl}", content)

    def test_seed_json_referential_integrity(self):
        self.assertTrue(self.seed_json_path.exists(), "seed_data.json must exist")
        with open(self.seed_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        college_ids = {c["college_id"] for c in data["colleges"]}
        hackathon_ids = {h["hackathon_id"] for h in data["hackathons"]}
        team_ids = {t["team_id"] for t in data["teams"]}
        participant_ids = {p["participant_id"] for p in data["participants"]}
        project_ids = {pr["project_id"] for pr in data["projects"]}

        # Check teams -> colleges
        for team in data["teams"]:
            self.assertIn(
                team["college_id"],
                college_ids,
                f"Team {team['team_name']} references invalid college_id {team['college_id']}"
            )

        # Check participants -> colleges
        for participant in data["participants"]:
            self.assertIn(
                participant["college_id"],
                college_ids,
                f"Participant {participant['full_name']} references invalid college_id {participant['college_id']}"
            )

        # Check team_members -> teams and participants
        for tm in data["team_members"]:
            self.assertIn(tm["team_id"], team_ids, f"team_member references invalid team_id {tm['team_id']}")
            self.assertIn(tm["participant_id"], participant_ids, f"team_member references invalid participant_id {tm['participant_id']}")

        # Check projects -> teams and hackathons
        for project in data["projects"]:
            self.assertIn(project["team_id"], team_ids, f"Project {project['title']} references invalid team_id {project['team_id']}")
            self.assertIn(project["hackathon_id"], hackathon_ids, f"Project {project['title']} references invalid hackathon_id {project['hackathon_id']}")
            self.assertGreater(len(project["description"]), 50, f"Project {project['title']} needs a detailed description for vector search")

        # Check awards -> projects and hackathons
        for award in data["awards"]:
            self.assertIn(award["project_id"], project_ids, f"Award {award['award_id']} references invalid project_id {award['project_id']}")
            self.assertIn(award["hackathon_id"], hackathon_ids, f"Award {award['award_id']} references invalid hackathon_id {award['hackathon_id']}")


if __name__ == "__main__":
    unittest.main()
