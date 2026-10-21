"""
Unified Query Explainability Module for TriQuery (Milestone 4).
Generates structured telemetry reports, engine selection rationales,
ordered plan breakdowns, and reciprocal rank fusion evidence for viva inspection.
"""

from typing import Any, Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.query import UnifiedQuery
from src.core.types import EngineType, QueryExplanation, UnifiedRecord
from src.fusion.rrf import ReciprocalRankFusion
from src.planner.planner import UnifiedExecutionResult


class QueryExplainer:
    """
    Transforms UnifiedExecutionResult and UnifiedQuery into human-readable
    and machine-readable explanation models.
    """

    @staticmethod
    def build_explanation(
        result: UnifiedExecutionResult, query: UnifiedQuery
    ) -> QueryExplanation:
        """Constructs a typed QueryExplanation model."""
        plan_desc_lines = []
        for step in result.plan.steps:
            deps = f" [depends on steps {step.depends_on_steps}]" if step.depends_on_steps else " [independent]"
            plan_desc_lines.append(f"Step {step.step_id} ({step.engine.value}): {step.description}{deps}")

        ranking_lines = []
        if len(result.plan.required_engines) > 1:
            fusion_info = ReciprocalRankFusion.get_algorithm_explanation()
            ranking_lines.append(f"Algorithm: {fusion_info['name']} (k={query.fusion.k if query.fusion else 60})")
            ranking_lines.append(f"Formula: {fusion_info['formula']}")
            ranking_lines.append(f"Mandatory SQL Filter Guard: {query.fusion.mandatory_relational_filter if query.fusion else True}")
        else:
            ranking_lines.append(f"Single Engine Mode ({result.plan.required_engines[0].value}): Ordinal ranking preserved directly.")

        # Map fused items to UnifiedRecord
        unified_records: List[UnifiedRecord] = []
        for item in result.fused_results:
            unified_records.append(
                UnifiedRecord(
                    entity_id=item.entity_id,
                    entity_type="project" if item.entity_id.startswith("project:") else "entity",
                    title=item.title,
                    attributes=item.metadata,
                    relational_matched=EngineType.RELATIONAL in item.participating_engines,
                    graph_matched=EngineType.GRAPH in item.participating_engines,
                    vector_score=item.engine_scores.get(EngineType.VECTOR.value),
                    final_rank_score=item.rrf_score,
                    reason_for_inclusion=(
                        f"Ranked #{item.final_rank} via RRF score {item.rrf_score:.6f} "
                        f"across {[e.value for e in item.participating_engines]}"
                    ),
                )
            )

        return QueryExplanation(
            query_id=query.query_id,
            query_text=query.description or query.name,
            engines_used=result.plan.required_engines,
            total_execution_time_ms=result.total_latency_ms,
            engine_timings=result.stage_latencies_ms,
            intermediate_counts=result.stage_record_counts,
            plan_explanation="\n".join(plan_desc_lines),
            ranking_explanation="\n".join(ranking_lines),
            records=unified_records,
        )

    @staticmethod
    def render_rich_explanation(
        result: UnifiedExecutionResult, query: UnifiedQuery, console: Console
    ):
        """Renders formatted Rich tables and panels for CLI inspection."""
        console.print(f"\n[bold cyan]TriQuery Unified Execution Plan & Explainability[/bold cyan]")
        console.print(f"Query ID   : [yellow]{query.query_id}[/yellow]")
        console.print(f"Query Name : [bold white]{query.name}[/bold white]")
        console.print(f"Description: [dim]{query.description or 'Custom multi-paradigm query'}[/dim]\n")

        # 1. Engine Selection Rationale Table
        engine_table = Table(title="1. Engine Selection & Dispatch Rationale")
        engine_table.add_column("Engine", style="cyan")
        engine_table.add_column("Status", style="bold green")
        engine_table.add_column("Selection Rationale / Trigger", style="bold white")

        rel_selected = query.relational is not None
        engine_table.add_row(
            "Relational (MySQL/SQLite)",
            "[green]SELECTED[/green]" if rel_selected else "[dim]SKIPPED[/dim]",
            f"Filter on {query.relational.filters or query.relational.college_name or 'projects'}" if rel_selected else "No relational constraints specified"
        )

        graph_selected = query.graph is not None
        engine_table.add_row(
            "Graph (NetworkX)",
            "[green]SELECTED[/green]" if graph_selected else "[dim]SKIPPED[/dim]",
            f"Traverse {query.graph.operation} from '{query.graph.source_entity}'" if graph_selected else "No graph relationship traversal specified"
        )

        vector_selected = query.vector is not None
        engine_table.add_row(
            "Vector (Similarity Search)",
            "[green]SELECTED[/green]" if vector_selected else "[dim]SKIPPED[/dim]",
            f"Semantic similarity for: \"{query.vector.text}\"" if vector_selected else "No natural language query specified"
        )
        console.print(engine_table)
        console.print()

        # 2. Ordered Execution Plan Steps Table
        plan_table = Table(title="2. Ordered Execution Plan Steps")
        plan_table.add_column("Step #", style="dim", justify="right")
        plan_table.add_column("Target Engine", style="cyan")
        plan_table.add_column("Operation", style="magenta")
        plan_table.add_column("Dependencies", style="yellow")
        plan_table.add_column("Step Description", style="bold white")

        for s in result.plan.steps:
            dep_str = f"Steps {s.depends_on_steps}" if s.depends_on_steps else "None (Initial)"
            plan_table.add_row(
                str(s.step_id),
                s.engine.value.upper(),
                s.target_operation,
                dep_str,
                s.description
            )
        console.print(plan_table)
        console.print()

        # 3. Measured Stage Latency & Counts Table
        telemetry_table = Table(title="3. Measured Stage Latency & Intermediate Record Counts")
        telemetry_table.add_column("Pipeline Stage", style="cyan")
        telemetry_table.add_column("Execution Time (ms)", style="bold green", justify="right")
        telemetry_table.add_column("Records Produced", style="bold yellow", justify="right")
        telemetry_table.add_column("Timing Type", style="dim")

        for stage, dur in result.stage_latencies_ms.items():
            cnt = result.stage_record_counts.get(stage, 0)
            telemetry_table.add_row(
                stage.capitalize(),
                f"{dur:.3f} ms",
                str(cnt),
                "Measured (time.perf_counter)"
            )
        telemetry_table.add_row(
            "[bold]Total End-to-End[/bold]",
            f"[bold green]{result.total_latency_ms:.3f} ms[/bold green]",
            f"[bold yellow]{len(result.fused_results)}[/bold yellow]",
            "Cumulative Measured"
        )
        console.print(telemetry_table)
        console.print()

        # 4. Result Fusion & Ranking Evidence Table
        if len(result.plan.required_engines) > 1:
            fusion_table = Table(title=f"4. Reciprocal Rank Fusion (RRF) Evidence (k={query.fusion.k if query.fusion else 60})")
            fusion_table.add_column("Final Rank", style="dim", justify="right")
            fusion_table.add_column("RRF Score", style="bold green", justify="right")
            fusion_table.add_column("Entity ID", style="cyan")
            fusion_table.add_column("Project Title", style="bold white")
            fusion_table.add_column("Engine Contributions", style="magenta")
            fusion_table.add_column("Individual Engine Ranks", style="yellow")

            for item in result.fused_results:
                engines_str = ", ".join([e.value for e in item.participating_engines])
                ranks_str = ", ".join([f"{k}: #{v}" for k, v in item.engine_ranks.items()])
                fusion_table.add_row(
                    str(item.final_rank),
                    f"{item.rrf_score:.6f}",
                    item.entity_id,
                    item.title[:35] + ("..." if len(item.title) > 35 else ""),
                    engines_str,
                    ranks_str
                )
            console.print(fusion_table)
            console.print()

        # 5. Viva Defense Notes Panel
        console.print(Panel(
            "[bold white]Why Reciprocal Rank Fusion Over Linear Score Combination?[/bold white]\n"
            "- [green]Incommensurable Scales[/green]: Relational queries return unranked sets; Graph returns integer hop distances; Vector returns continuous cosine similarities. Direct linear combination (e.g. cosine + hops) is mathematically uncalibrated.\n"
            "- [green]Monotonic Rank Positions[/green]: RRF operates exclusively on ordinal rank positions, neutralizing scale divergence.\n"
            "- [green]Deterministic Plan Dependencies[/green]: Steps execute with strict dependency barriers, ensuring mandatory SQL filters prune candidates before final consensus ranking.",
            title="DBMS Viva Defense Note"
        ))
        console.print()
