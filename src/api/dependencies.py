"""
Engine Lifecycle & Dependency Injection for TriQuery API.
Initializes singleton engine instances once during application startup,
preventing redundant index construction or graph rebuilding on each request.
"""

import logging
from typing import Optional
from fastapi import Depends, Request

from src.config import DatabaseConfig, config
from src.engines.graph.engine import GraphEngine
from src.engines.relational.connection import DatabaseConnectionManager
from src.engines.relational.engine import RelationalEngine
from src.engines.vector.engine import VectorEngine
from src.planner.planner import UnifiedQueryPlanner

logger = logging.getLogger("triquery.api")


class EngineContainer:
    """
    Holds persistent, shared engine instances for the lifespan of the API server.
    """

    def __init__(self, db_config: Optional[DatabaseConfig] = None, auto_build: bool = True):
        self.cfg = db_config or config.db
        logger.info(f"Initializing EngineContainer with backend: {self.cfg.driver}")

        self.conn_mgr = DatabaseConnectionManager(self.cfg)
        self.relational_engine = RelationalEngine(self.conn_mgr)

        # Graph engine builds from the relational store
        self.graph_engine = GraphEngine(relational_engine=self.relational_engine, auto_build=auto_build)

        # Vector engine uses TF-IDF provider by default
        self.vector_engine = VectorEngine(relational_engine=self.relational_engine, auto_build=auto_build)

        # Unified Query Planner wraps all 3 engines
        self.planner = UnifiedQueryPlanner(
            relational_engine=self.relational_engine,
            graph_engine=self.graph_engine,
            vector_engine=self.vector_engine,
        )

    def close(self):
        """Releases underlying database connections."""
        if hasattr(self.conn_mgr, "close"):
            self.conn_mgr.close()


def get_container(request: Request) -> EngineContainer:
    """Retrieves the singleton engine container from FastAPI app state."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        # Fallback for isolated test runs without full lifespan trigger
        container = EngineContainer()
        request.app.state.container = container
    return container


def get_relational_engine(container: EngineContainer = Depends(get_container)) -> RelationalEngine:
    return container.relational_engine


def get_graph_engine(container: EngineContainer = Depends(get_container)) -> GraphEngine:
    return container.graph_engine


def get_vector_engine(container: EngineContainer = Depends(get_container)) -> VectorEngine:
    return container.vector_engine


def get_planner(container: EngineContainer = Depends(get_container)) -> UnifiedQueryPlanner:
    return container.planner
