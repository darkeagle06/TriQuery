"""
Graph Engine for TriQuery using NetworkX.
Constructs an in-memory knowledge graph directly from verified relational records,
enforcing foreign-key relationship integrity without synthetic or speculative links.
Provides BFS, DFS, shortest path, and neighborhood queries compatible with BaseEngine.
"""

import collections
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import networkx as nx

from src.core.types import EngineExecutionMetadata, EngineResult, EngineType
from src.engines.base import BaseEngine
from src.engines.graph.types import EdgeType, GraphEdge, GraphNode, NodeType, PathResult, PathStep
from src.engines.relational.engine import RelationalEngine


class GraphEngine(BaseEngine):
    """
    NetworkX-backed Graph Engine for TriQuery.
    Maintains a directed graph (DiGraph) representing entities as nodes
    and validated relational constraints as typed edges.
    """

    def __init__(
        self,
        relational_engine: Optional[RelationalEngine] = None,
        auto_build: bool = True
    ):
        self.relational_engine = relational_engine or RelationalEngine()
        self._graph = nx.DiGraph()
        self._label_to_id: Dict[str, str] = {}
        self._last_built_at: Optional[float] = None

        if auto_build:
            self.build_from_relational()

    @property
    def engine_type(self) -> EngineType:
        return EngineType.GRAPH

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def is_healthy(self) -> bool:
        """Checks if graph is loaded with nodes and relational source is reachable."""
        return isinstance(self._graph, nx.DiGraph) and self.node_count > 0

    # -------------------------------------------------------------------------
    # Graph Construction & Relational Ingestion
    # -------------------------------------------------------------------------

    def build_from_relational(self) -> Dict[str, int]:
        """
        Extracts verified relational records and constructs the knowledge graph.
        Never infers or synthesizes edges beyond explicit relational foreign keys.
        """
        self._graph.clear()
        self._label_to_id.clear()

        # 1. Fetch Colleges
        colleges = self.relational_engine.conn_mgr.execute_query(
            "SELECT college_id, name, city, state, country, established_year FROM colleges"
        )
        for c in colleges:
            node_id = f"college:{c['college_id']}"
            self._add_node(node_id, NodeType.COLLEGE, c["name"], c)

        # 2. Fetch Hackathons
        hackathons = self.relational_engine.conn_mgr.execute_query(
            "SELECT hackathon_id, name, edition_year, organizer, city, theme, total_prize_pool FROM hackathons"
        )
        for h in hackathons:
            node_id = f"hackathon:{h['hackathon_id']}"
            label = f"{h['name']} ({h['edition_year']})"
            self._add_node(node_id, NodeType.HACKATHON, label, h)

        # 3. Fetch Teams & Affiliations (Team -> College)
        teams = self.relational_engine.conn_mgr.execute_query(
            "SELECT team_id, team_name, college_id FROM teams"
        )
        for t in teams:
            team_node = f"team:{t['team_id']}"
            self._add_node(team_node, NodeType.TEAM, t["team_name"], t)
            # Edge: (:Team)-[:AFFILIATED_WITH]->(:College)
            college_node = f"college:{t['college_id']}"
            if self._graph.has_node(college_node):
                self._add_edge(team_node, college_node, EdgeType.AFFILIATED_WITH)

        # 4. Fetch Participants & Enrollment (Participant -> College)
        participants = self.relational_engine.conn_mgr.execute_query(
            "SELECT participant_id, full_name, email, college_id, graduation_year FROM participants"
        )
        for p in participants:
            p_node = f"participant:{p['participant_id']}"
            self._add_node(p_node, NodeType.PARTICIPANT, p["full_name"], p)
            # Edge: (:Participant)-[:ENROLLED_AT]->(:College)
            college_node = f"college:{p['college_id']}"
            if self._graph.has_node(college_node):
                self._add_edge(p_node, college_node, EdgeType.ENROLLED_AT)

        # 5. Fetch Team Memberships (Participant -> Team)
        memberships = self.relational_engine.conn_mgr.execute_query(
            "SELECT team_id, participant_id, role, joined_at FROM team_members"
        )
        for m in memberships:
            p_node = f"participant:{m['participant_id']}"
            t_node = f"team:{m['team_id']}"
            if self._graph.has_node(p_node) and self._graph.has_node(t_node):
                # Edge: (:Participant)-[:MEMBER_OF]->(:Team)
                self._add_edge(
                    p_node,
                    t_node,
                    EdgeType.MEMBER_OF,
                    role=m.get("role", "Developer"),
                    joined_at=str(m.get("joined_at", ""))
                )

        # 6. Fetch Projects (Team -> Project, Project -> Hackathon)
        projects = self.relational_engine.conn_mgr.execute_query(
            "SELECT project_id, team_id, hackathon_id, title, track, short_summary, tech_stack FROM projects"
        )
        for pr in projects:
            pr_node = f"project:{pr['project_id']}"
            self._add_node(pr_node, NodeType.PROJECT, pr["title"], pr)
            # Edge: (:Team)-[:SUBMITTED]->(:Project)
            t_node = f"team:{pr['team_id']}"
            if self._graph.has_node(t_node):
                self._add_edge(t_node, pr_node, EdgeType.SUBMITTED)
            # Edge: (:Project)-[:COMPETED_AT]->(:Hackathon)
            h_node = f"hackathon:{pr['hackathon_id']}"
            if self._graph.has_node(h_node):
                self._add_edge(pr_node, h_node, EdgeType.COMPETED_AT)

        # 7. Fetch Awards (Project -> Award, Award -> Hackathon)
        awards = self.relational_engine.conn_mgr.execute_query(
            "SELECT award_id, project_id, hackathon_id, prize_category, rank_position, cash_prize FROM awards"
        )
        for a in awards:
            a_node = f"award:{a['award_id']}"
            label = f"{a['prize_category']} (Rank #{a['rank_position']})"
            self._add_node(a_node, NodeType.AWARD, label, a)
            # Edge: (:Project)-[:WON_AWARD]->(:Award)
            pr_node = f"project:{a['project_id']}"
            if self._graph.has_node(pr_node):
                self._add_edge(
                    pr_node,
                    a_node,
                    EdgeType.WON_AWARD,
                    rank=a["rank_position"],
                    prize_money=float(a.get("cash_prize", 0.0))
                )
            # Edge: (:Award)-[:PRESENTED_AT]->(:Hackathon)
            h_node = f"hackathon:{a['hackathon_id']}"
            if self._graph.has_node(h_node):
                self._add_edge(a_node, h_node, EdgeType.PRESENTED_AT)

        self._last_built_at = time.time()
        return {"nodes": self.node_count, "edges": self.edge_count}

    def _add_node(self, node_id: str, node_type: NodeType, label: str, attributes: Dict[str, Any]):
        """Adds a node with metadata to the graph and indexes its label."""
        self._graph.add_node(
            node_id,
            node_type=node_type.value,
            label=label,
            **attributes
        )
        # Case-insensitive label lookup index
        self._label_to_id[label.lower()] = node_id
        # Also index plain ID (e.g. "team:1")
        self._label_to_id[node_id.lower()] = node_id

    def _add_edge(self, source: str, target: str, edge_type: EdgeType, **attrs):
        """Adds a validated relationship edge."""
        self._graph.add_edge(
            source,
            target,
            edge_type=edge_type.value,
            **attrs
        )

    # -------------------------------------------------------------------------
    # Identifier Resolution
    # -------------------------------------------------------------------------

    def resolve_node_id(self, identifier: Union[str, int]) -> Optional[str]:
        """
        Resolves an entity identifier or natural name into an internal node_id.
        Examples:
            'college:1' -> 'college:1'
            'IIT Delhi' -> 'college:1'
            'AeroVision' -> 'project:1'
        """
        ident_str = str(identifier).strip()
        if self._graph.has_node(ident_str):
            return ident_str

        # If it matches an explicit 'type:id' pattern, do not perform fuzzy substring matching
        if ":" in ident_str:
            prefix, _ = ident_str.split(":", 1)
            if prefix.lower() in {nt.value for nt in NodeType}:
                return None

        # Case-insensitive exact label lookup
        lower_ident = ident_str.lower()
        if lower_ident in self._label_to_id:
            return self._label_to_id[lower_ident]

        # Substring search across natural labels only (excluding 'type:id' keys)
        for label, nid in self._label_to_id.items():
            if ":" not in label and (lower_ident in label or label in lower_ident):
                return nid

        return None

    def get_node_data(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Returns node attributes dictionary or None if not found."""
        if not self._graph.has_node(node_id):
            return None
        return dict(self._graph.nodes[node_id])

    # -------------------------------------------------------------------------
    # Neighborhood & Traversal Operations
    # -------------------------------------------------------------------------

    def get_neighbors(
        self,
        node_identifier: str,
        direction: str = "both",
        edge_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns adjacent nodes and connecting edge attributes.
        direction: 'out' (outgoing), 'in' (incoming), or 'both' (undirected).
        """
        node_id = self.resolve_node_id(node_identifier)
        if not node_id:
            return []

        neighbors = []

        # Outgoing edges: (node_id) -> (v)
        if direction in ("out", "both"):
            for _, target, edge_data in self._graph.out_edges(node_id, data=True):
                if edge_type and edge_data.get("edge_type") != edge_type:
                    continue
                target_data = self._graph.nodes[target]
                neighbors.append({
                    "neighbor_id": target,
                    "neighbor_type": target_data.get("node_type"),
                    "neighbor_label": target_data.get("label"),
                    "edge_type": edge_data.get("edge_type"),
                    "direction": "outgoing",
                    "edge_attributes": edge_data,
                    "neighbor_attributes": target_data
                })

        # Incoming edges: (u) -> (node_id)
        if direction in ("in", "both"):
            for source, _, edge_data in self._graph.in_edges(node_id, data=True):
                if edge_type and edge_data.get("edge_type") != edge_type:
                    continue
                source_data = self._graph.nodes[source]
                neighbors.append({
                    "neighbor_id": source,
                    "neighbor_type": source_data.get("node_type"),
                    "neighbor_label": source_data.get("label"),
                    "edge_type": edge_data.get("edge_type"),
                    "direction": "incoming",
                    "edge_attributes": edge_data,
                    "neighbor_attributes": source_data
                })

        return neighbors

    def bfs_traversal(
        self,
        start_identifier: str,
        max_depth: Optional[int] = None,
        directed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Executes Breadth-First Search (BFS) starting from start_node.
        Returns nodes visited in level-order with depth and predecessor info.
        Time Complexity: O(|V| + |E|), Space Complexity: O(|V|).
        """
        start_node = self.resolve_node_id(start_identifier)
        if not start_node or not self._graph.has_node(start_node):
            return []

        visited: Set[str] = {start_node}
        queue = collections.deque([(start_node, 0, None, None)])  # (node, depth, parent, edge_type)
        traversal_order = []

        active_graph = self._graph if directed else self._graph.to_undirected(as_view=True)

        while queue:
            current, depth, parent, edge_label = queue.popleft()
            node_data = self._graph.nodes[current]

            traversal_order.append({
                "node_id": current,
                "node_type": node_data.get("node_type"),
                "label": node_data.get("label"),
                "depth": depth,
                "parent_id": parent,
                "relationship": edge_label,
                "attributes": node_data
            })

            if max_depth is not None and depth >= max_depth:
                continue

            # Traverse adjacent neighbors
            for neighbor in active_graph.neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    # Determine edge type between current and neighbor
                    edge_type = self._get_edge_label_between(current, neighbor)
                    queue.append((neighbor, depth + 1, current, edge_type))

        return traversal_order

    def dfs_traversal(
        self,
        start_identifier: str,
        max_depth: Optional[int] = None,
        directed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Executes Depth-First Search (DFS) starting from start_node.
        Explores branches as deeply as possible before backtracking.
        Time Complexity: O(|V| + |E|), Space Complexity: O(|V|).
        """
        start_node = self.resolve_node_id(start_identifier)
        if not start_node or not self._graph.has_node(start_node):
            return []

        visited: Set[str] = set()
        traversal_order = []
        active_graph = self._graph if directed else self._graph.to_undirected(as_view=True)

        def _dfs(current: str, depth: int, parent: Optional[str], edge_label: Optional[str]):
            visited.add(current)
            node_data = self._graph.nodes[current]
            traversal_order.append({
                "node_id": current,
                "node_type": node_data.get("node_type"),
                "label": node_data.get("label"),
                "depth": depth,
                "parent_id": parent,
                "relationship": edge_label,
                "attributes": node_data
            })

            if max_depth is not None and depth >= max_depth:
                return

            for neighbor in active_graph.neighbors(current):
                if neighbor not in visited:
                    rel = self._get_edge_label_between(current, neighbor)
                    _dfs(neighbor, depth + 1, current, rel)

        _dfs(start_node, 0, None, None)
        return traversal_order

    def _get_edge_label_between(self, u: str, v: str) -> str:
        """Helper to find the edge type between two nodes regardless of direction."""
        if self._graph.has_edge(u, v):
            return self._graph.edges[u, v].get("edge_type", "CONNECTED_TO")
        elif self._graph.has_edge(v, u):
            return self._graph.edges[v, u].get("edge_type", "CONNECTED_TO")
        return "ADJACENT"

    # -------------------------------------------------------------------------
    # Shortest Path Finding
    # -------------------------------------------------------------------------

    def find_shortest_path(
        self,
        source_identifier: str,
        target_identifier: str,
        directed: bool = False
    ) -> PathResult:
        """
        Finds the shortest relationship path between two entities using BFS pathfinding.
        Handles missing nodes and disconnected components safely.
        Time Complexity: O(|V| + |E|).
        """
        src = self.resolve_node_id(source_identifier)
        tgt = self.resolve_node_id(target_identifier)

        if not src:
            return PathResult(source=source_identifier, target=target_identifier, found=False, message=f"Source entity not found: '{source_identifier}'")
        if not tgt:
            return PathResult(source=source_identifier, target=target_identifier, found=False, message=f"Target entity not found: '{target_identifier}'")

        if src == tgt:
            return PathResult(
                source=src,
                target=tgt,
                path=[src],
                length=0,
                steps=[],
                found=True,
                message="Source and target are the same entity."
            )

        active_graph = self._graph if directed else self._graph.to_undirected(as_view=True)

        try:
            raw_path = nx.shortest_path(active_graph, source=src, target=tgt)
        except nx.NetworkXNoPath:
            return PathResult(
                source=src,
                target=tgt,
                path=[],
                length=0,
                steps=[],
                found=False,
                message=f"No relationship path exists between '{src}' and '{tgt}'."
            )

        # Build detailed step metadata
        steps = []
        for i in range(len(raw_path) - 1):
            u, v = raw_path[i], raw_path[i + 1]
            if self._graph.has_edge(u, v):
                edge_data = self._graph.edges[u, v]
                direction = "outgoing"
            else:
                edge_data = self._graph.edges.get((v, u), {})
                direction = "incoming"

            steps.append(PathStep(
                from_node=u,
                to_node=v,
                edge_type=edge_data.get("edge_type", "RELATED_TO"),
                direction=direction,
                attributes=edge_data
            ))

        return PathResult(
            source=src,
            target=tgt,
            path=raw_path,
            length=len(raw_path) - 1,
            steps=steps,
            found=True,
            message=f"Shortest path found: {len(raw_path) - 1} hops."
        )

    # -------------------------------------------------------------------------
    # Domain-Specific Graph Queries (Hackathon Dataset)
    # -------------------------------------------------------------------------

    def get_team_members(self, team_identifier: str) -> EngineResult:
        """
        Finds all participants belonging to a team via incoming MEMBER_OF edges.
        Demonstrates 1-hop reverse relationship traversal.
        """
        start_time = time.perf_counter()
        team_id = self.resolve_node_id(team_identifier)
        if not team_id:
            return self._empty_result("team_members", f"Team not found: '{team_identifier}'", start_time)

        team_node_data = self.get_node_data(team_id)
        members = []
        for src, _, edge_data in self._graph.in_edges(team_id, data=True):
            if edge_data.get("edge_type") == EdgeType.MEMBER_OF.value:
                p_data = self._graph.nodes[src]
                members.append({
                    "participant_id": p_data.get("participant_id"),
                    "node_id": src,
                    "full_name": p_data.get("full_name"),
                    "email": p_data.get("email"),
                    "role": edge_data.get("role", "Developer"),
                    "team_name": team_node_data.get("label", ""),
                    "team_id": team_node_data.get("team_id")
                })

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return EngineResult(
            engine=self.engine_type,
            success=True,
            data=members,
            metadata=EngineExecutionMetadata(
                engine=self.engine_type,
                execution_time_ms=round(duration_ms, 3),
                record_count=len(members),
                query_executed=f"get_team_members({team_identifier})",
                notes=[f"1-hop graph traversal (:Participant)-[:MEMBER_OF]->({team_id})"]
            )
        )

    def get_college_projects(self, college_identifier: str) -> EngineResult:
        """
        Traverses relationships from a College to all its submitted Projects:
        (:College)<-[:AFFILIATED_WITH]-(:Team)-[:SUBMITTED]->(:Project)
        Demonstrates 2-hop graph traversal.
        """
        start_time = time.perf_counter()
        college_id = self.resolve_node_id(college_identifier)
        if not college_id:
            return self._empty_result("college_projects", f"College not found: '{college_identifier}'", start_time)

        college_data = self.get_node_data(college_id)
        projects = []

        # Hop 1: Find teams affiliated with this college (incoming AFFILIATED_WITH)
        for team_node, _, edge_data in self._graph.in_edges(college_id, data=True):
            if edge_data.get("edge_type") == EdgeType.AFFILIATED_WITH.value:
                team_data = self._graph.nodes[team_node]

                # Hop 2: Find projects submitted by this team (outgoing SUBMITTED)
                for _, proj_node, proj_edge in self._graph.out_edges(team_node, data=True):
                    if proj_edge.get("edge_type") == EdgeType.SUBMITTED.value:
                        pr_data = self._graph.nodes[proj_node]

                        # Check if project won an award (Hop 3 optional)
                        award_info = "None"
                        for _, a_node, a_edge in self._graph.out_edges(proj_node, data=True):
                            if a_edge.get("edge_type") == EdgeType.WON_AWARD.value:
                                award_info = self._graph.nodes[a_node].get("label", "")

                        projects.append({
                            "project_id": pr_data.get("project_id"),
                            "project_node": proj_node,
                            "title": pr_data.get("title"),
                            "track": pr_data.get("track"),
                            "team_name": team_data.get("team_name"),
                            "college_name": college_data.get("name"),
                            "award": award_info,
                            "tech_stack": pr_data.get("tech_stack", "")
                        })

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return EngineResult(
            engine=self.engine_type,
            success=True,
            data=projects,
            metadata=EngineExecutionMetadata(
                engine=self.engine_type,
                execution_time_ms=round(duration_ms, 3),
                record_count=len(projects),
                query_executed=f"get_college_projects({college_identifier})",
                notes=[f"2-hop traversal ({college_id})<-[:AFFILIATED_WITH]-(:Team)-[:SUBMITTED]->(:Project)"]
            )
        )

    def get_shortest_path_result(
        self,
        source_identifier: str,
        target_identifier: str,
        directed: bool = False
    ) -> EngineResult:
        """Wraps find_shortest_path in a standardized EngineResult."""
        start_time = time.perf_counter()
        path_res = self.find_shortest_path(source_identifier, target_identifier, directed=directed)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        data = [path_res.model_dump()] if path_res.found else []

        return EngineResult(
            engine=self.engine_type,
            success=path_res.found,
            data=data,
            metadata=EngineExecutionMetadata(
                engine=self.engine_type,
                execution_time_ms=round(duration_ms, 3),
                record_count=1 if path_res.found else 0,
                query_executed=f"shortest_path({source_identifier} -> {target_identifier}, directed={directed})",
                notes=[path_res.message]
            ),
            error=None if path_res.found else path_res.message
        )

    # -------------------------------------------------------------------------
    # BaseEngine Implementation
    # -------------------------------------------------------------------------

    def execute(self, query: Any, **kwargs) -> EngineResult:
        """
        Executes a graph query specification.
        Supported query types:
            - 'team_members': kwargs={'team': str}
            - 'college_projects': kwargs={'college': str}
            - 'shortest_path': kwargs={'source': str, 'target': str, 'directed': bool}
            - 'bfs': kwargs={'start': str, 'max_depth': int}
            - 'dfs': kwargs={'start': str, 'max_depth': int}
            - 'neighbors': kwargs={'node': str, 'direction': str}
        """
        start_time = time.perf_counter()
        op = str(query).lower()

        if op in ("team_members", "team"):
            team = kwargs.get("team") or kwargs.get("identifier")
            return self.get_team_members(team)
        elif op in ("college_projects", "college"):
            college = kwargs.get("college") or kwargs.get("identifier")
            return self.get_college_projects(college)
        elif op in ("shortest_path", "path"):
            src = kwargs.get("source")
            tgt = kwargs.get("target")
            directed = kwargs.get("directed", False)
            return self.get_shortest_path_result(src, tgt, directed)
        elif op == "bfs":
            start = kwargs.get("start")
            max_depth = kwargs.get("max_depth")
            directed = kwargs.get("directed", False)
            nodes = self.bfs_traversal(start, max_depth, directed)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return EngineResult(
                engine=self.engine_type,
                success=True,
                data=nodes,
                metadata=EngineExecutionMetadata(
                    engine=self.engine_type,
                    execution_time_ms=round(duration_ms, 3),
                    record_count=len(nodes),
                    query_executed=f"BFS(start={start}, max_depth={max_depth})",
                    notes=[f"Visited {len(nodes)} nodes level-by-level"]
                )
            )
        elif op == "dfs":
            start = kwargs.get("start")
            max_depth = kwargs.get("max_depth")
            directed = kwargs.get("directed", False)
            nodes = self.dfs_traversal(start, max_depth, directed)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return EngineResult(
                engine=self.engine_type,
                success=True,
                data=nodes,
                metadata=EngineExecutionMetadata(
                    engine=self.engine_type,
                    execution_time_ms=round(duration_ms, 3),
                    record_count=len(nodes),
                    query_executed=f"DFS(start={start}, max_depth={max_depth})",
                    notes=[f"Visited {len(nodes)} nodes depth-first"]
                )
            )
        elif op == "neighbors":
            node = kwargs.get("node") or kwargs.get("identifier")
            direction = kwargs.get("direction", "both")
            neighbors = self.get_neighbors(node, direction)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return EngineResult(
                engine=self.engine_type,
                success=True,
                data=neighbors,
                metadata=EngineExecutionMetadata(
                    engine=self.engine_type,
                    execution_time_ms=round(duration_ms, 3),
                    record_count=len(neighbors),
                    query_executed=f"neighbors({node}, direction={direction})",
                    notes=[f"Found {len(neighbors)} adjacent nodes"]
                )
            )

        return self._empty_result(op, f"Unknown graph operation: '{op}'", start_time)

    def explain(self, query: Any, **kwargs) -> Dict[str, Any]:
        """
        Explains the computational complexity of the requested graph operation.
        Vital for DBMS viva defense comparing Graph Traversals vs. Recursive SQL CTEs.
        """
        op = str(query).lower()
        v = self.node_count
        e = self.edge_count

        explanations = {
            "bfs": {
                "algorithm": "Breadth-First Search (Level-Order Queue)",
                "time_complexity": f"O(|V| + |E|) = O({v} + {e}) = {v + e} operations worst-case",
                "space_complexity": f"O(|V|) = O({v}) queue and visited set",
                "comparison_with_sql": (
                    "In SQL, variable-depth exploration requires recursive CTEs (WITH RECURSIVE) "
                    "which repeatedly join intermediate tables and materialize duplicate tuples. "
                    "In the graph engine, adjacency pointers are traversed in O(degree(u)) without repeated table scans."
                )
            },
            "dfs": {
                "algorithm": "Depth-First Search (Recursive Branch Exploration)",
                "time_complexity": f"O(|V| + |E|) = O({v} + {e}) = {v + e} operations worst-case",
                "space_complexity": f"O(|V|) call stack depth",
                "comparison_with_sql": (
                    "SQL has no native concept of backtracking or branch pruning. "
                    "DFS in graph engines allows depth-bounded exploration and cycle detection."
                )
            },
            "shortest_path": {
                "algorithm": "Unweighted Shortest Path (BFS Single-Source)",
                "time_complexity": f"O(|V| + |E|) = O({v} + {e})",
                "space_complexity": f"O(|V|)",
                "comparison_with_sql": (
                    "Finding the shortest path between two arbitrary entities in SQL requires "
                    "iterative recursive joins with cycle checking or N-way self-joins where N is unknown in advance. "
                    "NetworkX solves this in a single BFS pass over node adjacency lists."
                )
            }
        }

        return explanations.get(op, {
            "algorithm": f"Graph operation: {op}",
            "time_complexity": "O(|V| + |E|)",
            "space_complexity": "O(|V|)",
            "node_count": v,
            "edge_count": e
        })

    def _empty_result(self, op: str, message: str, start_time: float) -> EngineResult:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return EngineResult(
            engine=self.engine_type,
            success=False,
            data=[],
            metadata=EngineExecutionMetadata(
                engine=self.engine_type,
                execution_time_ms=round(duration_ms, 3),
                record_count=0,
                query_executed=op,
                notes=[message]
            ),
            error=message
        )
