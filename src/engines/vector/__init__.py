"""
TriQuery Vector Engine Package.
Provides vector embedding generation, in-memory cosine indexing, and semantic similarity search.
"""

from src.engines.vector.engine import VectorEngine
from src.engines.vector.index import VectorIndex
from src.engines.vector.providers import (
    BaseEmbeddingProvider,
    DeterministicTestProvider,
    SentenceTransformersProvider,
    TFIDFEmbeddingProvider,
)
from src.engines.vector.types import VectorDocument, VectorSearchResult

__all__ = [
    "VectorEngine",
    "VectorIndex",
    "VectorDocument",
    "VectorSearchResult",
    "BaseEmbeddingProvider",
    "SentenceTransformersProvider",
    "TFIDFEmbeddingProvider",
    "DeterministicTestProvider",
]
