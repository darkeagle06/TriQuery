# TriQuery: Explainable Multi-Paradigm Query Engine

TriQuery is an explainable query engine designed for college DBMS evaluation, unifying **Relational (MySQL 8.x)**, **Graph (NetworkX)**, and **Vector (Similarity Search)** data paradigms over a shared hackathon benchmark corpus.

---

## 1. Project Overview & Architecture

TriQuery divides responsibilities across lightweight, decoupled modules to avoid monolithic coupling:

```
TriQuery/
├── database/
│   ├── schema.sql            # MySQL 8.x DDL: 3NF tables, FK constraints & B-Tree indexes
│   ├── seed_data.sql         # Reproducible SQL seed dataset (Hackathons, Teams, Projects)
│   ├── seed_data.json        # Normalized JSON representation for the ingestion pipeline
│   ├── SETUP.md              # Detailed MySQL 8.x setup & troubleshooting instructions
│   └── triquery_local.db     # Standalone local database file for offline CLI execution
├── src/
│   ├── config.py             # Environment configuration (never hardcodes credentials)
│   ├── core/
│   │   └── types.py          # Strict contracts: QueryPlan, EngineResult, UnifiedRecord, Explanation
│   ├── engines/
│   │   ├── base.py           # Abstract BaseEngine interface
│   │   ├── relational/       # Relational Engine (MySQL 8.x + isolated test runner)
│   │   │   ├── connection.py # Connection manager, ACID transactions & dialect handler
│   │   │   ├── engine.py     # Relational algebra, multi-table joins & EXPLAIN inspection
│   │   │   └── setup_db.py   # Automated schema creation & seed population utility
│   │   ├── graph/            # Graph Engine (NetworkX) - Milestone 2
│   │   │   ├── engine.py     # Graph construction, BFS, DFS, shortest path & neighborhood
│   │   │   └── types.py      # GraphNode, GraphEdge, PathResult, NodeType, EdgeType
│   │   └── vector/           # Vector Engine (Similarity search) - Milestone 3
│   │       ├── __init__.py   # Package exports (VectorEngine, VectorIndex, Providers)
│   │       ├── benchmark.py  # Reproducible indexing throughput & query latency benchmark
│   │       ├── engine.py     # Embedding orchestration, MD5 caching & explainability
│   │       ├── index.py      # BLAS-accelerated in-memory cosine similarity matrix index
│   │       ├── providers.py  # SentenceTransformers, Scikit-Learn TF-IDF, Deterministic
│   │       └── types.py      # VectorDocument, VectorSearchResult
│   ├── ingestion/            # Reusable data ingestion & validation pipeline
│   ├── planner/              # Query decomposition & engine router
│   ├── fusion/               # Reciprocal Rank Fusion (RRF) & score normalization
│   ├── explain/              # Explainability & step-by-step latency telemetry
│   └── cli/                  # Interactive Command-Line Interface (Rich-powered)
│       └── main.py           # Interactive & subcommand CLI implementation
├── tests/                    # Automated test suites
│   ├── test_config.py        # Configuration and environment tests
│   ├── test_schema_syntax.py # Schema & seed data integrity tests
│   ├── test_relational_engine.py # Relational algebra & query tests (isolated in-memory)
│   ├── test_graph_engine.py  # Graph construction, traversal & shortest path tests
│   ├── test_vector_engine.py # Vector index, providers, top-K, and hash caching tests
│   └── test_mysql_integration.py # Live MySQL 8.x server integration tests
├── .env.example              # Credentials & engine configuration template
├── requirements.txt          # Python 3.13 dependencies
├── run_cli.py                # Root CLI executable entry point
└── README.md                 # Project documentation & execution guide
```

---

## 2. Relational Schema Design (3NF Normalization)

The relational schema strictly enforces **Third Normal Form (3NF)** with referential integrity constraints and B-Tree indexes:

```
+---------------+       1:N       +---------------+       1:N       +---------------+
|   colleges    | --------------> |     teams     | --------------> |   projects    |
+---------------+                 +---------------+                 +---------------+
  | college_id (PK)                 | team_id (PK)                    | project_id (PK)
  | name (UQ)                       | team_name                       | team_id (FK)
  | location idx                    | college_id (FK)                 | hackathon_id (FK)
                                                                      | title, track idx
                                                                      | description
                                                                        |
                                                                        | 1:N
                                                                        v
+---------------+       1:N       +---------------+       1:N       +---------------+
| participants  | --------------> |  team_members | <-------------- |    awards     |
+---------------+   (M:N Bridge)  +---------------+                 +---------------+
  | participant_id (PK)             | team_id (PK, FK)                | award_id (PK)
  | email (UQ)                      | participant_id (PK, FK)         | project_id (FK)
  | college_id (FK)                 | role                            | rank_pos, prize
```

