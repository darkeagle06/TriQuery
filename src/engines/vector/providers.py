"""
Embedding providers for TriQuery Vector Engine.
Supports Sentence-Transformers (dense semantic embeddings),
Scikit-Learn TF-IDF (statistical lexical vector space),
and DeterministicTestProvider (reproducible offline test backend).
"""

import hashlib
import re
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np


class BaseEmbeddingProvider(ABC):
    """
    Abstract interface for text embedding generation.
    Enforces consistent vector dimensions, normalization, and semantic labeling.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the dimensionality of the generated embedding vectors."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name or identifier of the underlying model/algorithm."""
        pass

    @property
    @abstractmethod
    def is_semantic(self) -> bool:
        """True if provider uses true deep neural semantic embeddings, False for lexical/test."""
        pass

    @property
    def description(self) -> str:
        semantic_tag = "Neural Semantic" if self.is_semantic else "Non-Semantic (Lexical / Test)"
        return f"{self.model_name} [{semantic_tag}, dim={self.dimension}]"

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Generates a 1D L2-normalized float32 embedding vector for a single text."""
        pass

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generates a 2D float32 array (N, D) of embeddings for a list of texts."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        vectors = [self.embed_text(t) for t in texts]
        return np.vstack(vectors).astype(np.float32)


class SentenceTransformersProvider(BaseEmbeddingProvider):
    """
    Dense semantic embedding provider using Sentence-Transformers.
    Uses models like 'all-MiniLM-L6-v2' (384-dimensional).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None
        self._dimension = 384
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
        except ImportError as exc:
            raise ModuleNotFoundError(
                "The 'sentence-transformers' package is not installed in the current environment.\n"
                "To enable real dense neural embeddings, install it via: pip install sentence-transformers\n"
                "Alternatively, TriQuery automatically falls back to Scikit-Learn TF-IDF or DeterministicTestProvider."
            ) from exc

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return f"sentence-transformers/{self._model_name}"

    @property
    def is_semantic(self) -> bool:
        return True

    def embed_text(self, text: str) -> np.ndarray:
        clean_text = text.strip() if text else "empty"
        vec = self._model.encode(clean_text, normalize_embeddings=True, convert_to_numpy=True)
        return vec.astype(np.float32)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        clean_texts = [t.strip() if t else "empty" for t in texts]
        if not clean_texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        vecs = self._model.encode(clean_texts, normalize_embeddings=True, convert_to_numpy=True)
        return vecs.astype(np.float32)


class TFIDFEmbeddingProvider(BaseEmbeddingProvider):
    """
    Statistical lexical embedding provider using Scikit-Learn TfidfVectorizer.
    Computes L2-normalized term-frequency inverse-document-frequency vectors.
    Does not capture deep semantic connotations, but produces exact vocabulary match vectors.
    """

    def __init__(self, max_features: int = 512):
        self._max_features = max_features
        self._vectorizer = None
        self._corpus: List[str] = []
        self._is_fitted = False

    def fit_corpus(self, corpus: List[str]):
        """Fits the vocabulary and IDF weights on the available corpus."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        clean_corpus = [t.strip() for t in corpus if t and t.strip()]
        if not clean_corpus:
            clean_corpus = ["default fallback document"]

        self._vectorizer = TfidfVectorizer(
            max_features=self._max_features,
            stop_words="english",
            sublinear_tf=True,
            norm="l2"
        )
        self._vectorizer.fit(clean_corpus)
        self._corpus = clean_corpus
        self._is_fitted = True

    @property
    def dimension(self) -> int:
        if self._vectorizer and hasattr(self._vectorizer, "vocabulary_"):
            return len(self._vectorizer.vocabulary_)
        return self._max_features

    @property
    def model_name(self) -> str:
        return "sklearn-tfidf-vectorizer"

    @property
    def is_semantic(self) -> bool:
        return False

    def embed_text(self, text: str) -> np.ndarray:
        if not self._is_fitted:
            self.fit_corpus([text])

        clean_text = text.strip() if text else "empty"
        sparse_vec = self._vectorizer.transform([clean_text])
        dense_vec = sparse_vec.toarray()[0].astype(np.float32)

        # Ensure L2 normalized
        norm = np.linalg.norm(dense_vec)
        if norm > 1e-6:
            dense_vec = dense_vec / norm
        return dense_vec

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        if not self._is_fitted:
            self.fit_corpus(texts)

        clean_texts = [t.strip() if t else "empty" for t in texts]
        sparse_matrix = self._vectorizer.transform(clean_texts)
        dense_matrix = sparse_matrix.toarray().astype(np.float32)

        # L2 normalize rows
        norms = np.linalg.norm(dense_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return dense_matrix / norms


class DeterministicTestProvider(BaseEmbeddingProvider):
    """
    Deterministic pseudo-random projection embedding provider for unit tests.
    Generates predictable, fixed-dimension vectors based on hashing text tokens.
    Labeled explicitly as a test-only substitute (is_semantic = False).
    """

    def __init__(self, dimension: int = 64):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "deterministic-test-hash-projector"

    @property
    def is_semantic(self) -> bool:
        return False

    def embed_text(self, text: str) -> np.ndarray:
        clean = (text or "").strip().lower()
        if not clean:
            return np.zeros(self._dim, dtype=np.float32)

        # Tokenize words
        tokens = re.findall(r"\w+", clean)
        vec = np.zeros(self._dim, dtype=np.float64)

        # Hash whole text for global base
        h_full = int(hashlib.md5(clean.encode("utf-8")).hexdigest(), 16)
        rng_full = np.random.RandomState(h_full % (2**32))
        vec += rng_full.randn(self._dim) * 0.5

        # Hash individual tokens for token overlap similarity
        for token in tokens:
            h_tok = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            rng_tok = np.random.RandomState(h_tok % (2**32))
            vec += rng_tok.randn(self._dim)

        # L2 Normalize
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        return vec.astype(np.float32)
