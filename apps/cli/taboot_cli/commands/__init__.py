"""Taboot CLI commands package.

This package contains all CLI command implementations organized by functionality:
- ingest_* modules: Data ingestion from various sources (web, GitHub, Reddit, etc.)
- extract_* modules: Extraction pipeline commands
- query: Query the knowledge graph
- status: System status and health checks
- graph: Direct Neo4j graph operations
- init: System initialization
- list_documents: List ingested documents
"""

__all__ = [
    "extract_pending",
    "extract_reprocess",
    "extract_status",
    "graph",
    "ingest_docker_compose",
    "ingest_elasticsearch",
    "ingest_github",
    "ingest_gmail",
    "ingest_reddit",
    "ingest_swag",
    "ingest_web",
    "ingest_youtube",
    "init",
    "list_documents",
    "query",
    "status",
]