---

## 3. Graph Engine Architecture & Topology

The Graph Engine constructs an in-memory knowledge graph directly from verified relational records without synthetic or speculative links.

### Entity Nodes (38 total in seed dataset):
- `college:{id}`: Academic institutions (5 nodes)
- `hackathon:{id}`: Hackathon events (3 nodes)
- `team:{id}`: Student builder teams (6 nodes)
- `participant:{id}`: Student participants (12 nodes)
- `project:{id}`: Hackathon projects (6 nodes)
- `award:{id}`: Winning accolades (6 nodes)

### Validated Relational Relationships (55 total edges):
- `(:Participant)-[:MEMBER_OF {role: ...}]->(:Team)` (13 edges)
- `(:Team)-[:AFFILIATED_WITH]->(:College)` (6 edges)
- `(:Participant)-[:ENROLLED_AT]->(:College)` (12 edges)
- `(:Team)-[:SUBMITTED]->(:Project)` (6 edges)
- `(:Project)-[:COMPETED_AT]->(:Hackathon)` (6 edges)
- `(:Project)-[:WON_AWARD {rank: ..., prize: ...}]->(:Award)` (6 edges)
- `(:Award)-[:PRESENTED_AT]->(:Hackathon)` (6 edges)

---

## 4. Vector Engine Architecture & Similarity Indexing

The Vector Engine provides natural language semantic and lexical retrieval over project descriptions (`projects.description`, `projects.short_summary`, `projects.tech_stack`), returning stable entity IDs (`project:{id}`) ready for relational joins.

### Embedding Provider Abstraction:
TriQuery implements a strict `BaseEmbeddingProvider` interface with explicit semantic labeling:
1. **`SentenceTransformersProvider`**:
   - Generates 384-dimensional dense neural embeddings using `all-MiniLM-L6-v2`.
   - `is_semantic = True`. Auto-activates if `sentence-transformers` is installed (`pip install sentence-transformers`).
2. **`TFIDFEmbeddingProvider`**:
   - Generates statistical lexical vector-space embeddings using Scikit-Learn `TfidfVectorizer` (sublinear term frequency, L2-normalized).
   - `is_semantic = False`. Operates offline with zero downloads using pre-installed packages.
3. **`DeterministicTestProvider`**:
   - Generates 64-dimensional pseudo-random projections via token MD5 hashing.
   - `is_semantic = False`. Guarantees reproducible, offline unit tests without network access.

### Why NumPy BLAS over FAISS / MongoDB:
- **Zero C++ Build Breakages**: FAISS (`faiss-cpu`) lacks official pre-compiled wheels for Python 3.13 on Windows, triggering MSVC build failures.
- **Zero Database Server Footprint**: No external vector databases (MongoDB Atlas, Qdrant, Milvus) are required.
- **100% Exact Recall**: Flat inner-product matrix multiplication ($\mathbf{X} \cdot \mathbf{q}^T$) avoids the recall trade-offs and hyperparameter tuning of approximate nearest neighbor algorithms (HNSW, IVF).
- **Sub-Millisecond Performance**: In-memory dense matrix search takes **< 0.05 ms** for hundreds of vectors and **< 1.7 ms** for 5,000 vectors ($7.32\text{ MB}$ RAM), easily fitting in CPU L3 cache.

### Document Hash Caching:
During index rebuilds (`vector_engine.build_from_relational()`), TriQuery computes an MD5 hash of each document's concatenated text. Unchanged records are skipped, eliminating redundant matrix calculations.

---

## 5. Algorithms, Time Complexities & DBMS Viva Defense

| Engine Operation | Algorithm / Mechanism | Time Complexity | Space Complexity |
| :--- | :--- | :--- | :--- |
| **Relational Join** | Indexed B-Tree Nested Loop | $O(\sum M_i \log N_i)$ | $O(N)$ (Disk / Buffer Pool) |
| **Graph BFS / Shortest Path** | Single-Source Queue BFS | $O(\|V\| + \|E\|)$ | $O(\|V\|)$ in RAM |
| **Vector Ingestion** | Batch Embedding + Matrix Stack | $O(N \cdot D)$ | $O(N \cdot D)$ float32 matrix |
| **Vector Search** | BLAS Cosine Inner Product + Top-K | $O(D) + O(N \cdot D) + O(N \log K)$ | $4 \cdot N \cdot D$ bytes |

