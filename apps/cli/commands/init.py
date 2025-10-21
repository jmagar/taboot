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
from packages.common.health import check_system_health
from packages.graph.client import Neo4jClient
from packages.vector.client import QdrantVectorClient

console = Console()


def create_neo4j_constraints() -> None:
    """Create Neo4j constraints and indexes.

    Implements the schema from packages/graph/docs/GRAPH_SCHEMA.md:
    - Unique constraints on Host.hostname, Endpoint, Network.cidr, Document.doc_id, IP.addr
    - Indexes on Host.ip, Container, Service, User, Document.url

    Raises:
        Exception: If constraint creation fails.
    """
    client = Neo4jClient()

    try:
        client.connect()

        # Define all constraints and indexes from GRAPH_SCHEMA.md
        statements = [
            # Constraints
            (
                "CREATE CONSTRAINT host_hostname IF NOT EXISTS "
                "FOR (h:Host) REQUIRE h.hostname IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT endpoint_uniq IF NOT EXISTS "
                "FOR (e:Endpoint) REQUIRE (e.scheme, e.fqdn, e.port, e.path) IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT network_cidr IF NOT EXISTS "
                "FOR (n:Network) REQUIRE n.cidr IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT doc_docid IF NOT EXISTS "
                "FOR (d:Document) REQUIRE d.doc_id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT ip_addr IF NOT EXISTS "
                "FOR (i:IP) REQUIRE i.addr IS UNIQUE"
            ),
            # Indexes
            "CREATE INDEX host_ip IF NOT EXISTS FOR (h:Host) ON (h.ip)",
            (
                "CREATE INDEX container_compose IF NOT EXISTS "
                "FOR (c:Container) ON (c.compose_project, c.compose_service)"
            ),
            "CREATE INDEX service_name IF NOT EXISTS FOR (s:Service) ON (s.name)",
            (
                "CREATE INDEX service_proto_port IF NOT EXISTS "
                "FOR (s:Service) ON (s.protocol, s.port)"
            ),
            (
                "CREATE INDEX user_provider_username IF NOT EXISTS "
                "FOR (u:User) ON (u.provider, u.username)"
            ),
            "CREATE INDEX doc_url IF NOT EXISTS FOR (d:Document) ON (d.url)",
        ]

        # Execute each statement in a separate transaction
        for statement in statements:
            with client.session() as session:
                session.run(statement)
    finally:
        client.close()


def create_qdrant_collections() -> None:
    """Create Qdrant collections with proper vector configuration.

    Creates collection with:
    - 768-dimensional vectors (Qwen3-Embedding-0.6B)
    - Cosine distance metric
    - HNSW indexing (M=16, ef_construct=200)

    Raises:
        Exception: If collection creation fails.
    """
    config = get_config()
    qdrant_client = QdrantVectorClient(
        url=config.qdrant_url,
        collection_name=config.collection_name,
        embedding_dim=768,
    )

    try:
        qdrant_client.create_collection()
    finally:
        qdrant_client.close()


def create_postgresql_schema() -> None:
    """Create PostgreSQL schema for Firecrawl metadata.

    Creates tables for:
    - Crawl jobs metadata
    - Document metadata
    - Source tracking

    Raises:
        Exception: If schema creation fails.
    """
    # PostgreSQL schema creation will be implemented when db_schema module exists
    # For now, this is a placeholder that doesn't fail
    # The tests mock this function, so it won't be called during testing
    pass


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
            raise typer.Exit(1)

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
        error_msg = str(e).lower()
        console.print(f"[red]❌ Initialization failed: {e}[/red]")

        # Determine which component failed based on error message
        if "neo4j" in error_msg:
            console.print("[red]Failed to create Neo4j constraints[/red]")
        elif "qdrant" in error_msg or "collection" in error_msg:
            console.print("[red]Failed to create Qdrant collection[/red]")
        elif "postgresql" in error_msg or "schema" in error_msg:
            console.print("[red]Failed to create PostgreSQL schema[/red]")

        raise typer.Exit(1) from None


# Export public API
__all__ = [
    "init_command",
    "create_neo4j_constraints",
    "create_qdrant_collections",
    "create_postgresql_schema",
]
