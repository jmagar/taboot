"""Taboot CLI - Typer command-line interface for orchestrating RAG workflows."""

from __future__ import annotations

import logging
from typing import Literal

import typer
from rich.console import Console

from apps.cli.taboot_cli.commands import (
    extract_app,
    graph_app,
    ingest_app,
    list_app,
    migrate_app,
)
from apps.cli.taboot_cli.utils import async_command
from packages.schemas.models import ExtractionState, SourceType

app = typer.Typer(
    name="taboot",
    help="Taboot CLI - Doc-to-Graph RAG Platform",
    add_completion=False,
)
console = Console()
logger = logging.getLogger(__name__)


# Register ingest subcommand
app.add_typer(ingest_app, name="ingest")


# Register extract subcommand group with commands
@extract_app.command(name="pending")
@async_command
async def extract_pending(
    limit: int | None = typer.Option(
        None, "--limit", "-l", help="Maximum number of documents to process"
    ),
) -> None:
    """
    Process all documents awaiting extraction.

    The extraction pipeline runs three tiers:
        Tier A: Deterministic regex/JSON parsing (≥50 pages/sec)
        Tier B: spaCy NLP entity extraction (≥200 sentences/sec)
        Tier C: LLM-based structured extraction (≤250ms/window median)

    Examples:
        taboot extract pending
        taboot extract pending --limit 10
    """
    from apps.cli.taboot_cli.commands.extract_pending import extract_pending_command

    await extract_pending_command(limit=limit)


@extract_app.command(name="status")
@async_command
async def extract_status() -> None:
    """
    Display system status including service health, queue depths, and metrics.

    Shows:
        - Service health (Neo4j, Qdrant, Redis, TEI, Ollama, Firecrawl, Playwright)
        - Queue depths (ingestion, extraction)
        - System metrics (documents, chunks, jobs, nodes)

    Examples:
        taboot extract status
    """
    from apps.cli.taboot_cli.commands.extract_status import extract_status_command

    await extract_status_command()


@extract_app.command(name="reprocess")
def extract_reprocess(
    since: str = typer.Option(..., "--since", help="Reprocess documents from period (e.g., '7d')"),
) -> None:
    """
    Reprocess documents with updated extractors.

    Examples:
        taboot extract reprocess --since 7d
        taboot extract reprocess --since 30d
    """
    from apps.cli.taboot_cli.commands.extract_reprocess import extract_reprocess_command

    extract_reprocess_command(since=since)


app.add_typer(extract_app, name="extract")


@app.command()
def query(
    question: str = typer.Argument(..., help="Natural language question"),
    sources: str | None = typer.Option(None, help="Filter by source types (comma-separated)"),
    after: str | None = typer.Option(None, help="Filter by date (YYYY-MM-DD)"),
    top_k: int = typer.Option(10, help="Number of results to retrieve"),
) -> None:
    """
    Query the knowledge graph using hybrid retrieval (vector + graph traversal).

    The 6-stage retrieval pipeline:
        1. Query embedding (TEI)
        2. Metadata filtering (source, date)
        3. Vector search (Qdrant, top-k)
        4. Reranking (Qwen/Qwen3-Reranker-0.6B)
        5. Graph traversal (≤2 hops Neo4j)
        6. Synthesis (Qwen3-4B) with inline citations

    Examples:
        taboot query "what changed in auth?"
        taboot query "docker compose services" --sources docker-compose,swag
        taboot query "recent updates" --after 2025-01-01 --top-k 20
    """
    from apps.cli.taboot_cli.commands.query import query_command

    query_command(question=question, sources=sources, after=after, top_k=top_k)


@app.command()
@async_command
async def status(
    *,
    component: str | None = typer.Option(
        default=None,
        help="Component to check (neo4j, qdrant, redis, tei, ollama, firecrawl, playwright)",
    ),
    verbose: bool = typer.Option(default=False, help="Show detailed metrics"),
) -> None:
    """
    Display system status, health checks, and performance metrics.

    Components:
        neo4j      - Graph database connection and health
        qdrant     - Vector database collection stats
        redis      - Cache connection and memory usage
        tei        - Text embeddings inference service
        ollama     - LLM service status
        firecrawl  - Web crawling service status
        playwright - Browser automation service

    Examples:
        taboot status
        taboot status --component neo4j --verbose
        taboot status --component qdrant
    """
    from apps.cli.taboot_cli.commands.status import status_command

    await status_command(component=component, verbose=verbose)