### Why Vector Search vs. SQL `LIKE '%pattern%'`:
1. **Semantic Conceptual Matching**:
   - SQL `LIKE '%traffic congestion%'` only matches exact string occurrences and completely misses related projects indexed as "autonomous drone navigation", "fleet routing", or "UAV pathfinding".
   - Vector similarity projects text into a continuous metric space where geometric closeness ($\cos \theta$) measures conceptual relevance.
2. **Mathematical Formulation**:
   - Cosine Similarity: $\cos(\theta) = \frac{\mathbf{q} \cdot \mathbf{d}}{\|\mathbf{q}\| \|\mathbf{d}\|}$.
   - Because all vectors in TriQuery are L2-normalized during ingestion ($\|\mathbf{d}\| = 1.0$) and querying ($\|\mathbf{q}\| = 1.0$):
     $$\cos(\theta) = \mathbf{q} \cdot \mathbf{d} = \sum_{i=1}^D q_i \cdot d_i$$
   - This simplifies cosine similarity to a multi-threaded matrix-vector dot product with zero division overhead.

---

## 6. Milestone 4: Unified Query Planner & Reciprocal Rank Fusion (RRF)

Milestone 4 introduces the unified query execution and multi-engine result fusion layer. It enables declarative multi-paradigm queries combining SQL constraints, graph topology traversals, and semantic vector similarity.

### 6.1 Declarative Query Representation (`UnifiedQuery`)
TriQuery defines a typed, minimal query schema supporting selective engine dispatch:

```python
from src.core.query import UnifiedQuery, RelationalSubquery, GraphSubquery, VectorSubquery, FusionConfig

query = UnifiedQuery(
    query_id="demo-5",
    name="three_way_unified_search",
    relational=RelationalSubquery(filters={"track": "Robotics & AI"}),
    graph=GraphSubquery(operation="college_projects", source_entity="IIT Delhi"),
    vector=VectorSubquery(text="autonomous drone navigation pathfinding", top_k=5),
    fusion=FusionConfig(k=60, mandatory_relational_filter=True)
)
```

### 6.2 Reciprocal Rank Fusion (RRF) Formulation
Ranked lists produced across disparate paradigms cannot be fused via linear score addition because their raw metrics are incommensurable:
- **Relational**: Binary set inclusion $\{0, 1\}$.
- **Graph**: Integer path length / hop distance $\{1, 2, 3\}$.
- **Vector**: Dense cosine similarity in $[0.0, 1.0]$.

TriQuery uses **Reciprocal Rank Fusion (RRF)**:
$$RRF(d) = \sum_{m \in M} \frac{1}{k + \text{rank}_m(d)}$$

Where:
- $M$: Participating engine rankings (Relational, Graph, Vector).
- $\text{rank}_m(d)$: Ordinal rank position of entity $d$ in engine $m$, starting at $1$.
- $k$: Configurable positive smoothing constant (default: $60$).
- If document $d$ does not appear in ranking $m$, its contribution from engine $m$ is exactly $0$.

#### Worked Numerical Example:
Consider candidate entity `project:1` ("AeroVision"):
- Relational Rank: $\#1 \implies \frac{1}{60 + 1} = \frac{1}{61} \approx 0.016393$
- Graph Rank: $\#1 \implies \frac{1}{60 + 1} = \frac{1}{61} \approx 0.016393$
- Vector Rank: $\#1 \implies \frac{1}{60 + 1} = \frac{1}{61} \approx 0.016393$
- **Total Fused RRF Score**:
  $$RRF(\text{project:1}) = 0.016393 + 0.016393 + 0.016393 = \mathbf{0.049180}$$

Consider candidate entity `project:3` appearing only in Vector ranking at rank $\#1$:
- Vector Rank: $\#1 \implies \frac{1}{60 + 1} = 0.016393$
- Relational Rank: Absent $\implies 0.0$
- Graph Rank: Absent $\implies 0.0$
- **Total Fused RRF Score**: $\mathbf{0.016393}$

#### Mandatory SQL Predicate Gating:
When `mandatory_relational_filter = True`, relational query results act as a hard constraint filter. Any candidate entity returned by graph traversal or vector search that does not satisfy the relational filter is pruned before final consensus ranking.

#### RRF Advantages & Limitations:
- **Advantage**: Scale-invariant, parameter-free (requires no per-engine tuning weights), immune to outliers or disparate metric distributions.
- **Limitation**: Ignores the magnitude of score separation (e.g. difference between cosine 0.99 and 0.90 is treated the same as 0.50 and 0.41 if both represent adjacent rank positions).

