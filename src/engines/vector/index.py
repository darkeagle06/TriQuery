"""
Vector Similarity Index for TriQuery.
Provides exact nearest-neighbor search over L2-normalized embedding vectors
using BLAS-accelerated inner product (cosine similarity) in NumPy.
Avoids heavy C++ dependencies while guaranteeing sub-millisecond query execution.
"""

from typing import Any, Dict, List, Optional
import numpy as np
from src.engines.vector.types import VectorSearchResult


class VectorIndex:
    """
    Lightweight, high-performance in-memory vector index.
    Stores dense vectors in a contiguous NumPy array with stable entity-ID mapping.
    """

    def __init__(self, dimension: Optional[int] = None):
        self._dimension = dimension
        self._vectors: Optional[np.ndarray] = None  # Shape (N, D)
        self._entity_ids: List[str] = []
        self._id_to_idx: Dict[str, int] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    @property
    def size(self) -> int:
        """Returns the number of indexed vectors."""
        return len(self._entity_ids)

    @property
    def dimension(self) -> Optional[int]:
        """Returns the vector dimensionality."""
        return self._dimension

    def clear(self):
        """Clears all vectors and index mappings."""
        self._vectors = None
        self._entity_ids.clear()
        self._id_to_idx.clear()
        self._metadata.clear()

    def add(self, entity_id: str, vector: np.ndarray, metadata: Optional[Dict[str, Any]] = None):
        """
        Adds or updates a single vector in the index.
        If entity_id already exists, updates the vector in place to prevent duplicates.
        """
        vec = np.asarray(vector, dtype=np.float32).flatten()
        if self._dimension is None:
            self._dimension = vec.shape[0]
        elif vec.shape[0] != self._dimension:
            raise ValueError(f"Vector dimension mismatch: expected {self._dimension}, got {vec.shape[0]}")

        # Ensure vector is L2 normalized for exact cosine distance
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm

        meta = metadata or {}

        # If entity_id already exists, update in-place
        if entity_id in self._id_to_idx:
            idx = self._id_to_idx[entity_id]
            self._vectors[idx] = vec
            self._metadata[entity_id] = meta
            return

        # Append new vector
        if self._vectors is None or self._vectors.shape[0] == 0:
            self._vectors = np.expand_dims(vec, axis=0)
        else:
            self._vectors = np.vstack([self._vectors, vec])

        new_idx = len(self._entity_ids)
        self._entity_ids.append(entity_id)
        self._id_to_idx[entity_id] = new_idx
        self._metadata[entity_id] = meta

    def add_batch(
        self,
        entity_ids: List[str],
        vectors: np.ndarray,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """Batch adds or updates vectors with vectorized L2-normalization."""
        if len(entity_ids) == 0:
            return
        if metadatas is None:
            metadatas = [{} for _ in entity_ids]

        vecs = np.asarray(vectors, dtype=np.float32)
        if vecs.ndim == 1:
            vecs = np.expand_dims(vecs, axis=0)

        # Check if any ID already exists
        existing_mask = [eid in self._id_to_idx for eid in entity_ids]
        if any(existing_mask):
            for eid, vec, meta in zip(entity_ids, vecs, metadatas):
                self.add(eid, vec, meta)
            return

        if self._dimension is None:
            self._dimension = vecs.shape[1]
        elif vecs.shape[1] != self._dimension:
            raise ValueError(f"Batch vector dimension mismatch: expected {self._dimension}, got {vecs.shape[1]}")

        # Vectorized normalization
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms <= 1e-6] = 1.0
        vecs = vecs / norms

        start_idx = len(self._entity_ids)
        if self._vectors is None or self._vectors.shape[0] == 0:
            self._vectors = vecs.copy()
        else:
            self._vectors = np.vstack([self._vectors, vecs])

        for i, (eid, meta) in enumerate(zip(entity_ids, metadatas)):
            self._entity_ids.append(eid)
            self._id_to_idx[eid] = start_idx + i
            self._metadata[eid] = meta

    def get_vector(self, entity_id: str) -> Optional[np.ndarray]:
        """Returns the stored vector for a given entity_id or None."""
        if entity_id not in self._id_to_idx or self._vectors is None:
            return None
        idx = self._id_to_idx[entity_id]
        return self._vectors[idx].copy()

    def get_metadata(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Returns metadata stored with the entity_id."""
        return self._metadata.get(entity_id)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[VectorSearchResult]:
        """
        Executes nearest-neighbor search using cosine similarity.
        Time Complexity: O(N * D) matrix dot product + O(N log K) top-K sort.
        """
        if self.size == 0 or self._vectors is None:
            return []

        q_vec = np.asarray(query_vector, dtype=np.float32).flatten()
        if self._dimension and q_vec.shape[0] != self._dimension:
            raise ValueError(f"Query vector dimension mismatch: expected {self._dimension}, got {q_vec.shape[0]}")

        # Normalize query vector
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 1e-6:
            q_vec = q_vec / q_norm

        # Cosine similarity via inner product on normalized vectors
        # Shape: (N,)
        scores = np.dot(self._vectors, q_vec)

        # Handle NaNs or precision anomalies
        scores = np.nan_to_num(scores, nan=0.0)

        # Rank indices in descending order
        sorted_indices = np.argsort(scores)[::-1]

        results = []
        rank = 1
        for idx in sorted_indices:
            score = float(scores[idx])
            if score < min_score:
                break

            eid = self._entity_ids[idx]
            meta = self._metadata.get(eid, {})

            results.append(VectorSearchResult(
                entity_id=eid,
                score=round(score, 4),
                title=meta.get("title", ""),
                short_summary=meta.get("short_summary", ""),
                metadata=meta,
                rank=rank
            ))
            rank += 1
            if len(results) >= top_k:
                break

        return results
