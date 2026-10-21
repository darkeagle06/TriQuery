"""
Interactive & Command-Line Interface for TriQuery.
Executes relational SQL queries, joins, aggregations,
and graph traversals (BFS, DFS, shortest path) using unified engine interfaces.
"""

import argparse
import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import DatabaseConfig, config
from src.engines.graph.engine import GraphEngine
from src.engines.relational.connection import DatabaseConnectionManager
from src.engines.relational.engine import RelationalEngine
from src.engines.relational.setup_db import setup_database
from src.engines.vector.engine import VectorEngine
from src.engines.vector.providers import (
    BaseEmbeddingProvider,
    DeterministicTestProvider,
    SentenceTransformersProvider,
    TFIDFEmbeddingProvider,
)
from src.core.query import (
    PREDEFINED_QUERIES,
    FusionConfig,
    GraphSubquery,
    RelationalSubquery,
    UnifiedQuery,
    VectorSubquery,
)
from src.planner.planner import UnifiedExecutionResult, UnifiedQueryPlanner
from src.explain.explainer import QueryExplainer

console = Console()


def get_relational_engine(driver: Optional[str] = None) -> RelationalEngine:
    """Instantiates RelationalEngine based on CLI flag or environment config."""
    if driver:
        cfg = DatabaseConfig(
            driver=driver,
            sqlite_fallback=(driver == "sqlite")
        )
    else:
        # Enable graceful fallback to isolated SQLite when MySQL is unreachable
        cfg = DatabaseConfig(
            host=config.db.host,
            port=config.db.port,
            name=config.db.name,
            user=config.db.user,
            password=config.db.password,
            charset=config.db.charset,
            driver=config.db.driver,
            sqlite_fallback=True,
            sqlite_path=config.db.sqlite_path,
        )
    conn_mgr = DatabaseConnectionManager(cfg)
    return RelationalEngine(conn_mgr)


def get_graph_engine(rel_engine: RelationalEngine) -> GraphEngine:
    """Instantiates GraphEngine initialized from the relational store."""
    return GraphEngine(relational_engine=rel_engine, auto_build=True)


def get_vector_engine(rel_engine: RelationalEngine, provider_name: Optional[str] = None) -> VectorEngine:
    """Instantiates VectorEngine initialized from the relational store."""
    provider = None
    if provider_name in ("deterministic", "test"):
        provider = DeterministicTestProvider()
    elif provider_name in ("sentence-transformers", "neural"):
        provider = SentenceTransformersProvider()
    elif provider_name in ("tfidf", "lexical"):
        provider = TFIDFEmbeddingProvider()
    return VectorEngine(relational_engine=rel_engine, provider=provider, auto_build=True)


def get_planner(
    rel_engine: RelationalEngine,
    graph_engine: GraphEngine,
    vector_engine: VectorEngine,
    k: int = 60
) -> UnifiedQueryPlanner:
    """Instantiates UnifiedQueryPlanner with specified engines and RRF parameter."""
    from src.fusion.rrf import ReciprocalRankFusion
    return UnifiedQueryPlanner(
        relational_engine=rel_engine,
        graph_engine=graph_engine,
        vector_engine=vector_engine,
        fusion_engine=ReciprocalRankFusion(k=k)
    )


# =============================================================================
# Relational CLI Commands
# =============================================================================

def cmd_status(engine: RelationalEngine):
    """Checks database health and displays table statistics."""
    console.print("\n[bold cyan]TriQuery Relational Engine: System Status[/bold cyan]")
    healthy = engine.is_healthy()
    mode = "SQLite (Isolated Mode)" if engine.conn_mgr.is_sqlite_mode else f"MySQL 8.x ({engine.conn_mgr.cfg.host}:{engine.conn_mgr.cfg.port})"

    console.print(f"Backend Store : [bold]{mode}[/bold]")
    console.print(f"Health Status : {'[bold green][ONLINE][/bold green]' if healthy else '[bold red][OFFLINE][/bold red]'}")

    if not healthy:
        console.print("[yellow]Hint: Run 'python run_cli.py setup-db' or check database credentials in .env[/yellow]\n")
        return

    counts = engine.get_table_counts()
    table = Table(title="Relational Table Record Counts")
    table.add_column("Table Name", style="cyan")
    table.add_column("Row Count", style="green", justify="right")
    for tbl, count in counts.items():
        table.add_row(tbl, str(count))
    console.print(table)
    console.print()


