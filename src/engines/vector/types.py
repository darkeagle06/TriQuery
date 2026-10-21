"""
Domain types and data contracts for TriQuery Vector Engine.
Defines vector documents, search results, and embedding provider configurations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    """Represents a document indexed in the vector store."""
    entity_id: str = Field(description="Unique entity identifier (e.g. 'project:1')")
    text: str = Field(description="Normalized textual content that was embedded")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    text_hash: str = Field(description="MD5 hash of text to prevent unnecessary re-embedding")


class VectorSearchResult(BaseModel):
    """Represents a single nearest-neighbor search result."""
    entity_id: str
    score: float = Field(description="Cosine similarity score (0.0 to 1.0)")
    title: str = ""
    short_summary: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    rank: int = 1
