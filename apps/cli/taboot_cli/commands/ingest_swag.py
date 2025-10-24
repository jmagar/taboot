"""Ingest SWAG config command for Taboot CLI.

Implements the SWAG reverse proxy config ingestion workflow:
1. Accept config file/directory path
2. Create SwagReader and GraphWriter adapters
3. Call IngestSwagUseCase.execute() orchestration
4. Display progress and results

This command is thin - parsing logic is in packages/ingest/readers/swag.py,
graph operations use packages/graph/writers/swag_writer.py,
and orchestration is in packages/core/use_cases/ingest_swag.py.

Per CLAUDE.md architecture: Apps are thin I/O layers calling core use-cases.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from apps.cli.taboot_cli.commands import ingest_app as app
from packages.core.use_cases.ingest_swag import IngestSwagError, IngestSwagUseCase
from packages.graph.client import Neo4jClient, Neo4jConnectionError
from packages.graph.writers.swag_writer import SwagGraphWriter
from packages.ingest.readers.swag import SwagReader, SwagReaderError

console = Console()
logger = logging.getLogger(__name__)


@app.command(name="swag")
def ingest_swag_command(
    config_path: Annotated[str, typer.Argument(..., help="Path to SWAG nginx config file")],
    proxy_name: Annotated[
        str, typer.Option("--proxy-name", "-n", help="Name for the Proxy node")
    ] = "swag",
) -> None:
    """Ingest SWAG reverse proxy config into the knowledge graph.

    Parses nginx configuration files to extract:
    - Proxy nodes (reverse proxy information)
    - ROUTES_TO relationships (host, path, target service, TLS)

    Args:
        config_path: Path to nginx config file or directory.
        proxy_name: Name for the Proxy node (default: "swag").

    Example:
        uv run apps/cli ingest swag /path/to/swag/config.conf
        uv run apps/cli ingest swag /path/to/swag/config.conf --proxy-name custom-proxy

    Expected output:
        ✓ Starting SWAG config ingestion: /path/to/config.conf
        ✓ Parsed: 1 proxy, 5 routes
        ✓ Wrote 1 Proxy node to Neo4j
        ✓ Wrote 5 ROUTES_TO relationships to Neo4j
        ✓ SWAG config ingestion completed successfully

    Raises:
        typer.Exit: Exit with code 1 if ingestion fails.
    """
    try:
        # Validate config path exists
        path = Path(config_path)
        if not path.exists():
            console.print(f"[red]✗ Config file not found: {config_path}[/red]")
            raise typer.Exit(1)

        # Display starting message
        console.print(f"[yellow]Starting SWAG config ingestion: {config_path}[/yellow]")
        logger.info("Starting SWAG config ingestion: %s", config_path)

        # Create adapters
        swag_reader = SwagReader(proxy_name=proxy_name)

        neo4j_client = Neo4jClient()
        neo4j_client.connect()

        try:
            graph_writer = SwagGraphWriter(neo4j_client, batch_size=2000)

            # Create use-case and execute
            use_case = IngestSwagUseCase(
                swag_reader=swag_reader,
                graph_writer=graph_writer,
            )

            # Execute ingestion pipeline
            logger.info("Executing SWAG ingestion use-case")
            summary = use_case.execute(config_path)

            # Display results
            parse_stats = summary["parse_stats"]
            console.print(
                f"[green]✓ Parsed: {parse_stats['proxy_count']} proxy, "
                f"{parse_stats['route_count']} routes[/green]"
            )

            console.print(
                f"[green]✓ Wrote {summary['proxies_written']} Proxy node(s) to Neo4j[/green]"
            )

            console.print(
                f"[green]✓ Wrote {summary['routes_written']} ROUTES_TO "
                f"relationship(s) to Neo4j[/green]"
            )

            # Display batch statistics
            write_stats = summary["write_stats"]
            if write_stats:
                console.print(
                    f"[dim]  (Batches: {write_stats.get('proxy_batches', 0)} proxies, "
                    f"{write_stats.get('route_batches', 0)} routes)[/dim]"
                )

            console.print("[green]✓ SWAG config ingestion completed successfully[/green]")
            logger.info("SWAG config ingestion completed successfully")

        finally:
            # Always close Neo4j connection
            neo4j_client.close()
            logger.info("Closed Neo4j connection")

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit code
        raise
    except SwagReaderError as e:
        # Handle SwagReader-specific errors
        console.print(f"[red]✗ SWAG config parsing failed: {e}[/red]")
        logger.exception("SWAG config parsing failed")
        raise typer.Exit(1) from None
    except Neo4jConnectionError as e:
        # Handle Neo4j connection errors
        console.print(f"[red]✗ Neo4j connection failed: {e}[/red]")
        logger.exception("Neo4j connection failed")
        raise typer.Exit(1) from None
    except IngestSwagError as e:
        # Handle use-case errors
        console.print(f"[red]✗ Ingestion failed: {e}[/red]")
        logger.exception("Ingestion failed")
        raise typer.Exit(1) from None
    except ValueError as e:
        # Handle validation errors
        console.print(f"[red]✗ Invalid input: {e}[/red]")
        logger.exception("Invalid input")
        raise typer.Exit(1) from None
    except Exception as e:
        # Catch any other errors and report them
        console.print(f"[red]✗ Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during SWAG ingestion")
        raise typer.Exit(1) from None


# Export public API
__all__ = ["app", "ingest_swag_command"]
