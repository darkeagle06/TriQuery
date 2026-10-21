"""
Health & System Status API Routes.
Reports live database connectivity, table counts, graph topology metrics,
and active vector provider state.
"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import EngineContainer, get_container
from src.api.schemas import GraphHealthInfo, HealthResponse, VectorHealthInfo

router = APIRouter(prefix="/api", tags=["System & Health"])


@router.get("/health", response_model=HealthResponse)
def get_system_health(request: Request, container: EngineContainer = Depends(get_container)):
    """
    Returns comprehensive system health for Relational, Graph, and Vector engines.
    Reflects the actual live database connection and record counts.
    """
    rel = container.relational_engine
    graph = container.graph_engine
    vec = container.vector_engine

    # 1. Relational Health & Table Counts
    rel_healthy = rel.is_healthy()
    table_counts = rel.get_table_counts() if rel_healthy else {}

    backend_str = "SQLite (isolated mode)" if rel.conn_mgr.is_sqlite_mode else "MySQL 8.x"

    # 2. Graph Metrics
    graph_info = GraphHealthInfo(
        node_count=graph.node_count,
        edge_count=graph.edge_count,
        is_healthy=graph.is_healthy(),
    )

    # 3. Vector Metrics
    vec_provider_desc = getattr(vec.provider, "description", str(vec.provider))
    vec_dim = getattr(vec.index, "dimension", None)
    vector_info = VectorHealthInfo(
        provider=vec_provider_desc,
        dimension=vec_dim,
        document_count=vec.document_count,
        is_semantic=getattr(vec.provider, "is_semantic", False),
    )

    overall_healthy = rel_healthy and graph_info.is_healthy and vector_info.document_count > 0
    status_str = "healthy" if overall_healthy else ("degraded" if rel_healthy else "unhealthy")

    return HealthResponse(
        status=status_str,
        is_healthy=overall_healthy,
        backend=backend_str,
        database_name=container.cfg.name,
        host=container.cfg.host,
        port=container.cfg.port,
        table_counts=table_counts,
        graph=graph_info,
        vector=vector_info,
    )