def cmd_projects(engine: RelationalEngine, college: Optional[str] = None, track: Optional[str] = None):
    """Executes 5-way relational JOIN combining projects, teams, colleges, hackathons, and awards."""
    console.print("\n[bold cyan]Executing 5-Way Relational JOIN: Projects & Awards[/bold cyan]")
    if college:
        result = engine.find_projects_by_college(college)
    else:
        result = engine.get_projects_with_details(track=track)

    if not result.success:
        console.print(f"[bold red]Query failed:[/bold red] {result.error}")
        return

    meta = result.metadata
    console.print(f"[dim]Execution Time: [bold green]{meta.execution_time_ms} ms[/bold green] | Records Found: [bold]{meta.record_count}[/bold] | Backend: {meta.notes[0] if meta.notes else 'Relational'}[/dim]\n")

    table = Table(title="Hackathon Projects & Results")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Project Title", style="bold white")
    table.add_column("Track", style="magenta")
    table.add_column("Team", style="cyan")
    table.add_column("College", style="yellow")
    if not college:
        table.add_column("Hackathon", style="blue")
        table.add_column("Award Placement", style="bold green")
        table.add_column("Prize (INR)", style="green", justify="right")

    for row in result.data:
        if college:
            table.add_row(
                str(row.get("project_id", "")),
                str(row.get("title", "")),
                str(row.get("track", "")),
                str(row.get("team_name", "")),
                str(row.get("college_name", "")),
            )
        else:
            table.add_row(
                str(row.get("project_id", "")),
                str(row.get("project_title", "")),
                str(row.get("track", "")),
                str(row.get("team_name", "")),
                str(row.get("college_name", "")),
                str(row.get("hackathon_name", "")),
                str(row.get("prize_category", "")),
                f"Rs {float(row.get('cash_prize', 0)):,.2f}" if row.get("cash_prize") else "Rs 0.00",
            )

    console.print(table)
    console.print()


def cmd_leaderboard(engine: RelationalEngine):
    """Executes analytical aggregation: total prize money won grouped by college."""
    console.print("\n[bold cyan]Executing Relational Aggregation: College Leaderboard[/bold cyan]")
    result = engine.find_top_award_winning_colleges()

    if not result.success:
        console.print(f"[bold red]Query failed:[/bold red] {result.error}")
        return

    meta = result.metadata
    console.print(f"[dim]Execution Time: [bold green]{meta.execution_time_ms} ms[/bold green] | Aggregation: GROUP BY c.college_id | Order: SUM(cash_prize) DESC[/dim]\n")

    table = Table(title="Top Performing Colleges by Total Prize Money")
    table.add_column("Rank", style="dim", justify="right")
    table.add_column("College Name", style="bold white")
    table.add_column("Location", style="yellow")
    table.add_column("Total Awards", style="cyan", justify="right")
    table.add_column("Total Prize Won", style="bold green", justify="right")

    for idx, row in enumerate(result.data, 1):
        table.add_row(
            str(idx),
            str(row.get("college_name", "")),
            f"{row.get('city', '')}, {row.get('state', '')}",
            str(row.get("total_awards", 0)),
            f"Rs {float(row.get('total_prize_money', 0)):,.2f}",
        )

    console.print(table)
    console.print()


def cmd_hackathons(engine: RelationalEngine):
    """Executes multi-level aggregation summary of hackathons."""
    console.print("\n[bold cyan]Executing Multi-Level Aggregation: Hackathon Summaries[/bold cyan]")
    result = engine.get_hackathon_summary_metrics()

    if not result.success:
        console.print(f"[bold red]Query failed:[/bold red] {result.error}")
        return

    meta = result.metadata
    console.print(f"[dim]Execution Time: [bold green]{meta.execution_time_ms} ms[/bold green][/dim]\n")

    table = Table(title="Hackathon Event Performance Overview")
    table.add_column("Hackathon Name", style="bold white")
    table.add_column("Year", style="yellow")
    table.add_column("Theme", style="magenta")
    table.add_column("Total Prize Pool", style="green", justify="right")
    table.add_column("Submissions", style="cyan", justify="right")
    table.add_column("Awards Won", style="cyan", justify="right")
    table.add_column("Cash Distributed", style="bold green", justify="right")

    for row in result.data:
        table.add_row(
            str(row.get("hackathon_name", "")),
            str(row.get("edition_year", "")),
            str(row.get("theme", "")),
            f"Rs {float(row.get('total_prize_pool', 0)):,.2f}",
            str(row.get("total_projects_submitted", 0)),
            str(row.get("total_awards_won", 0)),
            f"Rs {float(row.get('total_cash_distributed', 0)):,.2f}",
        )

    console.print(table)
    console.print()


def cmd_explain(engine: RelationalEngine, query: str):
    """Executes EXPLAIN on an SQL query to inspect query optimization plan."""
    console.print(f"\n[bold cyan]Query Optimization Inspection: EXPLAIN[/bold cyan]")
    console.print(f"Target Query: [yellow]{query}[/yellow]\n")
    plan = engine.explain(query)

    if not plan["success"]:
        console.print(f"[bold red]EXPLAIN failed:[/bold red] {plan.get('error')}")
        return

    table = Table(title=f"Execution Plan ({plan['backend'].upper()})")
    records = plan.get("explain_plan", [])
    if records:
        for key in records[0].keys():
            table.add_column(str(key), style="cyan")
        for rec in records:
            table.add_row(*[str(val) for val in rec.values()])
        console.print(table)
    else:
        console.print("[dim]No plan details returned.[/dim]")
    console.print()


# =============================================================================
# Graph Engine CLI Commands
# =============================================================================

