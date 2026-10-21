"""
Unit and Integration Tests for TriQuery Vector Engine (Milestone 3).

Validates:
- Embedding dimensions, output shapes, and L2 normalization
- Vector similarity index construction, stable entity IDs, and top-K search ranking
- Empty datasets, whitespace queries, missing fields, and error handling
- Document MD5 hash caching to avoid redundant embedding generation
- Deterministic offline test provider vs. statistical TF-IDF provider
- Separate live neural model test suite (conditionally skipped if package unavailable)
"""

import unittest
from unittest.mock import MagicMock
import numpy as np

from src.core.types import EngineType
from src.engines.relational.connection import DatabaseConfig, DatabaseConnectionManager
from src.engines.relational.engine import RelationalEngine
from tests.test_relational_engine import TestRelationalEngine
from src.engines.vector.engine import VectorEngine
from src.engines.vector.index import VectorIndex
from src.engines.vector.providers import (
    BaseEmbeddingProvider,
    DeterministicTestProvider,
    SentenceTransformersProvider,
    TFIDFEmbeddingProvider,
)
from src.engines.vector.types import VectorSearchResult

# Check if sentence-transformers is installed
try:
    import sentence_transformers
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


class TestVectorProviders(unittest.TestCase):
    """Tests for vector embedding provider implementations."""

    def test_deterministic_test_provider_output_dimension_and_normalization(self):
        """Validates that DeterministicTestProvider yields L2-normalized vectors of expected dimension."""
        provider = DeterministicTestProvider(dimension=64)
        self.assertEqual(provider.dimension, 64)
        self.assertFalse(provider.is_semantic)
        self.assertIn("deterministic-test", provider.model_name)

        vec = provider.embed_text("Autonomous UAV pathfinding system")
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (64,))
        self.assertEqual(vec.dtype, np.float32)

        # Vector should be unit length (L2 norm = 1.0)
        norm = float(np.linalg.norm(vec))
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_deterministic_test_provider_reproducibility(self):
        """Verifies that the same text produces identical embedding vectors across calls."""
        provider = DeterministicTestProvider(dimension=64)
        vec1 = provider.embed_text("Decentralized smart grid balancer")
        vec2 = provider.embed_text("Decentralized smart grid balancer")
        np.testing.assert_array_almost_equal(vec1, vec2)

    def test_deterministic_test_provider_empty_and_whitespace(self):
        """Validates that empty or whitespace inputs produce a zero-vector without crashing."""
        provider = DeterministicTestProvider(dimension=32)
        vec_empty = provider.embed_text("")
        vec_spaces = provider.embed_text("   \n\t  ")

        self.assertEqual(vec_empty.shape, (32,))
        self.assertEqual(float(np.linalg.norm(vec_empty)), 0.0)
        self.assertEqual(float(np.linalg.norm(vec_spaces)), 0.0)

    def test_deterministic_test_provider_batch(self):
        """Validates batch embedding generation shape and values."""
        provider = DeterministicTestProvider(dimension=48)
        texts = ["Project Alpha", "Project Beta", "Project Gamma"]
        batch = provider.embed_batch(texts)

        self.assertEqual(batch.shape, (3, 48))
        self.assertEqual(batch.dtype, np.float32)
        for i in range(3):
            self.assertAlmostEqual(float(np.linalg.norm(batch[i])), 1.0, places=4)

        # Empty batch returns (0, D) array
        empty_batch = provider.embed_batch([])
        self.assertEqual(empty_batch.shape, (0, 48))

    def test_tfidf_provider_vocabulary_and_normalization(self):
        """Validates that TFIDFEmbeddingProvider builds vocabulary and produces normalized vectors."""
        corpus = [
            "Autonomous drone pathfinding and computer vision in disaster zones.",
            "Zero-knowledge health vault for electronic medical records with zk-SNARKs.",
            "Deep learning diagnostic assistant for pulmonary chest X-ray pathology."
        ]
        provider = TFIDFEmbeddingProvider(max_features=256)
        provider.fit_corpus(corpus)

        self.assertFalse(provider.is_semantic)
        self.assertGreater(provider.dimension, 0)
        self.assertLessEqual(provider.dimension, 256)

        vec = provider.embed_text("drone computer vision")
        self.assertEqual(vec.shape, (provider.dimension,))
        norm = float(np.linalg.norm(vec))
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_tfidf_provider_batch(self):
        """Validates TF-IDF batch transform."""
        corpus = ["Alpha machine learning", "Beta blockchain smart contracts"]
        provider = TFIDFEmbeddingProvider()
        provider.fit_corpus(corpus)

        batch = provider.embed_batch(["Alpha model", "Beta contracts"])
        self.assertEqual(batch.shape[0], 2)
        self.assertEqual(batch.shape[1], provider.dimension)

    def test_sentence_transformers_missing_error(self):
        """Verifies that SentenceTransformersProvider raises ModuleNotFoundError if not installed."""
        if not HAS_SENTENCE_TRANSFORMERS:
            with self.assertRaises(ModuleNotFoundError) as ctx:
                SentenceTransformersProvider()
            self.assertIn("sentence-transformers", str(ctx.exception))


