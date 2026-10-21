"""
Pydantic Request and Response Schemas for TriQuery API.
Enforces strict input validation, data integrity, and sanitized outputs.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.query import UnifiedQuery


# =============================================================================
# Health & Status Schemas
# =============================================================================

class GraphHealthInfo(BaseModel):
    node_count: int
    edge_count: int
    is_healthy: bool


class VectorHealthInfo(BaseModel):
    provider: str
    dimension: Optional[int] = None
    document_count: int
    is_semantic: bool


class HealthResponse(BaseModel):
    status: str = Field(description="'healthy' when MySQL and all engines are online, otherwise 'degraded' or 'unhealthy'")
    is_healthy: bool
    backend: str = Field(description="Active relational backend, e.g. 'MySQL 8.x' or 'SQLite (isolated mode)'")
    database_name: str
    host: str
    port: int
    table_counts: Dict[str, int]
    graph: GraphHealthInfo
    vector: VectorHealthInfo


# =============================================================================
# Presets Schemas
# =============================================================================

class PresetItem(BaseModel):
    preset_id: str
    name: str
    description: str
    target_paradigms: List[str]
    query: UnifiedQuery


class PresetsResponse(BaseModel):
    total_presets: int
    presets: List[PresetItem]


# =============================================================================
# Relational Schemas
# =============================================================================

class TableColumnSchema(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool
    default: Optional[str] = None


class ForeignKeySchema(BaseModel):
    column: str
    referenced_table: str
    referenced_column: str


class TableSchema(BaseModel):
    table_name: str
    row_count: int
    columns: List[TableColumnSchema]
    foreign_keys: List[ForeignKeySchema] = Field(default_factory=list)


class TablesResponse(BaseModel):
    database: str
    table_count: int
    tables: List[TableSchema]


class ProjectsResponse(BaseModel):
    success: bool
    count: int
    data: List[Dict[str, Any]]
    execution_time_ms: float
    notes: List[str] = Field(default_factory=list)


# =============================================================================
# Graph Schemas
# =============================================================================

class GraphNodeItem(BaseModel):
    id: str
    label: str
    node_type: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeItem(BaseModel):
    source: str
    target: str
    edge_type: str
    direction: str = "directed"
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GraphTopologyResponse(BaseModel):
    node_count: int
    edge_count: int
    node_types: Dict[str, int]
    edge_types: Dict[str, int]
    nodes: List[GraphNodeItem]
    edges: List[GraphEdgeItem]


class GraphPathRequest(BaseModel):
    source: str = Field(min_length=1, max_length=150, description="Source node identifier (e.g. 'participant:1' or 'IIT Delhi')")
    target: str = Field(min_length=1, max_length=150, description="Target node identifier (e.g. 'participant:5' or 'VeriMed')")
    directed: bool = Field(default=False, description="Whether to restrict traversal to directed edges")


class GraphPathResponse(BaseModel):
    found: bool
    source: str
    target: str
    length: int
    path: List[str]
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    message: str


# =============================================================================
# Vector Schemas
# =============================================================================

class VectorSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of candidates to return (1-50)")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum cosine similarity cutoff (0.0-1.0)")


class VectorSearchItem(BaseModel):
    rank: int
    score: float
    entity_id: str
    project_id: Optional[int] = None
    title: str
    track: Optional[str] = None
    short_summary: Optional[str] = None
    tech_stack: Optional[str] = None


class VectorSearchResponse(BaseModel):
    success: bool
    count: int
    query: str
    execution_time_ms: float
    provider: str
    results: List[VectorSearchItem]
    notes: List[str] = Field(default_factory=list)


# =============================================================================
# Error Schemas
# =============================================================================

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
