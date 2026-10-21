"""
Relational Engine API Routes.
Exposes actual 3NF table schemas, column types, foreign key relationships,
and parameterized project queries with multi-table joins.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_relational_engine
from src.api.schemas import (
    ForeignKeySchema,
    ProjectsResponse,
    TableColumnSchema,
    TableSchema,
    TablesResponse,
)
from src.engines.relational.engine import RelationalEngine

logger = logging.getLogger("triquery.api.relational")

router = APIRouter(prefix="/api/relational", tags=["Relational Engine"])


def _get_mysql_table_metadata(rel: RelationalEngine) -> List[TableSchema]:
    """Inspects tables and foreign keys via MySQL information_schema."""
    db_name = rel.conn_mgr.cfg.name
    counts = rel.get_table_counts()

    # 1. Fetch Columns
    sql_cols = """
        SELECT table_name, column_name, data_type, is_nullable, column_key, column_default
        FROM information_schema.columns
        WHERE table_schema = %s
        ORDER BY table_name, ordinal_position
    """
    col_rows = rel.conn_mgr.execute_query(sql_cols, (db_name,))
    col_rows = [{k.lower(): v for k, v in r.items()} for r in col_rows]

    # 2. Fetch Foreign Keys
    sql_fks = """
        SELECT table_name, column_name, referenced_table_name, referenced_column_name
        FROM information_schema.key_column_usage
        WHERE table_schema = %s AND referenced_table_name IS NOT NULL
        ORDER BY table_name, column_name
    """
    fk_rows = rel.conn_mgr.execute_query(sql_fks, (db_name,))
    fk_rows = [{k.lower(): v for k, v in r.items()} for r in fk_rows]

    # Group by table
    fks_by_table = {}
    for fk in fk_rows:
        tname = fk["table_name"]
        fks_by_table.setdefault(tname, []).append(
            ForeignKeySchema(
                column=fk["column_name"],
                referenced_table=fk["referenced_table_name"],
                referenced_column=fk["referenced_column_name"],
            )
        )

    cols_by_table = {}
    for col in col_rows:
        tname = col["table_name"]
        cols_by_table.setdefault(tname, []).append(
            TableColumnSchema(
                name=col["column_name"],
                type=col["data_type"],
                nullable=(col["is_nullable"].upper() == "YES"),
                primary_key=(col.get("column_key") == "PRI"),
                default=col.get("column_default"),
            )
        )

    table_schemas = []
    canonical_order = ["colleges", "hackathons", "teams", "participants", "team_members", "projects", "awards"]
    for tbl in canonical_order:
        if tbl in cols_by_table:
            table_schemas.append(
                TableSchema(
                    table_name=tbl,
                    row_count=counts.get(tbl, 0),
                    columns=cols_by_table[tbl],
                    foreign_keys=fks_by_table.get(tbl, []),
                )
            )

    return table_schemas


def _get_sqlite_table_metadata(rel: RelationalEngine) -> List[TableSchema]:
    """Inspects tables and foreign keys via SQLite PRAGMA commands."""
    counts = rel.get_table_counts()
    table_schemas = []
    canonical_order = ["colleges", "hackathons", "teams", "participants", "team_members", "projects", "awards"]

    for tbl in canonical_order:
        try:
            col_rows = rel.conn_mgr.execute_query(f"PRAGMA table_info({tbl})")
            columns = [
                TableColumnSchema(
                    name=r["name"],
                    type=r["type"] or "TEXT",
                    nullable=(r["notnull"] == 0),
                    primary_key=(r["pk"] == 1),
                    default=r.get("dflt_value"),
                )
                for r in col_rows
            ]

            fk_rows = rel.conn_mgr.execute_query(f"PRAGMA foreign_key_list({tbl})")
            foreign_keys = [
                ForeignKeySchema(
                    column=r["from"],
                    referenced_table=r["table"],
                    referenced_column=r["to"],
                )
                for r in fk_rows
            ]

            table_schemas.append(
                TableSchema(
                    table_name=tbl,
                    row_count=counts.get(tbl, 0),
                    columns=columns,
                    foreign_keys=foreign_keys,
                )
            )
        except Exception as exc:
            logger.warning(f"Failed to inspect SQLite table {tbl}: {exc}")

    return table_schemas


@router.get("/tables", response_model=TablesResponse)
def get_relational_tables(rel: RelationalEngine = Depends(get_relational_engine)):
    """
    Returns actual schema metadata, column types, constraints, and foreign-key relationships.
    Queries live MySQL information_schema (or SQLite PRAGMA in test fallback).
    """
    if not rel.is_healthy():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Relational database is unreachable. Check connection parameters."
        )

    try:
        if rel.conn_mgr.is_sqlite_mode:
            tables = _get_sqlite_table_metadata(rel)
        else:
            tables = _get_mysql_table_metadata(rel)
    except Exception as exc:
        logger.error(f"Error inspecting relational schema: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve relational table metadata."
        )

    return TablesResponse(
        database=rel.conn_mgr.cfg.name,
        table_count=len(tables),
        tables=tables,
    )


@router.get("/projects", response_model=ProjectsResponse)
def get_projects(
    track: Optional[str] = Query(default=None, max_length=100, description="Filter by hackathon track (e.g. 'Robotics & AI')"),
    college: Optional[str] = Query(default=None, max_length=150, description="Filter projects by affiliated college name"),
    project_id: Optional[int] = Query(default=None, ge=1, description="Filter by exact project ID"),
    rel: RelationalEngine = Depends(get_relational_engine),
):
    """
    Queries projects using parameterized 5-way SQL JOINs across projects, teams,
    colleges, hackathons, and awards. Protects against SQL injection.
    """
    if not rel.is_healthy():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Relational database is unreachable."
        )

    try:
        if college:
            result = rel.find_projects_by_college(college)
        else:
            result = rel.get_projects_with_details(project_id=project_id, track=track)
    except Exception as exc:
        logger.error(f"Error querying projects: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Relational project query failed."
        )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error or "Project query returned an error."
        )

    meta = result.metadata
    return ProjectsResponse(
        success=True,
        count=len(result.data),
        data=result.data,
        execution_time_ms=meta.execution_time_ms if meta else 0.0,
        notes=meta.notes if meta else [],
    )