def cmd_graph_status(graph_engine: GraphEngine):
    """Displays graph node and edge counts and degree distribution."""
    console.print("\n[bold cyan]TriQuery Graph Engine: Knowledge Graph Status[/bold cyan]")
    console.print(f"Engine Type   : [bold]NetworkX Knowledge Graph[/bold]")
    console.print(f"Total Nodes   : [bold green]{graph_engine.node_count}[/bold green]")
    console.print(f"Total Edges   : [bold green]{graph_engine.edge_count}[/bold green]")

    # Node types breakdown
    node_type_counts = {}
    for _, data in graph_engine.graph.nodes(data=True):
        nt = data.get("node_type", "unknown")
        node_type_counts[nt] = node_type_counts.get(nt, 0) + 1

    table = Table(title="Graph Entity (Node) Types")
    table.add_column("Node Type", style="cyan")
    table.add_column("Count", style="green", justify="right")
    for nt, c in sorted(node_type_counts.items()):
        table.add_row(nt, str(c))
    console.print(table)

    # Edge types breakdown
    edge_type_counts = {}
    for _, _, data in graph_engine.graph.edges(data=True):
        et = data.get("edge_type", "unknown")
        edge_type_counts[et] = edge_type_counts.get(et, 0) + 1

    table2 = Table(title="Graph Relationship (Edge) Types")
    table2.add_column("Edge Type", style="magenta")
    table2.add_column("Count", style="green", justify="right")
    for et, c in sorted(edge_type_counts.items()):
        table2.add_row(et, str(c))
    console.print(table2)
    console.print()


def cmd_graph_team(graph_engine: GraphEngine, team_identifier: str):
    """Graph Demo 1: Finding all participants belonging to a team."""
    console.print(f"\n[bold cyan]Graph Query: Team Members for '{team_identifier}'[/bold cyan]")
    result = graph_engine.get_team_members(team_identifier)

    if not result.success:
        console.print(f"[bold red]{result.error}[/bold red]\n")
        return

    meta = result.metadata
    console.print(f"[dim]Latency: [bold green]{meta.execution_time_ms} ms[/bold green] | Operation: 1-hop reverse traversal (:Participant)-[:MEMBER_OF]->(:Team)[/dim]\n")

    table = Table(title=f"Members of Team: {team_identifier}")
    table.add_column("Participant ID", style="dim", justify="right")
    table.add_column("Full Name", style="bold white")
    table.add_column("Email", style="yellow")
    table.add_column("Team Role", style="bold green")

    for row in result.data:
        table.add_row(
            str(row.get("participant_id", "")),
            str(row.get("full_name", "")),
            str(row.get("email", "")),
            str(row.get("role", "")),
        )

    console.print(table)
    console.print()


def cmd_graph_college(graph_engine: GraphEngine, college_identifier: str):
    """Graph Demo 2: Traversing relationships from a college to its projects."""
    console.print(f"\n[bold cyan]Graph Query: Projects Affiliated with '{college_identifier}'[/bold cyan]")
    result = graph_engine.get_college_projects(college_identifier)

    if not result.success:
        console.print(f"[bold red]{result.error}[/bold red]\n")
        return

    meta = result.metadata
    console.print(f"[dim]Latency: [bold green]{meta.execution_time_ms} ms[/bold green] | Operation: 2-hop traversal (:College)<-[:AFFILIATED_WITH]-(:Team)-[:SUBMITTED]->(:Project)[/dim]\n")

    table = Table(title=f"Projects Submitted by: {college_identifier}")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Project Title", style="bold white")
    table.add_column("Track", style="magenta")
    table.add_column("Team", style="cyan")
    table.add_column("Tech Stack", style="yellow")
    table.add_column("Award Won", style="bold green")

    for row in result.data:
        table.add_row(
            str(row.get("project_id", "")),
            str(row.get("title", "")),
            str(row.get("track", "")),
            str(row.get("team_name", "")),
            str(row.get("tech_stack", "")),
            str(row.get("award", "")),
        )

    console.print(table)
    console.print()


def cmd_graph_path(graph_engine: GraphEngine, source: str, target: str, directed: bool = False):
    """Graph Demo 3 & 4: Finding shortest relationship path or reporting when none exists."""
    console.print(f"\n[bold cyan]Graph Query: Shortest Relationship Path[/bold cyan]")
    console.print(f"Source: [bold yellow]{source}[/bold yellow] -> Target: [bold yellow]{target}[/bold yellow] (Directed: {directed})\n")

    path_res = graph_engine.find_shortest_path(source, target, directed=directed)

    if not path_res.found:
        console.print(f"[bold red][NO PATH][/bold red] {path_res.message}\n")
        return

    console.print(f"[bold green][PATH FOUND][/bold green] Distance: [bold]{path_res.length} hops[/bold]")
    console.print(f"Path Sequence: [cyan]{' -> '.join(path_res.path)}[/cyan]\n")

    table = Table(title=f"Step-by-Step Relationship Navigation ({path_res.length} hops)")
    table.add_column("Step", style="dim", justify="right")
    table.add_column("From Entity", style="bold white")
    table.add_column("Relationship (Edge)", style="bold magenta")
    table.add_column("Direction", style="yellow")
    table.add_column("To Entity", style="bold white")

    for idx, step in enumerate(path_res.steps, 1):
        table.add_row(
            str(idx),
            step.from_node,
            step.edge_type,
            step.direction,
            step.to_node,
        )

    console.print(table)
    console.print()


