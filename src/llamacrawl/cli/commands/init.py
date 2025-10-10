"""Infrastructure initialization command."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.storage.qdrant import QdrantClient
from llamacrawl.utils.logging import get_logger

from ..context import CLIState
from ..dependencies import build_neo4j, build_qdrant, build_redis

logger = get_logger(__name__)


def init(
    ctx: typer.Context,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force recreate collections/indexes even if they exist",
        ),
    ] = False,
) -> None:
    """Initialize backing services and indexes."""
    state = ctx.ensure_object(CLIState)
    console = state.console
    config = state.config

    logger.info("Init command called", extra={"force": force})

    if force and not _confirm_force(console):
        logger.info("Init --force cancelled by user")
        raise typer.Exit(code=0)

    console.print("\n[bold cyan]Initializing LlamaCrawl Infrastructure[/bold cyan]")
    console.print("=" * 50)

    steps_completed = 0
    total_steps = 3
    all_success = True

    console.print("\n[bold]1/3 Redis[/bold]")
    logger.info("Checking Redis connection")
    try:
        redis_client = build_redis(config)
        if redis_client.health_check():
            console.print("  [green]✓[/green] Redis connection successful")
            logger.info("Redis health check passed")
            steps_completed += 1
        else:
            console.print("  [red]✗[/red] Redis connection failed")
            logger.error("Redis health check failed")
            all_success = False
    except Exception as error:
        console.print(f"  [red]✗[/red] Redis connection error: {error}")
        logger.error("Redis connection error: %s", error)
        all_success = False

    console.print("\n[bold]2/3 Qdrant[/bold]")
    logger.info("Initializing Qdrant collection")
    qdrant_client: QdrantClient | None = None
    try:
        qdrant_client = build_qdrant(config)
        if not qdrant_client.health_check():
            console.print(f"  [red]✗[/red] Qdrant server is not accessible at {config.qdrant_url}")
            logger.error("Qdrant health check failed")
            all_success = False
        else:
            console.print("  [green]✓[/green] Qdrant server accessible")
            collection_exists = qdrant_client.collection_exists()

            if force and collection_exists:
                console.print(
                    f"  [yellow]![/yellow] Deleting existing collection "
                    f"'{config.vector_store.collection_name}'..."
                )
                logger.warning(
                    "Deleting existing Qdrant collection: %s",
                    config.vector_store.collection_name,
                )
                try:
                    qdrant_client.client.delete_collection(config.vector_store.collection_name)
                    console.print("  [green]✓[/green] Existing collection deleted")
                    collection_exists = False
                except Exception as error:
                    console.print(f"  [red]✗[/red] Failed to delete collection: {error}")
                    logger.error("Failed to delete Qdrant collection: %s", error)
                    all_success = False

            if not collection_exists:
                console.print(
                    f"  [yellow]![/yellow] Creating collection "
                    f"'{config.vector_store.collection_name}'..."
                )
                logger.info(
                    "Creating Qdrant collection: %s",
                    config.vector_store.collection_name,
                )
                try:
                    qdrant_client.create_collection(
                        hnsw_m=config.vector_store.hnsw.m,
                        hnsw_ef_construct=config.vector_store.hnsw.ef_construct,
                        enable_quantization=config.vector_store.enable_quantization,
                    )
                    console.print("  [green]✓[/green] Collection created successfully")
                    console.print(
                        f"    - Vector dimension: {config.vector_store.vector_dimension}"
                    )
                    console.print(
                        f"    - Distance metric: {config.vector_store.distance_metric}"
                    )
                    quant_status = (
                        "enabled" if config.vector_store.enable_quantization else "disabled"
                    )
                    console.print(f"    - Quantization: {quant_status}")
                    logger.info("Qdrant collection created successfully")
                    steps_completed += 1
                except Exception as error:
                    console.print(f"  [red]✗[/red] Failed to create collection: {error}")
                    logger.error("Failed to create Qdrant collection: %s", error)
                    all_success = False
            else:
                console.print(
                    f"  [green]✓[/green] Collection "
                    f"'{config.vector_store.collection_name}' already exists"
                )
                logger.info("Qdrant collection already exists")
                steps_completed += 1
    except Exception as error:
        console.print(f"  [red]✗[/red] Qdrant initialization error: {error}")
        logger.error("Qdrant initialization error: %s", error)
        all_success = False

    console.print("\n[bold]3/3 Neo4j[/bold]")
    logger.info("Initializing Neo4j schema")
    neo4j_client: Neo4jClient | None = None
    try:
        neo4j_client = build_neo4j(config)
        if not neo4j_client.health_check():
            console.print(f"  [red]✗[/red] Neo4j server is not accessible at {config.neo4j_uri}")
            logger.error("Neo4j health check failed")
            all_success = False
        else:
            console.print("  [green]✓[/green] Neo4j server accessible")
            console.print("  [yellow]![/yellow] Initializing schema (constraints and indexes)...")
            logger.info("Initializing Neo4j schema")
            try:
                neo4j_client.initialize_schema()
                console.print("  [green]✓[/green] Schema initialized successfully")
                console.print("    - Constraints created for unique identifiers")
                console.print("    - Indexes created for query optimization")
                logger.info("Neo4j schema initialized successfully")
                steps_completed += 1
            except Exception as error:
                console.print(f"  [red]✗[/red] Failed to initialize schema: {error}")
                logger.error("Failed to initialize Neo4j schema: %s", error)
                all_success = False
    except Exception as error:
        console.print(f"  [red]✗[/red] Neo4j initialization error: {error}")
        logger.error("Neo4j initialization error: %s", error)
        all_success = False
    finally:
        if neo4j_client is not None:
            try:
                neo4j_client.close()
            except Exception:  # pragma: no cover - defensive
                logger.debug("Failed to close Neo4j client after initialization")

    console.print("\n" + "=" * 50)

    if all_success:
        console.print("[bold green]✓ Infrastructure initialization complete![/bold green]")
        console.print(f"Successfully completed {steps_completed}/{total_steps} steps.")
        console.print()
        console.print("[dim]You can now run:[/dim]")
        console.print("  llamacrawl ingest <source> - to ingest data")
        console.print("  llamacrawl query '<text>' - to query the system")
        console.print("  llamacrawl status - to check system status")
        logger.info("Infrastructure initialization completed successfully")
        raise typer.Exit(code=0)

    console.print("[bold red]✗ Infrastructure initialization failed[/bold red]")
    console.print(f"Completed {steps_completed}/{total_steps} steps.")
    console.print()
    console.print("[dim]Please check the errors above and ensure all services are running:[/dim]")
    console.print(f"  - Qdrant: {config.qdrant_url}")
    console.print(f"  - Neo4j: {config.neo4j_uri}")
    console.print(f"  - Redis: {config.redis_url}")
    logger.error("Infrastructure initialization failed")
    raise typer.Exit(code=1)


def _confirm_force(console: Any) -> bool:
    console.print(
        "[bold red]WARNING:[/bold red] --force will delete existing collections and data!"
    )
    console.print("This operation is [bold red]destructive[/bold red] and cannot be undone.")
    console.print()
    return typer.confirm("Are you sure you want to proceed?", default=False)