class TestVectorIndex(unittest.TestCase):
    """Tests for VectorIndex in-memory similarity store."""

    def setUp(self):
        self.index = VectorIndex(dimension=4)

    def test_index_initialization_and_properties(self):
        """Validates empty index state."""
        self.assertEqual(self.index.size, 0)
        self.assertEqual(self.index.dimension, 4)
        self.assertIsNone(self.index.get_vector("project:1"))
        self.assertIsNone(self.index.get_metadata("project:1"))

    def test_index_add_and_retrieval(self):
        """Validates adding a vector and retrieving stored vector and metadata."""
        vec = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        self.index.add("project:1", vec, metadata={"title": "Drone Nav"})

        self.assertEqual(self.index.size, 1)
        stored_vec = self.index.get_vector("project:1")
        self.assertIsNotNone(stored_vec)
        np.testing.assert_array_almost_equal(stored_vec, vec)
        self.assertEqual(self.index.get_metadata("project:1")["title"], "Drone Nav")

    def test_index_dimension_mismatch_error(self):
        """Validates that adding an inconsistent vector dimension raises ValueError."""
        invalid_vec = np.array([1.0, 0.0], dtype=np.float32)
        with self.assertRaises(ValueError):
            self.index.add("project:bad", invalid_vec)

    def test_index_duplicate_entity_id_update(self):
        """Validates that re-adding an entity ID updates the vector in place without duplicate records."""
        vec1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)

        self.index.add("project:1", vec1, metadata={"version": 1})
        self.assertEqual(self.index.size, 1)

        self.index.add("project:1", vec2, metadata={"version": 2})
        self.assertEqual(self.index.size, 1)
        np.testing.assert_array_almost_equal(self.index.get_vector("project:1"), vec2)
        self.assertEqual(self.index.get_metadata("project:1")["version"], 2)

    def test_index_search_top_k_and_ordering(self):
        """Validates that nearest-neighbor search correctly ranks by cosine similarity."""
        # 3 orthogonal vectors
        v1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([0.8, 0.6, 0.0, 0.0], dtype=np.float32)  # cos ~ 0.8 with v1
        v3 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)  # cos = 0.0 with v1

        self.index.add("project:1", v1, metadata={"title": "Doc 1"})
        self.index.add("project:2", v2, metadata={"title": "Doc 2"})
        self.index.add("project:3", v3, metadata={"title": "Doc 3"})

        query = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        results = self.index.search(query, top_k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].entity_id, "project:1")
        self.assertAlmostEqual(results[0].score, 1.0, places=3)
        self.assertEqual(results[0].rank, 1)

        self.assertEqual(results[1].entity_id, "project:2")
        self.assertAlmostEqual(results[1].score, 0.8, places=3)
        self.assertEqual(results[1].rank, 2)

    def test_index_search_min_score_filter(self):
        """Validates that search filters out results below min_score."""
        v1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)

        self.index.add("project:1", v1)
        self.index.add("project:2", v2)

        query = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        results = self.index.search(query, top_k=5, min_score=0.5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entity_id, "project:1")

    def test_index_empty_search(self):
        """Validates search on empty index returns empty list."""
        query = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        results = self.index.search(query)
        self.assertEqual(results, [])

    def test_index_clear(self):
        """Validates clear resets all internal state."""
        self.index.add("project:1", np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32))
        self.assertEqual(self.index.size, 1)
        self.index.clear()
        self.assertEqual(self.index.size, 0)
        self.assertIsNone(self.index.get_vector("project:1"))