def cmd_graph_bfs(graph_engine: GraphEngine, start_node: str, max_depth: Optional[int] = None):
    """Graph BFS: Explores graph layer-by-layer up to max_depth."""
    console.print(f"\n[bold cyan]Graph BFS Traversal: Level-Order Exploration[/bold cyan]")
    console.print(f"Starting Node: [bold yellow]{start_node}[/bold yellow] (Max Depth: {max_depth or 'Unlimited'})\n")

    visited = graph_engine.bfs_traversal(start_node, max_depth=max_depth)
    if not visited:
        console.print(f"[bold red]Start node not found: '{start_node}'[/bold red]\n")
        return

    table = Table(title=f"BFS Exploration from '{start_node}' ({len(visited)} nodes visited)")
    table.add_column("Depth", style="green", justify="right")
    table.add_column("Node ID", style="cyan")
    table.add_column("Entity Type", style="magenta")
    table.add_column("Label / Name", style="bold white")
    table.add_column("Via Relationship", style="yellow")
    table.add_column("From Node", style="dim")

    for row in visited:
        table.add_row(
            str(row["depth"]),
            row["node_id"],
            str(row.get("node_type", "")),
            str(row.get("label", "")),
            str(row.get("relationship", "ORIGIN")),
            str(row.get("parent_id", "-")),
        )

    console.print(table)
    console.print()


# =============================================================================
# Vector Engine CLI Commands
# =============================================================================

def cmd_vector_status(vector_engine: VectorEngine):
    """Displays vector index status, provider information, and document counts."""
    console.print("\n[bold cyan]TriQuery Vector Engine: Similarity Index Status[/bold cyan]")
    healthy = vector_engine.is_healthy()
    status_str = "[bold green][ONLINE][/bold green]" if healthy else "[bold red][OFFLINE][/bold red]"
    console.print(f"Health Status      : {status_str}")
    console.print(f"Embedding Provider : [bold]{vector_engine.provider.description}[/bold]")
    console.print(f"Semantic Search    : {'[bold green]True (Deep Neural Embeddings)[/bold green]' if vector_engine.provider.is_semantic else '[bold yellow]False (Lexical / Test Vector Space)[/bold yellow]'}")
    console.print(f"Vector Dimension   : [bold cyan]{vector_engine.index.dimension}[/bold cyan]")
    console.print(f"Indexed Documents  : [bold green]{vector_engine.document_count}[/bold green]")

    dim = vector_engine.index.dimension or 0
    cnt = vector_engine.document_count
    bytes_used = cnt * dim * 4
    console.print(f"Index Memory (RAM) : [bold]{bytes_used} bytes ({bytes_used / 1024:.2f} KB)[/bold]")

    table = Table(title="Indexed Vector Entities (Projects)")
    table.add_column("Entity ID", style="cyan")
    table.add_column("Project Title", style="bold white")
    table.add_column("Track", style="magenta")
    table.add_column("Tech Stack", style="yellow")

    for eid in vector_engine.index._entity_ids:
        meta = vector_engine.index.get_metadata(eid) or {}
        table.add_row(
            eid,
            str(meta.get("title", "")),
            str(meta.get("track", "")),
            str(meta.get("tech_stack", ""))
        )
    console.print(table)
    console.print()


def cmd_vector_search(vector_engine: VectorEngine, query: str, top_k: int = 5, min_score: float = 0.0):
    """Executes natural language similarity search over hackathon projects."""
    console.print(f"\n[bold cyan]Vector Similarity Search[/bold cyan]")
    console.print(f"Query: [bold yellow]\"{query}\"[/bold yellow] | Top-K: [bold]{top_k}[/bold] | Min Score: [bold]{min_score}[/bold]")
    console.print(f"Provider: [dim]{vector_engine.provider.description}[/dim]\n")

    result = vector_engine.search(query, top_k=top_k, min_score=min_score)
    if not result.success:
        console.print(f"[bold red]Search failed:[/bold red] {result.error}\n")
        return

    meta = result.metadata
    console.print(f"[dim]Latency: [bold green]{meta.execution_time_ms} ms[/bold green] | Matches Found: [bold]{meta.record_count}[/bold] | Method: Cosine Inner-Product[/dim]\n")

    if not result.data:
        console.print("[yellow]No project descriptions matched the query criteria above the minimum score threshold.[/yellow]\n")
        return

    table = Table(title=f"Top Nearest-Neighbor Matches for: '{query}'")
    table.add_column("Rank", style="dim", justify="right")
    table.add_column("Score", style="bold green", justify="right")
    table.add_column("Entity ID", style="cyan")
    table.add_column("Project Title", style="bold white")
    table.add_column("Track", style="magenta")
    table.add_column("Short Description / Summary", style="dim", overflow="fold")

    for row in result.data:
        score_val = row.get("score", 0.0)
        score_color = "green" if score_val >= 0.5 else ("yellow" if score_val >= 0.2 else "dim")
        table.add_row(
            str(row.get("rank", "")),
            f"[{score_color}]{score_val:.4f}[/{score_color}]",
            str(row.get("entity_id", "")),
            str(row.get("title", "")),
            str(row.get("track", "")),
            str(row.get("short_summary", "")).strip()
        )

    console.print(table)
    console.print()


