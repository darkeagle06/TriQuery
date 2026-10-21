"""
Relational Engine implementation for TriQuery.
Handles SQL query execution, timing, EXPLAIN analysis, and relational data access.
Implements representative relational operations: selection, projection, joins, aggregation, and sorting.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from src.core.types import EngineExecutionMetadata, EngineResult, EngineType
from src.engines.base import BaseEngine
from src.engines.relational.connection import DatabaseConnectionManager


class RelationalEngine(BaseEngine):
    """
    Relational Engine backed by MySQL 8.x (with isolated SQLite test runner).
    Executes relational algebra operations (selection, projection, joins, aggregations)
    and captures timing and explainability metadata.
    """

    def __init__(self, connection_manager: Optional[DatabaseConnectionManager] = None):
        self.conn_mgr = connection_manager or DatabaseConnectionManager()

    @property
    def engine_type(self) -> EngineType:
        return EngineType.RELATIONAL

    def is_healthy(self) -> bool:
        ok, _ = self.conn_mgr.test_connection()
        return ok

    def execute(
        self,
        query: str,
        params: Optional[Union[Tuple[Any, ...], Dict[str, Any], List[Any]]] = None,
        notes: Optional[List[str]] = None,
        **kwargs
    ) -> EngineResult:
        """
        Executes a SQL query, captures execution latency, row count, and returns EngineResult.
        Guarantees SQL injection protection via parameterized binding.
        """
        notes = notes or []
        start_time = time.perf_counter()
        try:
            records = self.conn_mgr.execute_query(query, params)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            metadata = EngineExecutionMetadata(
                engine=self.engine_type,
                execution_time_ms=round(duration_ms, 3),
                record_count=len(records),
                query_executed=query.strip(),
                notes=notes + [f"Backend: {'SQLite (isolated mode)' if self.conn_mgr.is_sqlite_mode else 'MySQL 8.x'}"]
            )
            return EngineResult(
                engine=self.engine_type,
                success=True,
                data=records,
                metadata=metadata
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            metadata = EngineExecutionMetadata(
                engine=self.engine_type,
                execution_time_ms=round(duration_ms, 3),
                record_count=0,
                query_executed=query.strip(),
                notes=notes + [f"Execution failed: {str(exc)}"]
            )
            return EngineResult(
                engine=self.engine_type,
                success=False,
                data=[],
                metadata=metadata,
                error=str(exc)
            )

    def explain(
        self,
        query: str,
        params: Optional[Union[Tuple[Any, ...], Dict[str, Any], List[Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Runs EXPLAIN on the SQL statement to inspect indexes used, scan types, and cost estimations.
        Essential for DBMS viva demonstrations of query optimization.
        """
        explain_sql = f"EXPLAIN {query}"
        try:
            records = self.conn_mgr.execute_query(explain_sql, params)
            return {
                "success": True,
                "engine": "relational",
                "backend": "sqlite" if self.conn_mgr.is_sqlite_mode else "mysql8",
                "explain_plan": records,
                "raw_query": query
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "raw_query": query
            }

    def execute_script_file(self, file_path: Union[str, Path]) -> None:
        """Loads and executes a multi-statement SQL script file (e.g. schema.sql)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"SQL script not found: {path}")
        sql_content = path.read_text(encoding="utf-8")
        self.conn_mgr.execute_script(sql_content)

    # -------------------------------------------------------------------------
    # Representative SQL Operations (Hackathon Dataset)
    # Demonstrating: Filtering, Multi-table Joins, Aggregation, and Sorting
    # -------------------------------------------------------------------------

    def get_table_counts(self) -> Dict[str, int]:
        """Returns row count for all canonical relational tables."""
        tables = ["colleges", "hackathons", "teams", "participants", "team_members", "projects", "awards"]
        counts = {}
        for tbl in tables:
            try:
                res = self.conn_mgr.execute_query(f"SELECT COUNT(*) AS total FROM {tbl}")
                counts[tbl] = res[0]["total"] if res else 0
            except Exception:
                counts[tbl] = 0
        return counts

    def get_projects_with_details(
        self,
        project_id: Optional[int] = None,
        track: Optional[str] = None
    ) -> EngineResult:
        """
        [Multi-Table JOIN + Filtering + Sorting]
        Executes a 5-way SQL JOIN combining projects, teams, colleges, hackathons, and awards.
        Demonstrates 3NF normalization traversal, foreign key navigation, and rank ordering.
        """
        clauses = []
        params = []
        if project_id is not None:
            clauses.append("p.project_id = %s")
            params.append(project_id)
        if track is not None:
            clauses.append("p.track = %s")
            params.append(track)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        sql = f"""
            SELECT
                p.project_id,
                p.title AS project_title,
                p.track,
                p.short_summary,
                p.description,
                p.tech_stack,
                t.team_name,
                c.name AS college_name,
                c.city AS college_city,
                h.name AS hackathon_name,
                h.edition_year AS hackathon_year,
                COALESCE(a.prize_category, 'Participant') AS prize_category,
                COALESCE(a.rank_position, 999) AS rank_position,
                COALESCE(a.cash_prize, 0.0) AS cash_prize
            FROM projects p
            JOIN teams t ON p.team_id = t.team_id
            JOIN colleges c ON t.college_id = c.college_id
            JOIN hackathons h ON p.hackathon_id = h.hackathon_id
            LEFT JOIN awards a ON p.project_id = a.project_id
            {where_clause}
            ORDER BY a.rank_position ASC, p.project_id ASC
        """
        return self.execute(
            sql,
            tuple(params),
            notes=["Operation: 5-way JOIN (projects -> teams -> colleges -> hackathons -> awards)"]
        )

    def find_projects_by_college(self, college_name: str) -> EngineResult:
        """
        [Filtering + Foreign Key Join + Sorting]
        Finds all projects submitted by teams affiliated with a specific college.
        Demonstrates parameterized equality filtering with index lookup.
        """
        sql = """
            SELECT
                p.project_id,
                p.title,
                p.track,
                p.tech_stack,
                t.team_name,
                c.name AS college_name,
                h.name AS hackathon_name,
                h.edition_year
            FROM projects p
            JOIN teams t ON p.team_id = t.team_id
            JOIN colleges c ON t.college_id = c.college_id
            JOIN hackathons h ON p.hackathon_id = h.hackathon_id
            WHERE c.name = %s
            ORDER BY p.title ASC
        """
        return self.execute(sql, (college_name,), notes=[f"Filter by college: {college_name}"])

    def find_top_award_winning_colleges(self) -> EngineResult:
        """
        [Analytical Aggregation + Multiple Joins + Sorting]
        Computes total prize money won and total awards earned grouped by college.
        Demonstrates relational algebra aggregations: GROUP BY, SUM(), COUNT(DISTINCT), ORDER BY DESC.
        """
        sql = """
            SELECT
                c.college_id,
                c.name AS college_name,
                c.city,
                c.state,
                COUNT(DISTINCT a.award_id) AS total_awards,
                COALESCE(SUM(a.cash_prize), 0.0) AS total_prize_money
            FROM colleges c
            JOIN teams t ON c.college_id = t.college_id
            JOIN projects p ON t.team_id = p.team_id
            JOIN awards a ON p.project_id = a.project_id
            GROUP BY c.college_id, c.name, c.city, c.state
            ORDER BY total_prize_money DESC, total_awards DESC
        """
        return self.execute(sql, notes=["Analytical aggregation: total prize money and awards by college"])

    def get_hackathon_summary_metrics(self) -> EngineResult:
        """
        [Multi-Level Aggregation + Group By + Sorting]
        Computes summary metrics for each hackathon: registered teams, submitted projects, awards, and payouts.
        Demonstrates multi-table summary analysis across hackathon editions.
        """
        sql = """
            SELECT
                h.hackathon_id,
                h.name AS hackathon_name,
                h.edition_year,
                h.theme,
                h.total_prize_pool,
                COUNT(DISTINCT p.project_id) AS total_projects_submitted,
                COUNT(DISTINCT a.award_id) AS total_awards_won,
                COALESCE(SUM(a.cash_prize), 0.0) AS total_cash_distributed
            FROM hackathons h
            LEFT JOIN projects p ON h.hackathon_id = p.hackathon_id
            LEFT JOIN awards a ON p.project_id = a.project_id
            GROUP BY h.hackathon_id, h.name, h.edition_year, h.theme, h.total_prize_pool
            ORDER BY h.edition_year DESC, total_awards_won DESC
        """
        return self.execute(sql, notes=["Hackathon summary metrics with multi-table aggregation"])

    def filter_participants_by_role_and_college(
        self,
        college_name: Optional[str] = None,
        role: Optional[str] = None
    ) -> EngineResult:
        """
        [Many-to-Many Junction Traversal + Multi-predicate Filtering]
        Finds student participants and their roles in teams across institutions.
        Demonstrates traversal through the `team_members` junction table.
        """
        clauses = []
        params = []
        if college_name:
            clauses.append("c.name = %s")
            params.append(college_name)
        if role:
            clauses.append("tm.role = %s")
            params.append(role)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        sql = f"""
            SELECT
                p.participant_id,
                p.full_name,
                p.email,
                c.name AS college_name,
                t.team_name,
                tm.role
            FROM participants p
            JOIN colleges c ON p.college_id = c.college_id
            JOIN team_members tm ON p.participant_id = tm.participant_id
            JOIN teams t ON tm.team_id = t.team_id
            {where_clause}
            ORDER BY c.name ASC, p.full_name ASC
        """
        return self.execute(
            sql,
            tuple(params),
            notes=["Many-to-many junction traversal: participants <-> team_members <-> teams"]
        )
