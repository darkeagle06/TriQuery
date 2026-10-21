"""
Unified Query Representation for TriQuery (Milestone 4).
Expresses relational filters/joins, graph traversals/paths, and vector similarity searches
in a strongly-typed, composable data structure.
"""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RelationalSubquery(BaseModel):
    """Declarative specification for relational filters, joins, or aggregations."""
    table: str = "projects"
    filters: Dict[str, Any] = Field(default_factory=dict, description="Key-value filters (e.g. {'track': 'Robotics & AI'})")
    college_name: Optional[str] = None
    columns: Optional[List[str]] = None
    aggregation: Optional[str] = None  # e.g. "leaderboard", "hackathon_metrics"
    raw_sql: Optional[str] = None


class GraphSubquery(BaseModel):
    """Declarative specification for graph traversals and relationship queries."""
    operation: str = Field(description="One of: 'shortest_path', 'team_members', 'college_projects', 'bfs'")
    source_entity: Optional[str] = None  # e.g. 'participant:1' or 'IIT Delhi'
    target_entity: Optional[str] = None  # e.g. 'participant:5'
    max_depth: Optional[int] = 2
    directed: bool = False


class VectorSubquery(BaseModel):
    """Declarative specification for vector similarity search."""
    text: str = Field(description="Natural language query string")
    top_k: int = 5
    min_score: float = 0.0
    provider: Optional[str] = None


class FusionConfig(BaseModel):
    """Configuration for Reciprocal Rank Fusion (RRF)."""
    method: str = "rrf"
    k: int = Field(default=60, description="RRF constant (default: 60)")
    mandatory_relational_filter: bool = Field(
        default=True,
        description="If True, relational filters act as a mandatory guard pruning non-matching records"
    )


class UnifiedQuery(BaseModel):
    """
    Unified query combining Relational, Graph, and Vector operations.
    Can express single-paradigm, two-paradigm, or three-paradigm queries.
    """
    query_id: str = Field(default_factory=lambda: f"q-{uuid.uuid4().hex[:8]}")
    name: str = "custom_query"
    description: str = ""
    relational: Optional[RelationalSubquery] = None
    graph: Optional[GraphSubquery] = None
    vector: Optional[VectorSubquery] = None
    fusion: FusionConfig = Field(default_factory=FusionConfig)


# =============================================================================
# Predefined Reproducible Demonstration Queries
# =============================================================================

PREDEFINED_QUERIES: Dict[str, UnifiedQuery] = {
    "1": UnifiedQuery(
        query_id="demo-1-relational",
        name="relational_track_filter",
        description="[Relational Only] Filter projects competing in 'Robotics & AI' track via SQL",
        relational=RelationalSubquery(
            table="projects",
            filters={"track": "Robotics & AI"}
        )
    ),
    "2": UnifiedQuery(
        query_id="demo-2-graph",
        name="graph_shortest_path",
        description="[Graph Only] Find shortest collaborator relationship path between participant:1 and participant:5",
        graph=GraphSubquery(
            operation="shortest_path",
            source_entity="participant:1",
            target_entity="participant:5",
            directed=False
        )
    ),
    "3": UnifiedQuery(
        query_id="demo-3-vector",
        name="vector_semantic_search",
        description="[Vector Only] Semantic similarity search for 'AI solutions for traffic congestion'",
        vector=VectorSubquery(
            text="AI solutions for traffic congestion",
            top_k=5,
            min_score=0.0
        )
    ),
    "4": UnifiedQuery(
        query_id="demo-4-relational-vector",
        name="relational_vector_hybrid",
        description="[2-Engine Hybrid] Relational filter for 'Healthcare & AI' track fused with vector search for 'pulmonary chest X-ray diagnosis'",
        relational=RelationalSubquery(
            table="projects",
            filters={"track": "Healthcare & AI"}
        ),
        vector=VectorSubquery(
            text="pulmonary chest X-ray diagnosis",
            top_k=5,
            min_score=0.0
        ),
        fusion=FusionConfig(k=60, mandatory_relational_filter=True)
    ),
    "5": UnifiedQuery(
        query_id="demo-5-three-way-unified",
        name="triquery_three_paradigm_unified",
        description="[3-Engine Unified] Relational track filter ('Robotics & AI') + Graph college affiliation ('IIT Delhi') + Vector semantic search ('autonomous drone navigation')",
        relational=RelationalSubquery(
            table="projects",
            filters={"track": "Robotics & AI"}
        ),
        graph=GraphSubquery(
            operation="college_projects",
            source_entity="IIT Delhi"
        ),
        vector=VectorSubquery(
            text="autonomous drone navigation pathfinding",
            top_k=5,
            min_score=0.0
        ),
        fusion=FusionConfig(k=60, mandatory_relational_filter=True)
    )
}