def cmd_vector_explain(vector_engine: VectorEngine, query: Optional[str] = None):
    """Displays algorithmic complexity and conceptual explanation for vector search."""
    q = query or "AI solutions for traffic congestion"
    console.print(f"\n[bold cyan]Vector Engine Algorithmic Complexity Inspection (EXPLAIN)[/bold cyan]")
    console.print(f"Target Query: [yellow]\"{q}\"[/yellow]\n")

    info = vector_engine.explain(q)
    table = Table(title="Vector Engine Performance & Theoretical Complexity")
    table.add_column("Metric / Property", style="cyan")
    table.add_column("Specification / Complexity", style="bold white")

    table.add_row("Provider", info.get("provider", ""))
    table.add_row("Is Neural Semantic?", "True (Continuous Semantic Space)" if info.get("is_semantic") else "False (Lexical / Hash Space)")
    table.add_row("Vector Dimension (D)", str(info.get("vector_dimension", "")))
    table.add_row("Indexed Documents (N)", str(info.get("indexed_documents", "")))
    table.add_row("Indexing Complexity", info.get("indexing_complexity", ""))
    table.add_row("Search Complexity", info.get("search_complexity", ""))
    table.add_row("Space Complexity", info.get("space_complexity", ""))

    console.print(table)
    console.print()

    console.print(Panel(
        f"[bold white]Why Vector Search vs. SQL LIKE?[/bold white]\n\n"
        f"{info.get('comparison_with_sql_like', '')}\n\n"
        f"[bold cyan]Mathematical Formulation:[/bold cyan]\n"
        f"Cosine Similarity: cos(theta) = (q . d) / (||q|| * ||d||)\n"
        f"Because all vectors in TriQuery's index are strictly L2-normalized during ingestion (||d|| = 1.0) and query (||q|| = 1.0):\n"
        f"cos(theta) = q . d = sum(q_i * d_i) for i in 1..D.\n"
        f"This simplifies cosine similarity calculation to a fast BLAS-accelerated inner product with zero division overhead.",
        title="DBMS Viva Defense Note"
    ))
    console.print()


# =============================================================================
# Unified Query Planner & Fusion CLI Commands (Milestone 4)
# =============================================================================

def cmd_list_presets():
    """Displays all predefined multi-paradigm benchmark queries."""
    console.print("\n[bold cyan]TriQuery Predefined Multi-Paradigm Benchmark Queries[/bold cyan]")
    table = Table(title="Predefined Queries (Presets 1 to 5)")
    table.add_column("Preset #", style="dim", justify="right")
    table.add_column("Query Name", style="cyan")
    table.add_column("Target Paradigms", style="magenta")
    table.add_column("Query Description", style="bold white")

    for key, q in sorted(PREDEFINED_QUERIES.items()):
        engines = []
        if q.relational:
            engines.append("Relational (SQL)")
        if q.graph:
            engines.append("Graph (NetworkX)")
        if q.vector:
            engines.append("Vector (Cosine)")
        table.add_row(key, q.name, " + ".join(engines), q.description)

    console.print(table)
    console.print()


def cmd_unified_query(
    planner: UnifiedQueryPlanner,
    query: UnifiedQuery,
    explain: bool = False
):
    """Executes a UnifiedQuery across engines and displays fused results."""
    console.print(f"\n[bold cyan]Executing Unified Multi-Paradigm Query[/bold cyan]")
    console.print(f"Query Name : [bold yellow]{query.name}[/bold yellow] ({query.query_id})")
    console.print(f"Description: [dim]{query.description or 'Custom Multi-Paradigm Query'}[/dim]\n")

    res = planner.execute_plan(query)
    if not res.success:
        console.print(f"[bold red]Execution failed:[/bold red] {res.error}\n")
        return

    meta_parts = [
        f"Latency: [bold green]{res.total_latency_ms:.3f} ms[/bold green]",
        f"Fused Records: [bold]{len(res.fused_results)}[/bold]",
    ]
    for stg, lat in res.stage_latencies_ms.items():
        meta_parts.append(f"{stg.capitalize()}: {lat:.2f} ms")
    console.print(f"[dim]{' | '.join(meta_parts)}[/dim]\n")

    if not res.fused_results:
        console.print("[yellow]No candidate entities satisfied all multi-paradigm query constraints.[/yellow]\n")
    else:
        table = Table(title=f"Fused Results: {query.name}")
        table.add_column("Rank", style="dim", justify="right")
        table.add_column("Score", style="bold green", justify="right")
        table.add_column("Entity ID", style="cyan")
        table.add_column("Project Title", style="bold white")
        table.add_column("Engines", style="magenta")
        table.add_column("Ranks / Scores", style="yellow")
        table.add_column("Short Description", style="dim", overflow="fold")

        for item in res.fused_results:
            engines_str = ", ".join([e.value for e in item.participating_engines])
            ranks_str = ", ".join([f"{k}: #{v}" for k, v in item.engine_ranks.items()])
            summary = item.metadata.get("short_summary") or item.metadata.get("label") or ""
            table.add_row(
                str(item.final_rank),
                f"{item.rrf_score:.4f}",
                item.entity_id,
                item.title,
                engines_str,
                ranks_str,
                str(summary).strip(),
            )
        console.print(table)
        console.print()

    if explain:
        QueryExplainer.render_rich_explanation(res, query, console)


