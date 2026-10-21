"""
Unified Query Planner for TriQuery (Milestone 4).
Analyzes declarative multi-paradigm queries, constructs deterministic execution plans,
coordinates engine execution, and routes candidate sets to the result fusion layer.
"""

import time
import uuid
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from src.core.query import UnifiedQuery
from src.core.types import EngineResult, EngineType, QueryPlan, QueryPlanStep
from src.engines.graph.engine import GraphEngine
from src.engines.relational.engine import RelationalEngine
from src.engines.vector.engine import VectorEngine
from src.fusion.rrf import FusedItem, RankedItem, ReciprocalRankFusion


class UnifiedExecutionResult(BaseModel):
    """Encapsulates the complete result of executing a UnifiedQuery across engines."""
    query_id: str
    query_name: str
    success: bool
    plan: QueryPlan
    fused_results: List[FusedItem] = Field(default_factory=list)
    raw_engine_results: Dict[str, Any] = Field(default_factory=dict)
    stage_latencies_ms: Dict[str, float] = Field(default_factory=dict)
    stage_record_counts: Dict[str, int] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    error: Optional[str] = None


class UnifiedQueryPlanner:
    """
    Coordinates multi-engine query planning, step dependency ordering,
    selective engine dispatch, and result fusion.
    """

    def __init__(
        self,
        relational_engine: Optional[RelationalEngine] = None,
        graph_engine: Optional[GraphEngine] = None,
        vector_engine: Optional[VectorEngine] = None,
        fusion_engine: Optional[ReciprocalRankFusion] = None,
    ):
        self.relational_engine = relational_engine or RelationalEngine()
        self.graph_engine = graph_engine or GraphEngine(relational_engine=self.relational_engine)
        self.vector_engine = vector_engine or VectorEngine(relational_engine=self.relational_engine)
        self.default_fusion = fusion_engine or ReciprocalRankFusion(k=60)

    # -------------------------------------------------------------------------
    # Plan Construction
    # -------------------------------------------------------------------------

    def create_plan(self, query: UnifiedQuery) -> QueryPlan:
        """
        Constructs an explicit QueryPlan with ordered steps and dependencies.
        Validates that at least one engine subquery is provided.
        """
        required_engines: List[EngineType] = []
        steps: List[QueryPlanStep] = []
        step_id = 1
        search_step_ids: List[int] = []

        # 1. Inspect Relational Subquery
        if query.relational is not None:
            required_engines.append(EngineType.RELATIONAL)
            desc = "Execute SQL selection/join/aggregation filter"
            op = "sql_query"
            if query.relational.raw_sql:
                op = "raw_sql"
                desc = f"Execute custom SQL: {query.relational.raw_sql[:40]}..."
            elif query.relational.aggregation:
                op = f"aggregation_{query.relational.aggregation}"
                desc = f"Execute analytical aggregation: {query.relational.aggregation}"
            elif query.relational.college_name:
                op = "filter_by_college"
                desc = f"Filter projects by college: '{query.relational.college_name}'"
            elif query.relational.filters:
                op = "relational_filter"
                desc = f"Filter projects by predicates: {query.relational.filters}"

            steps.append(
                QueryPlanStep(
                    step_id=step_id,
                    engine=EngineType.RELATIONAL,
                    description=desc,
                    target_operation=op,
                    parameters=query.relational.model_dump(),
                    depends_on_steps=[],
                )
            )
            search_step_ids.append(step_id)
            step_id += 1

        # 2. Inspect Graph Subquery
        if query.graph is not None:
            required_engines.append(EngineType.GRAPH)
            g_op = query.graph.operation
            steps.append(
                QueryPlanStep(
                    step_id=step_id,
                    engine=EngineType.GRAPH,
                    description=f"Traverse knowledge graph ({g_op}) from '{query.graph.source_entity}'",
                    target_operation=f"graph_{g_op}",
                    parameters=query.graph.model_dump(),
                    depends_on_steps=[],
                )
            )
            search_step_ids.append(step_id)
            step_id += 1

        # 3. Inspect Vector Subquery
        if query.vector is not None:
            required_engines.append(EngineType.VECTOR)
            steps.append(
                QueryPlanStep(
                    step_id=step_id,
                    engine=EngineType.VECTOR,
                    description=f"Perform vector similarity search for query: '{query.vector.text[:40]}...'",
                    target_operation="vector_search",
                    parameters=query.vector.model_dump(),
                    depends_on_steps=[],
                )
            )
            search_step_ids.append(step_id)
            step_id += 1

        if not required_engines:
            raise ValueError("UnifiedQuery must specify at least one subquery (relational, graph, or vector).")

        # 4. If more than 1 engine is required, add a Result Fusion Step
        if len(required_engines) > 1:
            fusion_k = query.fusion.k if query.fusion else 60
            steps.append(
                QueryPlanStep(
                    step_id=step_id,
                    engine=EngineType.HYBRID,
                    description=f"Combine candidate entity rankings via Reciprocal Rank Fusion (k={fusion_k})",
                    target_operation="rrf_fusion",
                    parameters={"k": fusion_k, "mandatory_relational": query.fusion.mandatory_relational_filter},
                    depends_on_steps=search_step_ids,
                )
            )

        note = (
            f"Plan targets {len(required_engines)} engine(s): {[e.value for e in required_engines]}. "
            f"Execution order determined by subquery dependencies with zero redundant calls."
        )

        return QueryPlan(
            query_id=query.query_id,
            natural_query=query.description or query.name,
            required_engines=required_engines,
            steps=steps,
            estimated_cost_note=note,
        )

    # -------------------------------------------------------------------------
    # Plan Execution
    # -------------------------------------------------------------------------

    def execute_plan(
        self,
        query: UnifiedQuery,
        plan: Optional[QueryPlan] = None
    ) -> UnifiedExecutionResult:
        """
        Executes the planned query steps, recording exact per-stage latencies,
        record counts, and applying RRF fusion where required.
        """
        start_total = time.perf_counter()
        if plan is None:
            try:
                plan = self.create_plan(query)
            except Exception as exc:
                return UnifiedExecutionResult(
                    query_id=query.query_id,
                    query_name=query.name,
                    success=False,
                    plan=QueryPlan(query_id=query.query_id, natural_query=query.name, required_engines=[], steps=[]),
                    error=str(exc),
                )

        stage_latencies: Dict[str, float] = {}
        stage_counts: Dict[str, int] = {}
        raw_results: Dict[str, Any] = {}
        rankings: Dict[EngineType, List[RankedItem]] = {}
        mandatory_entity_ids: Optional[Set[str]] = None

        try:
            # 1. Execute Relational Step if planned
            if query.relational is not None:
                t0 = time.perf_counter()
                rel_items, rel_raw = self._execute_relational_subquery(query.relational)
                dur = (time.perf_counter() - t0) * 1000.0

                stage_latencies["relational"] = round(dur, 3)
                stage_counts["relational"] = len(rel_items)
                raw_results["relational"] = rel_raw
                rankings[EngineType.RELATIONAL] = rel_items

                if query.fusion and query.fusion.mandatory_relational_filter:
                    mandatory_entity_ids = {item.entity_id for item in rel_items}

            # 2. Execute Graph Step if planned
            if query.graph is not None:
                t0 = time.perf_counter()
                graph_items, graph_raw = self._execute_graph_subquery(query.graph)
                dur = (time.perf_counter() - t0) * 1000.0

                stage_latencies["graph"] = round(dur, 3)
                stage_counts["graph"] = len(graph_items)
                raw_results["graph"] = graph_raw
                rankings[EngineType.GRAPH] = graph_items

            # 3. Execute Vector Step if planned
            if query.vector is not None:
                t0 = time.perf_counter()
                vector_items, vector_raw = self._execute_vector_subquery(query.vector)
                dur = (time.perf_counter() - t0) * 1000.0

                stage_latencies["vector"] = round(dur, 3)
                stage_counts["vector"] = len(vector_items)
                raw_results["vector"] = vector_raw
                rankings[EngineType.VECTOR] = vector_items

            # 4. Result Fusion / Aggregation
            fused_items: List[FusedItem] = []
            if len(plan.required_engines) > 1:
                t0 = time.perf_counter()
                fusion_k = query.fusion.k if query.fusion else 60
                fusion_runner = ReciprocalRankFusion(k=fusion_k)
                fused_items = fusion_runner.fuse(
                    rankings=rankings,
                    mandatory_entity_ids=mandatory_entity_ids if query.fusion.mandatory_relational_filter else None,
                )
                dur = (time.perf_counter() - t0) * 1000.0
                stage_latencies["fusion"] = round(dur, 3)
                stage_counts["fusion"] = len(fused_items)
            else:
                # Single-engine execution: map items directly to FusedItem
                only_engine = plan.required_engines[0]
                engine_items = rankings.get(only_engine, [])
                for idx, it in enumerate(engine_items, start=1):
                    fused_items.append(
                        FusedItem(
                            entity_id=it.entity_id,
                            title=it.title,
                            rrf_score=it.score if it.score is not None else 1.0,
                            final_rank=idx,
                            participating_engines=[only_engine],
                            engine_ranks={only_engine.value: it.rank},
                            engine_scores={only_engine.value: it.score},
                            metadata=it.metadata,
                        )
                    )
                stage_counts["final"] = len(fused_items)

            total_lat = (time.perf_counter() - start_total) * 1000.0

            return UnifiedExecutionResult(
                query_id=query.query_id,
                query_name=query.name,
                success=True,
                plan=plan,
                fused_results=fused_items,
                raw_engine_results=raw_results,
                stage_latencies_ms=stage_latencies,
                stage_record_counts=stage_counts,
                total_latency_ms=round(total_lat, 3),
            )
        except Exception as exc:
            total_lat = (time.perf_counter() - start_total) * 1000.0
            return UnifiedExecutionResult(
                query_id=query.query_id,
                query_name=query.name,
                success=False,
                plan=plan,
                fused_results=[],
                raw_engine_results=raw_results,
                stage_latencies_ms=stage_latencies,
                stage_record_counts=stage_counts,
                total_latency_ms=round(total_lat, 3),
                error=str(exc),
            )

    # -------------------------------------------------------------------------
    # Engine Dispatch Adapters
    # -------------------------------------------------------------------------

    def _execute_relational_subquery(
        self, subquery
    ) -> (List[RankedItem], Dict[str, Any]):
        """Executes relational operations and maps results to RankedItems."""
        items: List[RankedItem] = []

        if subquery.raw_sql:
            res = self.relational_engine.execute(subquery.raw_sql)
            records = res.data if res.success else []
        elif subquery.college_name:
            res = self.relational_engine.find_projects_by_college(subquery.college_name)
            records = res.data if res.success else []
        elif subquery.filters and "track" in subquery.filters:
            res = self.relational_engine.get_projects_with_details(track=subquery.filters["track"])
            records = res.data if res.success else []
        else:
            res = self.relational_engine.get_projects_with_details()
            records = res.data if res.success else []

        for idx, r in enumerate(records, start=1):
            pid = r.get("project_id")
            eid = f"project:{pid}" if pid else f"relational:{idx}"
            title = r.get("title") or r.get("project_title") or ""
            items.append(
                RankedItem(
                    entity_id=eid,
                    rank=idx,
                    score=1.0,  # Relational inclusion is binary boolean match
                    engine=EngineType.RELATIONAL,
                    title=title,
                    metadata=r,
                )
            )

        return items, {"record_count": len(records), "data": records}

    def _execute_graph_subquery(
        self, subquery
    ) -> (List[RankedItem], Dict[str, Any]):
        """Executes graph traversals and maps results to RankedItems."""
        items: List[RankedItem] = []
        op = subquery.operation

        if op == "shortest_path":
            path_res = self.graph_engine.find_shortest_path(
                subquery.source_entity, subquery.target_entity, directed=subquery.directed
            )
            if path_res.found:
                for idx, node in enumerate(path_res.path, start=1):
                    node_data = self.graph_engine.graph.nodes.get(node, {})
                    label = node_data.get("label", node)
                    items.append(
                        RankedItem(
                            entity_id=node,
                            rank=idx,
                            score=round(1.0 / idx, 4),  # Inverse hop score
                            engine=EngineType.GRAPH,
                            title=label,
                            metadata={"node_type": node_data.get("node_type", "")},
                        )
                    )
            return items, {"found": path_res.found, "length": path_res.length, "path": path_res.path}

        elif op == "college_projects":
            res = self.graph_engine.get_college_projects(subquery.source_entity)
            if res.success:
                for idx, r in enumerate(res.data, start=1):
                    pid = r.get("project_id")
                    items.append(
                        RankedItem(
                            entity_id=f"project:{pid}",
                            rank=idx,
                            score=1.0,
                            engine=EngineType.GRAPH,
                            title=r.get("title", ""),
                            metadata=r,
                        )
                    )
            return items, {"record_count": len(items), "data": res.data if res.success else []}

        elif op == "team_members":
            res = self.graph_engine.get_team_members(subquery.source_entity)
            if res.success:
                for idx, r in enumerate(res.data, start=1):
                    pid = r.get("participant_id")
                    items.append(
                        RankedItem(
                            entity_id=f"participant:{pid}",
                            rank=idx,
                            score=1.0,
                            engine=EngineType.GRAPH,
                            title=r.get("full_name", ""),
                            metadata=r,
                        )
                    )
            return items, {"record_count": len(items), "data": res.data if res.success else []}

        elif op == "bfs":
            visited = self.graph_engine.bfs_traversal(subquery.source_entity, max_depth=subquery.max_depth)
            for idx, row in enumerate(visited, start=1):
                items.append(
                    RankedItem(
                        entity_id=row["node_id"],
                        rank=idx,
                        score=round(1.0 / max(1, row["depth"] + 1), 4),
                        engine=EngineType.GRAPH,
                        title=row.get("label", row["node_id"]),
                        metadata=row,
                    )
                )
            return items, {"record_count": len(items), "data": visited}

        return items, {"error": f"Unknown graph operation '{op}'"}

    def _execute_vector_subquery(
        self, subquery
    ) -> (List[RankedItem], Dict[str, Any]):
        """Executes vector similarity search and maps results to RankedItems."""
        items: List[RankedItem] = []
        res = self.vector_engine.search(
            subquery.text,
            top_k=subquery.top_k,
            min_score=subquery.min_score,
        )

        if res.success:
            for idx, r in enumerate(res.data, start=1):
                items.append(
                    RankedItem(
                        entity_id=r["entity_id"],
                        rank=r.get("rank", idx),
                        score=r.get("score"),
                        engine=EngineType.VECTOR,
                        title=r.get("title", ""),
                        metadata=r,
                    )
                )

        return items, {"record_count": len(items), "data": res.data if res.success else []}
