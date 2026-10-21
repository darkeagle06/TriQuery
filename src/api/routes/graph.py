"""
Graph Engine API Routes.
Exposes actual NetworkX knowledge graph topology (nodes, edges)
and executes shortest-path and neighborhood traversals.
"""

import logging
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_graph_engine
from src.api.schemas import (
    GraphEdgeItem,
    GraphNodeItem,
    GraphPathRequest,
    GraphPathResponse,
    GraphTopologyResponse,
)
from src.engines.graph.engine import GraphEngine

logger = logging.getLogger("triquery.api.graph")

router = APIRouter(prefix="/api/graph", tags=["Graph Engine"])


@router.get("/topology", response_model=GraphTopologyResponse)
def get_graph_topology(graph_engine: GraphEngine = Depends(get_graph_engine)):
    """
    Returns the complete knowledge graph topology (38 entity nodes, 55 directed edges)
    constructed directly from verified relational foreign key constraints.
    """
    if not graph_engine.is_healthy():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph engine is uninitialized or has zero nodes."
        )

    g = graph_engine.graph
    nodes = []
    node_types = Counter()

    for node_id, data in g.nodes(data=True):
        nt = data.get("node_type", "unknown")
        node_types[nt] += 1
        nodes.append(
            GraphNodeItem(
                id=node_id,
                label=data.get("label", node_id),
                node_type=nt,
                attributes={k: v for k, v in data.items() if k not in ("label", "node_type")},
            )
        )

    edges = []
    edge_types = Counter()

    for u, v, data in g.edges(data=True):
        et = data.get("edge_type", "RELATED_TO")
        edge_types[et] += 1
        edges.append(
            GraphEdgeItem(
                source=u,
                target=v,
                edge_type=et,
                direction="directed",
                attributes={k: v for k, v in data.items() if k != "edge_type"},
            )
        )

    return GraphTopologyResponse(
        node_count=len(nodes),
        edge_count=len(edges),
        node_types=dict(node_types),
        edge_types=dict(edge_types),
        nodes=nodes,
        edges=edges,
    )


@router.post("/path", response_model=GraphPathResponse)
def find_graph_path(
    req: GraphPathRequest,
    graph_engine: GraphEngine = Depends(get_graph_engine),
):
    """
    Executes BFS shortest-path exploration between two entities.
    Resolves natural entity names (e.g. 'IIT Delhi', 'AeroVision') or canonical IDs (e.g. 'college:1').
    """
    if not graph_engine.is_healthy():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph engine is uninitialized."
        )

    try:
        path_res = graph_engine.find_shortest_path(
            source_identifier=req.source,
            target_identifier=req.target,
            directed=req.directed,
        )
    except Exception as exc:
        logger.error(f"Path finding error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute graph relationship path."
        )

    steps_dict = [
        {
            "from_node": s.from_node,
            "to_node": s.to_node,
            "edge_type": s.edge_type,
            "direction": s.direction,
        }
        for s in path_res.steps
    ]

    return GraphPathResponse(
        found=path_res.found,
        source=path_res.source,
        target=path_res.target,
        length=path_res.length,
        path=path_res.path,
        steps=steps_dict,
        message=path_res.message,
    )