class TestVectorEngine(unittest.TestCase):
    """Tests for VectorEngine end-to-end integration and operations."""

    @classmethod
    def setUpClass(cls):
        """Initializes a shared standalone SQLite RelationalEngine with seed data."""
        cls.db_config = DatabaseConfig(sqlite_fallback=True, sqlite_path=":memory:")
        cls.conn_mgr = DatabaseConnectionManager(cls.db_config)
        cls.rel_engine = RelationalEngine(cls.conn_mgr)

        TestRelationalEngine._init_test_schema.__func__(cls)
        TestRelationalEngine._load_test_seed_data.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        """Cleans up relational test database connection."""
        if hasattr(cls, "conn_mgr") and cls.conn_mgr:
            cls.conn_mgr.close()

    def setUp(self):
        # Use DeterministicTestProvider for fast, reliable unit tests
        self.provider = DeterministicTestProvider(dimension=64)
        self.engine = VectorEngine(
            relational_engine=self.rel_engine,
            provider=self.provider,
            auto_build=True
        )

    def test_vector_engine_health_and_type(self):
        """Validates engine type and health status."""
        self.assertEqual(self.engine.engine_type, EngineType.VECTOR)
        self.assertTrue(self.engine.is_healthy())

    def test_vector_engine_build_from_relational(self):
        """Validates that 6 project records from relational store are indexed."""
        self.assertEqual(self.engine.document_count, 6)
        self.assertEqual(self.engine.index.dimension, 64)

        # Verify stable entity ID mapping
        for pid in range(1, 7):
            eid = f"project:{pid}"
            meta = self.engine.index.get_metadata(eid)
            self.assertIsNotNone(meta)
            self.assertEqual(meta["project_id"], pid)
            self.assertTrue(len(meta["title"]) > 0)
            self.assertTrue(len(meta["track"]) > 0)

    def test_vector_engine_search_execution(self):
        """Validates top-K search execution and EngineResult structure."""
        result = self.engine.search("Autonomous drone navigation in GPS-denied environments", top_k=3)

        self.assertTrue(result.success)
        self.assertEqual(result.engine, EngineType.VECTOR)
        self.assertLessEqual(len(result.data), 3)

        meta = result.metadata
        self.assertIsNotNone(meta)
        self.assertGreater(meta.execution_time_ms, 0.0)
        self.assertEqual(meta.record_count, len(result.data))

        # Check fields of top result
        top_match = result.data[0]
        self.assertIn("entity_id", top_match)
        self.assertIn("score", top_match)
        self.assertIn("title", top_match)
        self.assertIn("track", top_match)
        self.assertIn("short_summary", top_match)
        self.assertEqual(top_match["rank"], 1)

    def test_vector_engine_empty_query_handling(self):
        """Validates that empty or whitespace query returns failure without crashing."""
        res_empty = self.engine.search("")
        self.assertFalse(res_empty.success)
        self.assertEqual(res_empty.data, [])
        self.assertIn("Empty query", res_empty.error)

        res_spaces = self.engine.search("     ")
        self.assertFalse(res_spaces.success)

    def test_vector_engine_hash_caching_avoids_re_embedding(self):
        """Verifies that calling build_from_relational() when records haven't changed does not re-embed."""
        build_info = self.engine.build_from_relational(force=False)
        self.assertEqual(build_info["new_embeddings_generated"], 0)
        self.assertEqual(build_info["indexed_count"], 6)

    def test_vector_engine_force_rebuild(self):
        """Verifies that force=True generates new embeddings for all documents."""
        build_info = self.engine.build_from_relational(force=True)
        self.assertEqual(build_info["new_embeddings_generated"], 6)
        self.assertEqual(build_info["indexed_count"], 6)

    def test_vector_engine_empty_dataset_handling(self):
        """Validates behavior when relational database has zero projects."""
        mock_conn = MagicMock()
        mock_conn.execute_query.return_value = []
        mock_rel = RelationalEngine(mock_conn)

        empty_engine = VectorEngine(relational_engine=mock_rel, provider=self.provider, auto_build=True)
        self.assertEqual(empty_engine.document_count, 0)

        res = empty_engine.search("drone pathfinding")
        self.assertFalse(res.success)
        self.assertIn("empty", res.error.lower())

    def test_vector_engine_explain(self):
        """Validates explain output containing time/space complexity and viva justifications."""
        info = self.engine.explain("AI solutions for traffic congestion")

        self.assertEqual(info["engine"], "vector")
        self.assertEqual(info["indexed_documents"], 6)
        self.assertEqual(info["vector_dimension"], 64)
        self.assertIn("O(N * D)", info["indexing_complexity"])
        self.assertIn("comparison_with_sql_like", info)
        self.assertIn("continuous metric space", info["comparison_with_sql_like"])

    def test_vector_engine_with_tfidf_provider(self):
        """Validates VectorEngine end-to-end when using Scikit-Learn TF-IDF provider."""
        tfidf_provider = TFIDFEmbeddingProvider(max_features=128)
        engine = VectorEngine(relational_engine=self.rel_engine, provider=tfidf_provider, auto_build=True)

        self.assertEqual(engine.document_count, 6)
        self.assertFalse(engine.provider.is_semantic)

        # Search for exact vocabulary terms from AeroVision project
        res = engine.search("Autonomous drone pathfinding visual SLAM", top_k=3)
        self.assertTrue(res.success)
        self.assertGreater(len(res.data), 0)
        # AeroVision should rank #1 for its exact keywords
        self.assertEqual(res.data[0]["entity_id"], "project:1")
        self.assertEqual(res.data[0]["title"], "AeroVision Autonomous Drone Pathfinder")
        self.assertGreater(res.data[0]["score"], 0.1)