# Register list subcommand group with commands
@list_app.command(name="documents")
def list_documents(
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum documents to show"),
    offset: int = typer.Option(0, "--offset", "-o", help="Pagination offset"),
    source_type: str | None = typer.Option(
        None, "--source-type", "-s", help="Filter by source type"
    ),
    extraction_state: str | None = typer.Option(
        None, "--extraction-state", "-e", help="Filter by extraction state"
    ),
) -> None:
    """
    List ingested documents with filters and pagination.

    Examples:
        taboot list documents
        taboot list documents --limit 20 --source-type web
        taboot list documents --extraction-state pending
    """
    from apps.cli.taboot_cli.commands.list_documents import list_documents_command

    source_type_enum = SourceType(source_type) if source_type is not None else None
    extraction_state_enum = (
        ExtractionState(extraction_state) if extraction_state is not None else None
    )

    list_documents_command(
        limit=limit,
        offset=offset,
        source_type=source_type_enum,
        extraction_state=extraction_state_enum,
    )


app.add_typer(list_app, name="list")


# Register graph subcommand group with commands
@graph_app.command(name="query")
def graph_query(
    cypher: str = typer.Argument(..., help="Cypher query to execute"),
    output_format: Literal["table", "json"] = typer.Option(
        "table", "--format", "-f", help="Output format (table or json)"
    ),
) -> None:
    """
    Execute a raw Cypher query against the Neo4j knowledge graph.

    Use this for debugging, exploration, and direct database queries.

    Examples:
        taboot graph query "MATCH (s:Service) RETURN s LIMIT 10"
        taboot graph query "MATCH (s:Service)-[r]->(h:Host) RETURN s.name, type(r), h.hostname"
        taboot graph query "MATCH (n) RETURN count(n) as total_nodes" --format json
    """
    from apps.cli.taboot_cli.commands.graph import query_command

    query_command(cypher=cypher, output_format=output_format)


app.add_typer(graph_app, name="graph")


# Register migrate subcommand group with commands
@migrate_app.command(name="postgres")
def migrate_postgres() -> None:
    """
    Apply PostgreSQL Alembic migrations.

    Runs alembic upgrade head to apply all pending migrations.

    Examples:
        taboot migrate postgres
    """
    from apps.cli.taboot_cli.commands.migrate import migrate_postgres as run_postgres

    run_postgres()


@migrate_app.command(name="neo4j")
def migrate_neo4j() -> None:
    """
    Apply Neo4j Cypher migrations.

    Applies versioned Cypher migrations from packages/graph/migrations.
    Tracks applied versions in PostgreSQL schema_versions table.

    Examples:
        taboot migrate neo4j
    """
    from apps.cli.taboot_cli.commands.migrate import migrate_neo4j as run_neo4j

    run_neo4j()


@migrate_app.command(name="all")
def migrate_all() -> None:
    """
    Apply all database migrations in dependency order.

    Applies:
        1. PostgreSQL migrations (creates schema_versions table)
        2. Neo4j migrations (uses schema_versions for tracking)

    Examples:
        taboot migrate all
    """
    from apps.cli.taboot_cli.commands.migrate import migrate_all as run_all

    run_all()


app.add_typer(migrate_app, name="migrate")


@app.command()
def init() -> None:
    """
    Initialize the Taboot system: create Neo4j schema, Qdrant collections, and indexes.

    This command performs:
        - Neo4j constraints and indexes (Service.name, Host.hostname, etc.)
        - Qdrant collection creation with proper vector dimensions
        - Redis keyspace initialization
        - spaCy model verification and download if needed

    Run this once after starting Docker services for the first time.

    Example:
        taboot init
    """
    from apps.cli.taboot_cli.commands.init import init_command

    init_command()


if __name__ == "__main__":
    app()