### 6.3 Algorithmic Complexity
- **Planning Complexity**: $O(E)$ where $E \le 3$ is the number of engines. Dependency graph topological sorting operates in $O(1)$ time for $\le 4$ steps.
- **Fusion Time Complexity**: $O\left(\sum_{m} |R_m| + N \log N\right)$ where $|R_m|$ is the length of ranking from engine $m$, and $N \le \sum |R_m|$ is the total number of unique candidates. For top-K lists ($K \le 50$), fusion executes in $< 0.2$ ms.
- **Fusion Space Complexity**: $O(N)$ memory to store candidate hash map and deduplication sets.

---

## 7. Running the TriQuery CLI

TriQuery features a unified CLI for Relational, Graph, Vector, and Multi-Paradigm operations:

### Interactive Menu
```bash
python run_cli.py
```

### Milestone 4 Unified Multi-Paradigm Commands:
```bash
python run_cli.py unified-presets                                 # List all 5 canonical benchmark queries
python run_cli.py unified-query 1                                 # Preset 1: Relational-only SQL execution
python run_cli.py unified-query 2                                 # Preset 2: Graph-only relationship path
python run_cli.py unified-query 3                                 # Preset 3: Vector-only semantic search
python run_cli.py unified-query 4                                 # Preset 4: 2-Engine Hybrid (SQL + Vector)
python run_cli.py unified-query 5                                 # Preset 5: 3-Paradigm Unified (SQL + Graph + Vector)
python run_cli.py unified-explain 5                               # Full execution plan & RRF evidence
```

### Relational Subcommands:
```bash
python run_cli.py status                                          # Table row counts
python run_cli.py projects                                        # 5-way relational JOIN
python run_cli.py projects --track "Robotics & AI"                # Filter by track
python run_cli.py leaderboard                                     # College prize leaderboard
python run_cli.py hackathons                                      # Event metrics summary
python run_cli.py explain "SELECT * FROM projects"                # Query optimization plan
```

### Graph Subcommands:
```bash
python run_cli.py graph-status                                    # Node & edge breakdown
python run_cli.py graph-team NeuralVanguard                       # 1-hop team membership
python run_cli.py graph-college "IIT Delhi"                       # 2-hop college projects
python run_cli.py graph-path -s "participant:1" -t "participant:5" # Shortest relationship path
python run_cli.py graph-bfs team:1 --depth 2                      # Level-order traversal
```

### Vector Subcommands:
```bash
python run_cli.py vector-status                                   # Index dimensions & health
python run_cli.py vector-search "AI solutions for traffic congestion"
python run_cli.py vector-search "Secure digital identity platforms"
python run_cli.py vector-explain "AI solutions for traffic congestion"
```

---

## 8. Running Automated Tests

TriQuery provides 99 comprehensive automated tests across all four milestones:

```bash
python -m unittest discover -s tests -v
```

### Test Suite Distribution (99 Total Tests: 91 Passed, 8 Skipped):
- **Result Fusion Tests** (`tests/test_fusion.py` - 7 tests):
  Mathematical RRF correctness against manual arithmetic, missing rankings, deduplication, ties, non-positive $k$, and mandatory relational gating.
- **Unified Planner Tests** (`tests/test_planner.py` - 9 tests):
  Dynamic engine selection, step dependency ordering, selective dispatch (relational-only queries never touch graph or vector), per-stage latency telemetry, and exception handling.
- **Explainability Tests** (`tests/test_explain.py` - 3 tests):
  Structured `QueryExplanation` generation, plan explanation strings, viva defense notes, and Rich table rendering.
- **Unified Integration Tests** (`tests/test_unified_integration.py` - 6 tests):
  End-to-end execution of presets 1-5 against real `RelationalEngine`, `GraphEngine`, and `VectorEngine` instances, plus zero-result constraint handling.
- **Relational Tests** (`test_config.py`, `test_schema_syntax.py`, `test_relational_engine.py` - 19 tests):
  3NF schema, constraints, 5-way joins, aggregations, and EXPLAIN plans.
- **Graph Tests** (`test_graph_engine.py` - 18 tests):
  Graph construction, 38 nodes, 55 edges, BFS, DFS, shortest path, and topological consistency.
- **Vector Tests** (`test_vector_engine.py` - 30 tests):
  Vector index, L2 normalization, cosine ranking, TF-IDF and deterministic providers, MD5 document hash caching, and conditionally skipped live neural model tests.
- **MySQL Integration Tests** (`test_mysql_integration.py` - 7 tests):
  Skipped gracefully when MySQL server is offline.