# =============================================================================
# Interactive Menu
# =============================================================================

def interactive_menu(
    rel_engine: RelationalEngine,
    graph_engine: GraphEngine,
    vector_engine: VectorEngine,
    planner: UnifiedQueryPlanner,
):
    """Displays an interactive console menu."""
    while True:
        console.print(Panel(
            "[bold cyan]TriQuery Multi-Paradigm DBMS Terminal[/bold cyan]\n"
            "[dim]-- Relational Engine (MySQL / SQLite) --[/dim]\n"
            "1.  Database Status & Table Record Counts\n"
            "2.  Hackathon Projects (5-Way Relational JOIN)\n"
            "3.  College Prize Leaderboard (GROUP BY Aggregation)\n"
            "4.  Hackathon Summaries (Multi-Table Aggregation)\n"
            "5.  Filter Projects by Track\n"
            "6.  Inspect SQL Query Plan (EXPLAIN)\n"
            "7.  Populate / Reset Database (Schema & Seed)\n"
            "[dim]-- Graph Engine (NetworkX) --[/dim]\n"
            "8.  Graph Status & Entity Topology\n"
            "9.  Team Members (Graph 1-Hop Traversal)\n"
            "10. College Projects (Graph 2-Hop Traversal)\n"
            "11. Shortest Relationship Path (Collaborator / Entity Path)\n"
            "12. BFS Exploration (Level-Order Traversal)\n"
            "[dim]-- Vector Engine (Cosine Index & Embeddings) --[/dim]\n"
            "13. Vector Index Status & Document Metadata\n"
            "14. Natural Language Similarity Search\n"
            "15. Vector Search Complexity & Algorithmic Explanation (EXPLAIN)\n"
            "[dim]-- Unified Multi-Paradigm Planner & RRF Fusion (Milestone 4) --[/dim]\n"
            "16. Predefined Benchmark Queries (Presets 1 to 5)\n"
            "17. Interactive Multi-Paradigm Query (Relational + Graph + Vector)\n"
            "18. Unified Execution Plan & RRF Telemetry Breakdown (EXPLAIN)\n"
            "0.  Exit",
            title="Menu",
            subtitle="Choose an option"
        ))
        choice = console.input("[bold yellow]Enter choice (0-18): [/bold yellow]").strip()

        if choice == "1":
            cmd_status(rel_engine)
        elif choice == "2":
            cmd_projects(rel_engine)
        elif choice == "3":
            cmd_leaderboard(rel_engine)
        elif choice == "4":
            cmd_hackathons(rel_engine)
        elif choice == "5":
            track = console.input("[yellow]Enter track name (e.g. 'Robotics & AI', 'Healthcare & Web3'): [/yellow]").strip()
            cmd_projects(rel_engine, track=track if track else None)
        elif choice == "6":
            default_q = "SELECT p.title, t.team_name, c.name FROM projects p JOIN teams t ON p.team_id=t.team_id JOIN colleges c ON t.college_id=c.college_id WHERE c.name='IIT Delhi'"
            query = console.input(f"[yellow]Enter SQL query (press Enter for default): [/yellow]").strip()
            cmd_explain(rel_engine, query or default_q)
        elif choice == "7":
            setup_database(rel_engine.conn_mgr.cfg)
            graph_engine.build_from_relational()
            vector_engine.build_from_relational(force=True)
        elif choice == "8":
            cmd_graph_status(graph_engine)
        elif choice == "9":
            team = console.input("[yellow]Enter team name or ID (e.g. 'NeuralVanguard', 'team:1'): [/yellow]").strip()
            cmd_graph_team(graph_engine, team or "NeuralVanguard")
        elif choice == "10":
            college = console.input("[yellow]Enter college name or ID (e.g. 'IIT Delhi', 'college:1'): [/yellow]").strip()
            cmd_graph_college(graph_engine, college or "IIT Delhi")
        elif choice == "11":
            src = console.input("[yellow]Enter source entity (e.g. 'participant:1', 'IIT Delhi'): [/yellow]").strip()
            tgt = console.input("[yellow]Enter target entity (e.g. 'participant:5', 'VeriMed'): [/yellow]").strip()
            cmd_graph_path(graph_engine, src or "participant:1", tgt or "participant:5")
        elif choice == "12":
            start = console.input("[yellow]Enter start node (e.g. 'team:1', 'IIT Delhi'): [/yellow]").strip()
            cmd_graph_bfs(graph_engine, start or "team:1", max_depth=2)
        elif choice == "13":
            cmd_vector_status(vector_engine)
        elif choice == "14":
            default_q = "AI solutions for traffic congestion"
            q = console.input(f"[yellow]Enter natural language search query (default: '{default_q}'): [/yellow]").strip()
            cmd_vector_search(vector_engine, q or default_q)
        elif choice == "15":
            q = console.input("[yellow]Enter query to explain (press Enter for default): [/yellow]").strip()
            cmd_vector_explain(vector_engine, q or None)
        elif choice == "16":
            cmd_list_presets()
            pk = console.input("[yellow]Select preset (1-5, default: 5): [/yellow]").strip() or "5"
            exp = console.input("[yellow]Enable detailed explainability breakdown? (y/n, default: y): [/yellow]").strip().lower() != "n"
            q = PREDEFINED_QUERIES.get(pk, PREDEFINED_QUERIES["5"])
            cmd_unified_query(planner, q, explain=exp)
        elif choice == "17":
            track = console.input("[yellow]Relational filter - track (press Enter to skip, e.g. 'Robotics & AI'): [/yellow]").strip()
            g_op = console.input("[yellow]Graph traversal - operation (press Enter to skip, or 'college_projects'/'team_members'): [/yellow]").strip()
            g_src = console.input("[yellow]Graph source entity (e.g. 'IIT Delhi', 'team:1', press Enter to skip): [/yellow]").strip() if g_op else None
            v_text = console.input("[yellow]Vector search text (press Enter to skip, e.g. 'drone navigation'): [/yellow]").strip()
            custom_q = UnifiedQuery(
                name="custom_interactive_query",
                description="Interactive multi-paradigm query",
                relational=RelationalSubquery(filters={"track": track}) if track else None,
                graph=GraphSubquery(operation=g_op, source_entity=g_src) if g_op and g_src else None,
                vector=VectorSubquery(text=v_text) if v_text else None,
                fusion=FusionConfig(k=60, mandatory_relational_filter=True)
            )
            cmd_unified_query(planner, custom_q, explain=True)
        elif choice == "18":
            cmd_list_presets()
            pk = console.input("[yellow]Select preset to explain (1-5, default: 5): [/yellow]").strip() or "5"
            q = PREDEFINED_QUERIES.get(pk, PREDEFINED_QUERIES["5"])
            cmd_unified_query(planner, q, explain=True)
        elif choice in ("0", "exit", "quit", "q"):
            console.print("[dim]Exiting TriQuery CLI. Goodbye![/dim]\n")
            break
        else:
            console.print("[red]Invalid selection. Please try again.[/red]")


