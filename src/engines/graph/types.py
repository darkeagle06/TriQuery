"""
Graph domain types and data contracts for TriQuery Graph Engine.
Defines node types, edge types, paths, and graph traversal structures.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    COLLEGE = "college"
    HACKATHON = "hackathon"
    TEAM = "team"
    PARTICIPANT = "participant"
    PROJECT = "project"
    AWARD = "award"


class EdgeType(str, Enum):
    MEMBER_OF = "MEMBER_OF"              # (:Participant)-[:MEMBER_OF]->(:Team)
    AFFILIATED_WITH = "AFFILIATED_WITH"  # (:Team)-[:AFFILIATED_WITH]->(:College)
    ENROLLED_AT = "ENROLLED_AT"          # (:Participant)-[:ENROLLED_AT]->(:College)
    SUBMITTED = "SUBMITTED"              # (:Team)-[:SUBMITTED]->(:Project)
    COMPETED_AT = "COMPETED_AT"          # (:Project)-[:COMPETED_AT]->(:Hackathon)
    WON_AWARD = "WON_AWARD"              # (:Project)-[:WON_AWARD]->(:Award)
    PRESENTED_AT = "PRESENTED_AT"        # (:Award)-[:PRESENTED_AT]->(:Hackathon)


class GraphNode(BaseModel):
    id: str = Field(description="Unique entity ID in format 'type:id'")
    node_type: NodeType
    label: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: EdgeType
    attributes: Dict[str, Any] = Field(default_factory=dict)


class PathStep(BaseModel):
    from_node: str
    to_node: str
    edge_type: str
    direction: str = Field(description="'outgoing' (source->target) or 'incoming' (target<-source)")
    attributes: Dict[str, Any] = Field(default_factory=dict)


class PathResult(BaseModel):
    source: str
    target: str
    path: List[str] = Field(default_factory=list)
    length: int = 0
    steps: List[PathStep] = Field(default_factory=list)
    found: bool = False
    message: str = ""
