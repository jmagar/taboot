"""Taboot CLI commands package.

This package contains all CLI command implementations organized by functionality:
- ingest_* modules: Data ingestion from various sources (web, GitHub, Reddit, etc.)
- extract_* modules: Extraction pipeline commands
- query: Query the knowledge graph
- status: System status and health checks
- graph: Direct Neo4j graph operations
- init: System initialization
- list_documents: List ingested documents

Shared sub-apps are created here to avoid duplication across command modules.
"""

from __future__ import annotations

import typer

# Shared sub-apps for command grouping
# These are created once and imported by command modules to avoid duplicate app creation
ingest_app = typer.Typer(name="ingest", help="Ingest documents from various sources")
extract_app = typer.Typer(name="extract", help="Run extraction pipeline")
list_app = typer.Typer(name="list", help="List resources")
graph_app = typer.Typer(name="graph", help="Execute Cypher queries")
schema_app = typer.Typer(name="schema", help="Manage database schema versions")

__all__ = [
    "extract_app",
    "extract_pending",
    "extract_reprocess",
    "extract_status",
    "graph",
    "graph_app",
    "ingest_app",
    "ingest_docker_compose",
    "ingest_elasticsearch",
    "ingest_github",
    "ingest_gmail",
    "ingest_reddit",
    "ingest_swag",
    "ingest_web",
    "ingest_youtube",
    "init",
    "list_app",
    "list_documents",
    "query",
    "schema_app",
    "status",
]