def main():
    parser = argparse.ArgumentParser(description="TriQuery Multi-Paradigm CLI (Relational + Graph + Vector + Fusion)")
    parser.add_argument("--driver", choices=["mysql", "sqlite"], default=None, help="Force database driver (mysql or sqlite)")

    subparsers = parser.add_subparsers(dest="command", help="CLI Subcommands")

    # Relational Commands
    subparsers.add_parser("status", help="Check database connection and table record counts")

    proj_parser = subparsers.add_parser("projects", help="Query projects using 5-way relational JOIN")
    proj_parser.add_argument("--college", type=str, default=None, help="Filter by college name")
    proj_parser.add_argument("--track", type=str, default=None, help="Filter by hackathon track")

    subparsers.add_parser("leaderboard", help="Display college leaderboard by total prize money")
    subparsers.add_parser("hackathons", help="Display hackathon summary metrics")

    exp_parser = subparsers.add_parser("explain", help="Inspect query execution plan with EXPLAIN")
    exp_parser.add_argument("query", nargs="?", default="SELECT * FROM projects WHERE track='Robotics & AI'", help="SQL query to explain")

    subparsers.add_parser("setup-db", help="Execute schema.sql and seed_data.sql")

    # Graph Commands
    subparsers.add_parser("graph-status", help="Display knowledge graph entity and relationship topology")

    gt_parser = subparsers.add_parser("graph-team", help="Find all participants belonging to a team")
    gt_parser.add_argument("team", nargs="?", default="NeuralVanguard", help="Team name or node_id (e.g. 'NeuralVanguard', 'team:1')")

    gc_parser = subparsers.add_parser("graph-college", help="Traverse relationships from a college to its projects")
    gc_parser.add_argument("college", nargs="?", default="IIT Delhi", help="College name or node_id (e.g. 'IIT Delhi', 'college:1')")

    gp_parser = subparsers.add_parser("graph-path", help="Find shortest relationship path between two entities")
    gp_parser.add_argument("--source", "-s", type=str, required=True, help="Source entity (e.g. 'participant:1', 'IIT Delhi')")
    gp_parser.add_argument("--target", "-t", type=str, required=True, help="Target entity (e.g. 'participant:5', 'college:5')")
    gp_parser.add_argument("--directed", action="store_true", help="Enforce strict directed edge traversal")

    gbfs_parser = subparsers.add_parser("graph-bfs", help="Explore graph via Breadth-First Search (level-order)")
    gbfs_parser.add_argument("start", nargs="?", default="team:1", help="Starting node_id or entity name")
    gbfs_parser.add_argument("--depth", "-d", type=int, default=2, help="Maximum search depth (default: 2)")

    # Vector Commands
    subparsers.add_parser("vector-status", help="Display vector similarity index status and metadata")

    vs_parser = subparsers.add_parser("vector-search", help="Execute semantic/lexical similarity search on project descriptions")
    vs_parser.add_argument("query", nargs="?", default="AI solutions for traffic congestion", help="Natural language query string")
    vs_parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of nearest neighbors to retrieve (default: 5)")
    vs_parser.add_argument("--min-score", "-m", type=float, default=0.0, help="Minimum cosine similarity score threshold (0.0 to 1.0)")
    vs_parser.add_argument("--provider", "-p", choices=["default", "tfidf", "deterministic", "sentence-transformers"], default=None, help="Embedding provider override")

    ve_parser = subparsers.add_parser("vector-explain", help="Inspect vector search complexity and cosine similarity formulation")
    ve_parser.add_argument("query", nargs="?", default="AI solutions for traffic congestion", help="Query to analyze")

    # Unified Query Planner & Fusion Commands (Milestone 4)
    subparsers.add_parser("unified-presets", help="List all 5 predefined reproducible multi-paradigm benchmark queries")

    uq_parser = subparsers.add_parser("unified-query", help="Execute unified query across Relational, Graph, and Vector engines with RRF fusion")
    uq_parser.add_argument("preset", nargs="?", default="5", help="Preset query # (1 to 5) or 'custom'")
    uq_parser.add_argument("--track", type=str, default=None, help="Relational track filter override")
    uq_parser.add_argument("--college", type=str, default=None, help="Relational college filter override")
    uq_parser.add_argument("--vector", "-v", type=str, default=None, help="Vector query text override")
    uq_parser.add_argument("--graph-op", choices=["college_projects", "team_members", "shortest_path", "bfs"], default=None, help="Graph operation")
    uq_parser.add_argument("--source", "-s", type=str, default=None, help="Graph source entity")
    uq_parser.add_argument("--target", "-t", type=str, default=None, help="Graph target entity")
    uq_parser.add_argument("--explain", "-e", action="store_true", help="Display execution plan, telemetry, and RRF evidence")
    uq_parser.add_argument("--k", type=int, default=60, help="RRF constant k (default: 60)")

    ue_parser = subparsers.add_parser("unified-explain", help="Execute query and inspect complete execution plan and fusion telemetry")
    ue_parser.add_argument("preset", nargs="?", default="5", help="Preset query # (1 to 5, default: 5)")

    args = parser.parse_args()
    rel_engine = get_relational_engine(args.driver)
    graph_engine = get_graph_engine(rel_engine)
    vector_engine = get_vector_engine(rel_engine, getattr(args, "provider", None))
    planner_k = getattr(args, "k", 60)
    planner = get_planner(rel_engine, graph_engine, vector_engine, k=planner_k)

    # Dispatch commands
    if args.command == "status":
        cmd_status(rel_engine)
    elif args.command == "projects":
        cmd_projects(rel_engine, college=args.college, track=args.track)
    elif args.command == "leaderboard":
        cmd_leaderboard(rel_engine)
    elif args.command == "hackathons":
        cmd_hackathons(rel_engine)
    elif args.command == "explain":
        cmd_explain(rel_engine, args.query)
    elif args.command == "setup-db":
        setup_database(rel_engine.conn_mgr.cfg)
    elif args.command == "graph-status":
        cmd_graph_status(graph_engine)
    elif args.command == "graph-team":
        cmd_graph_team(graph_engine, args.team)
    elif args.command == "graph-college":
        cmd_graph_college(graph_engine, args.college)
    elif args.command == "graph-path":
        cmd_graph_path(graph_engine, args.source, args.target, args.directed)
    elif args.command == "graph-bfs":
        cmd_graph_bfs(graph_engine, args.start, args.depth)
    elif args.command == "vector-status":
        cmd_vector_status(vector_engine)
    elif args.command == "vector-search":
        cmd_vector_search(vector_engine, args.query, top_k=args.top_k, min_score=args.min_score)
    elif args.command == "vector-explain":
        cmd_vector_explain(vector_engine, args.query)
    elif args.command == "unified-presets":
        cmd_list_presets()
    elif args.command == "unified-query":
        # Check if dynamic overrides were provided
        has_overrides = any([args.track, args.college, args.vector, args.graph_op])
        if has_overrides:
            dyn_query = UnifiedQuery(
                name="cli_dynamic_query",
                description="Custom query constructed from CLI arguments",
                relational=RelationalSubquery(filters={"track": args.track} if args.track else {}, college_name=args.college) if (args.track or args.college) else None,
                graph=GraphSubquery(operation=args.graph_op, source_entity=args.source, target_entity=args.target) if args.graph_op else None,
                vector=VectorSubquery(text=args.vector) if args.vector else None,
                fusion=FusionConfig(k=args.k, mandatory_relational_filter=True),
            )
            cmd_unified_query(planner, dyn_query, explain=args.explain)
        else:
            preset_q = PREDEFINED_QUERIES.get(args.preset, PREDEFINED_QUERIES["5"])
            cmd_unified_query(planner, preset_q, explain=args.explain)
    elif args.command == "unified-explain":
        preset_q = PREDEFINED_QUERIES.get(args.preset, PREDEFINED_QUERIES["5"])
        cmd_unified_query(planner, preset_q, explain=True)
    else:
        interactive_menu(rel_engine, graph_engine, vector_engine, planner)


if __name__ == "__main__":
    main()


