"""
FastAPI Application Entry Point for TriQuery.
Coordinates lifespan engine lifecycle, CORS middleware, sanitized error handling,
and REST routing for Relational, Graph, Vector, and Unified Query paradigms.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.dependencies import EngineContainer
from src.api.routes import graph, health, presets, query, relational, vector
from src.config import DatabaseConfig, config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("triquery.api")


def create_app(db_config: Optional[DatabaseConfig] = None) -> FastAPI:
    """
    Factory creating the configured FastAPI application.
    Supports injecting custom DatabaseConfig for test isolation.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initializes engines once during startup and closes resources on shutdown."""
        logger.info("Initializing TriQuery API Engine Container...")
        app.state.container = EngineContainer(db_config=db_config or config.db)
        logger.info(
            f"TriQuery Engine Container ready. Relational backend: {app.state.container.cfg.driver}, "
            f"Graph nodes: {app.state.container.graph_engine.node_count}, "
            f"Vector index: {app.state.container.vector_engine.document_count} docs."
        )
        yield
        logger.info("Shutting down TriQuery API Engine Container...")
        if hasattr(app.state, "container") and app.state.container:
            app.state.container.close()

    app = FastAPI(
        title="TriQuery Multi-Paradigm Query API",
        description=(
            "Explainable Multi-Paradigm Query Engine unifying Relational SQL, "
            "NetworkX Graph Traversal, and TF-IDF Vector Similarity Search with Reciprocal Rank Fusion (RRF)."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS narrowly for local Vite dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register API Routers
    app.include_router(health.router)
    app.include_router(presets.router)
    app.include_router(query.router)
    app.include_router(relational.router)
    app.include_router(graph.router)
    app.include_router(vector.router)

    # Root service descriptor
    @app.get("/", tags=["Root"])
    def root():
        return {
            "name": "TriQuery Multi-Paradigm Query API",
            "version": "1.0.0",
            "status": "online",
            "docs_url": "/docs",
            "openapi_url": "/openapi.json",
            "backend": "MySQL 8.x" if not config.db.sqlite_fallback and config.db.driver == "mysql" else "SQLite (isolated)",
        }

    # Global Sanitized Exception Handler
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled API error on {request.method} {request.url.path}: {exc}", exc_info=True)
        # Never leak passwords, tracebacks, or system paths to client
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": "An internal error occurred during query processing. Please consult server logs."
            }
        )

    return app


# Default singleton instance for uvicorn run: uvicorn src.api.app:app
app = create_app()