class TestLiveSentenceTransformersModel(unittest.TestCase):
    """
    Live neural model integration tests.
    Conditionally skipped if sentence-transformers is not installed in the environment.
    """

    @unittest.skipUnless(
        HAS_SENTENCE_TRANSFORMERS,
        "Sentence-Transformers not installed. To run live neural tests: pip install sentence-transformers"
    )
    def test_live_sentence_transformers_semantic_search(self):
        """Tests dense neural semantic similarity using all-MiniLM-L6-v2."""
        provider = SentenceTransformersProvider(model_name="all-MiniLM-L6-v2")
        self.assertTrue(provider.is_semantic)
        self.assertEqual(provider.dimension, 384)

        # Test semantic proximity without exact keyword overlap
        v_uav = provider.embed_text("quadcopter aerial navigation in obstacle environments")
        v_drone = provider.embed_text("Autonomous Drone Pathfinder for UAVs in disaster zones")
        v_unrelated = provider.embed_text("Credit card fraud detection algorithm")

        sim_related = float(np.dot(v_uav, v_drone))
        sim_unrelated = float(np.dot(v_uav, v_unrelated))

        self.assertGreater(sim_related, sim_unrelated)
        self.assertGreater(sim_related, 0.4)


if __name__ == "__main__":
    unittest.main()
