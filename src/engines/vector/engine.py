"""
Vector Engine for TriQuery.
Provides semantic and lexical similarity search over hackathon project descriptions.
Integrates with RelationalEngine for data loading and returns stable entity IDs
compatible with downstream result fusion and explainability.
"""

import hashlib
import time
from typing import Any, Dict, List, Optional, Union
import numpy as np

from src.config import config
from src.core.types import EngineExecutionMetadata, EngineResult, EngineType
from src.engines.base import BaseEngine
from src.engines.relational.engine import RelationalEngine
from src.engines.vector.index import VectorIndex
from src.engines.vector.providers import (
    BaseEmbeddingProvider,
    DeterministicTestProvider,
    SentenceTransformersProvider,
    TFIDFEmbeddingProvider,
)
from src.engines.vector.types import VectorDocument, VectorSearchResult


class VectorEngine(BaseEngine):
    """
    TriQuery Vector Engine.
    Coordinates embedding generation, in-memory vector indexing, and nearest-neighbor search.
    Supports Sentence-Transformers, Scikit-Learn TF-IDF, and deterministic test backends.
    """

    def __init__(
        self,
        relational_engine: Optional[RelationalEngine] = None,
        provider: Optional[BaseEmbeddingProvider] = None,
        auto_build: bool = True
    ):
        self.relational_engine = relational_engine or RelationalEngine()
        self.provider = provider or self._select_default_provider()
        self.index = VectorIndex(dimension=self.provider.dimension if hasattr(self.provider, "dimension") else None)
        self._doc_hashes: Dict[str, str] = {}
        self._last_built_at: Optional[float] = None

        if auto_build:
            self.build_from_relational()

    @property
    def engine_type(self) -> EngineType:
        return EngineType.VECTOR

    @property
    def document_count(self) -> int:
        return self.index.size

    def is_healthy(self) -> bool:
        """Returns True if index is functional and provider is initialized."""
        return self.provider is not None and self.index is not None

    def _select_default_provider(self) -> BaseEmbeddingProvider:
        """Selects provider based on environment configuration with safe fallbacks."""
        backend = config.vector.backend.lower()

        if backend == "sentence_transformer":
            try:
                return SentenceTransformersProvider()
            except Exception:
                # Graceful fallback to TF-IDF if sentence-transformers is missing
                return TFIDFEmbeddingProvider()
        elif backend == "deterministic" or backend == "test":
            return DeterministicTestProvider()

        # Default: TF-IDF provider (uses pre-installed Scikit-Learn)
        return TFIDFEmbeddingProvider()

    # -------------------------------------------------------------------------
    # Ingestion & Index Construction
    # -------------------------------------------------------------------------

    def build_from_relational(self, force: bool = False) -> Dict[str, Any]:
        """
        Loads project records from RelationalEngine and updates the vector index.
        Uses MD5 hashing to avoid re-embedding documents whose text has not changed.
        """
        start_time = time.perf_counter()

        sql = """
            SELECT project_id, title, track, short_summary, description, tech_stack
            FROM projects
            ORDER BY project_id ASC
        """
        records = self.relational_engine.conn_mgr.execute_query(sql)

        if not records:
            self.index.clear()
            self._doc_hashes.clear()
            return {"indexed_count": 0, "duration_ms": 0.0, "status": "empty"}

        texts_to_embed = []
        entity_ids = []
        metadatas = []

        # Prepare corpus for TF-IDF if provider requires corpus fitting
        full_corpus = []
        for r in records:
            doc_text = self._prepare_search_text(r)
            full_corpus.append(doc_text)

        if isinstance(self.provider, TFIDFEmbeddingProvider):
            self.provider.fit_corpus(full_corpus)
            # Reinitialize index dimension to match fitted vocabulary size
            if self.index.dimension != self.provider.dimension:
                self.index = VectorIndex(dimension=self.provider.dimension)
                self._doc_hashes.clear()

        for r, doc_text in zip(records, full_corpus):
            eid = f"project:{r['project_id']}"
            text_hash = hashlib.md5(doc_text.encode("utf-8")).hexdigest()

            # Skip re-embedding if text hasn't changed and not forced
            if not force and eid in self._doc_hashes and self._doc_hashes[eid] == text_hash:
                continue

            entity_ids.append(eid)
            texts_to_embed.append(doc_text)
            self._doc_hashes[eid] = text_hash
            metadatas.append({
                "project_id": r["project_id"],
                "title": r["title"],
                "track": r["track"],
                "short_summary": r["short_summary"],
                "tech_stack": r.get("tech_stack", "")
            })

        # Batch embed only new or modified texts
        if texts_to_embed:
            vectors = self.provider.embed_batch(texts_to_embed)
            self.index.add_batch(entity_ids, vectors, metadatas)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        self._last_built_at = time.time()

        return {
            "indexed_count": self.index.size,
            "new_embeddings_generated": len(texts_to_embed),
            "vector_dimension": self.index.dimension,
            "provider": self.provider.description,
            "duration_ms": round(duration_ms, 3)
        }

    @staticmethod
    def _prepare_search_text(record: Dict[str, Any]) -> str:
        """Normalizes and combines project fields into a dense textual search document."""
        title = (record.get("title") or "").strip()
        track = (record.get("track") or "").strip()
        summary = (record.get("short_summary") or "").strip()
        desc = (record.get("description") or "").strip()
        stack = (record.get("tech_stack") or "").strip()

        return f"Project: {title}. Track: {track}. Stack: {stack}. Summary: {summary}. Details: {desc}"

    # -------------------------------------------------------------------------
    # Search & Nearest Neighbors
    # -------------------------------------------------------------------------

    def search(
        self,
        query_text: str,
        top_k: int = 5,
        min_score: float = 0.0
    ) -> EngineResult:
        """
        Executes top-K similarity search for a natural language query.
        Returns standardized EngineResult with cosine similarity scores and metadata.
        """
        start_time = time.perf_counter()
        clean_query = (query_text or "").strip()

        if not clean_query:
            return self._empty_result("Empty query provided", start_time, query_text)

        if self.index.size == 0:
            return self._empty_result("Vector index is empty", start_time, query_text)

        # Generate query vector
        query_vec = self.provider.embed_text(clean_query)

        # Search index
        raw_results = self.index.search(query_vec, top_k=top_k, min_score=min_score)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        data = []
        for r in raw_results:
            data.append({
                "entity_id": r.entity_id,
                "project_id": r.metadata.get("project_id"),
                "score": r.score,
                "title": r.title,
                "track": r.metadata.get("track"),
                "short_summary": r.short_summary,
                "tech_stack": r.metadata.get("tech_stack", ""),
                "rank": r.rank
            })

        notes = [
            f"Provider: {self.provider.description}",
            f"Semantic: {'Yes (Dense Embeddings)' if self.provider.is_semantic else 'No (Lexical / Test Vector Space)'}",
            f"Evaluated {self.index.size} vectors in {round(duration_ms, 3)} ms"
        ]

        metadata = EngineExecutionMetadata(
            engine=self.engine_type,
            execution_time_ms=round(duration_ms, 3),
            record_count=len(data),
            query_executed=f"vector_search('{clean_query}', top_k={top_k})",
            notes=notes
        )

        return EngineResult(
            engine=self.engine_type,
            success=True,
            data=data,
            metadata=metadata
        )

    # -------------------------------------------------------------------------
    # BaseEngine Implementation
    # -------------------------------------------------------------------------

    def execute(self, query: Any, **kwargs) -> EngineResult:
        """Executes a search query from string or parameter dict."""
        top_k = kwargs.get("top_k", config.vector.top_k)
        min_score = kwargs.get("min_score", 0.0)

        if isinstance(query, dict):
            q_text = query.get("query", "")
            top_k = query.get("top_k", top_k)
            min_score = query.get("min_score", min_score)
        else:
            q_text = str(query)

        return self.search(q_text, top_k=top_k, min_score=min_score)

    def explain(self, query: Any, **kwargs) -> Dict[str, Any]:
        """
        Explains the vector search process, complexity, and algorithmic justification.
        Crucial for viva defense contrasting semantic similarity vs. SQL LIKE matching.
        """
        n = self.index.size
        d = self.index.dimension or 0

        return {
            "engine": "vector",
            "provider": self.provider.description,
            "is_semantic": self.provider.is_semantic,
            "vector_dimension": d,
            "indexed_documents": n,
            "indexing_complexity": f"O(N * D) = O({n} * {d})",
            "search_complexity": f"O(D) [embed] + O(N * D) [cosine dot-product] + O(N log K) [top-K]",
            "space_complexity": f"O(N * D) = {n * d * 4} bytes in float32 matrix",
            "comparison_with_sql_like": (
                "SQL LIKE '%query%' only detects exact substring matches and fails on synonyms, "
                "paraphrases, or conceptual matches (e.g. 'drone pathfinding' vs. 'autonomous UAV navigation'). "
                "The Vector Engine projects text into a continuous metric space where geometric closeness "
                "represents conceptual relevance."
            )
        }

    def _empty_result(self, reason: str, start_time: float, query_text: str) -> EngineResult:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return EngineResult(
            engine=self.engine_type,
            success=False,
            data=[],
            metadata=EngineExecutionMetadata(
                engine=self.engine_type,
                execution_time_ms=round(duration_ms, 3),
                record_count=0,
                query_executed=f"vector_search('{query_text}')",
                notes=[reason, f"Provider: {self.provider.description}"]
            ),
            error=reason
        )
