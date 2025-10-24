"""Init command for Taboot CLI.

Implements the initialization workflow that:
1. Checks system health (all services must be healthy)
2. Creates Neo4j constraints and indexes
3. Creates Qdrant collections
4. Creates PostgreSQL schema

This command must be run after starting Docker services for the first time.
"""

import asyncio

import typer
from rich.console import Console

from packages.common.config import get_config
from packages.common.db_schema import create_schema as create_postgres_schema
from packages.common.health import check_system_health
from packages.common.logging import get_logger
from packages.graph.client import Neo4jClient
from packages.graph.constraints import create_constraints
from packages.vector.qdrant_client import QdrantVectorClient

console = Console()
logger = get_logger(__name__)


def create_neo4j_constraints() -> None:
    """Create Neo4j constraints and indexes.

    Implements the schema from packages/graph/docs/GRAPH_SCHEMA.md:
    - Unique constraints on Host.hostname, Endpoint, Network.cidr, Document.doc_id, IP.addr
    - Indexes on Host.ip, Container, Service, User, Document.url

    Raises:
        Exception: If constraint creation fails.
    """
    with Neo4jClient() as client:
        create_constraints(client.get_driver())


def create_qdrant_collections() -> None:
    """Create Qdrant collections with proper vector configuration.

    Creates collection with:
    - 1024-dimensional vectors (Qwen3-Embedding-0.6B)
    - Cosine distance metric
    - HNSW indexing (M=16, ef_construct=200)

    Raises:
        Exception: If collection creation fails.
    """
    config = get_config()
    with QdrantVectorClient(
        url=config.qdrant_url,
        collection_name=config.collection_name,
        embedding_dim=1024,
    ) as qdrant_client:
        qdrant_client.create_collection()


def create_postgresql_schema() -> None:
    """Create PostgreSQL schema for Firecrawl metadata.

    Creates tables for:
    - Crawl jobs metadata
    - Document metadata
    - Source tracking

    Raises:
        Exception: If schema creation fails.
    """
    config = get_config()
    logger.info("Creating PostgreSQL schema", extra={"database": config.postgres_db})
    create_postgres_schema(config)


def init_command() -> None:
    """Initialize Taboot system schemas and collections.

    Orchestrates the initialization workflow:
    1. Check system health (Neo4j, Qdrant, Redis, TEI, Ollama, Firecrawl, Playwright)
    2. Create Neo4j constraints and indexes
    3. Create Qdrant collections
    4. Create PostgreSQL schema

    Exits with code 1 if any step fails.

    Example:
        $ taboot init
    """
    try:
        # 1. Check system health first
        console.print("[yellow]Checking system health...[/yellow]")
        health = asyncio.run(check_system_health())

        if not health["healthy"]:
            # Report which services failed
            console.print("[red]❌ System health check failed:[/red]")
            for service, status in health["services"].items():
                if not status:
                    console.print(f"  - {service}: unhealthy")
            raise typer.Exit(1) from None

        console.print("[green]✓ All services healthy[/green]")

        # 2. Create Neo4j constraints
        console.print("[yellow]Creating Neo4j constraints...[/yellow]")
        create_neo4j_constraints()
        console.print("[green]✓ Neo4j constraints created[/green]")

        # 3. Create Qdrant collections
        console.print("[yellow]Creating Qdrant collections...[/yellow]")
        create_qdrant_collections()
        console.print("[green]✓ Qdrant collection created[/green]")

        # 4. Create PostgreSQL schema
        console.print("[yellow]Creating PostgreSQL schema...[/yellow]")
        create_postgresql_schema()
        console.print("[green]✓ PostgreSQL schema created[/green]")

        console.print("[bold green]✅ System initialized successfully![/bold green]")

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit code
        raise
    except Exception as e:
        # Catch any other errors and report them
        console.print(f"[red]❌ Initialization failed: {e}[/red]")
        logger.exception("Initialization failed")
        raise typer.Exit(1) from e


# Export public API
__all__ = [
    "create_neo4j_constraints",
    "create_postgresql_schema",
    "create_qdrant_collections",
    "init_command",
]
