"""Ingest SWAG config command for Taboot CLI.

Implements the SWAG reverse proxy config ingestion workflow:
1. Accept config file/directory path
2. Parse nginx config using SwagReader
3. Extract Proxy nodes and ROUTES_TO relationships
4. Write to Neo4j using batched graph writer
5. Display progress and results

This command is thin - parsing logic is in packages/ingest/readers/swag.py,
and graph operations use packages/graph/ adapters.
"""

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from packages.graph.client import Neo4jClient, Neo4jConnectionError
from packages.ingest.readers.swag import SwagReader, SwagReaderError

console = Console()
logger = logging.getLogger(__name__)

app = typer.Typer(name="ingest", help="Ingest documents from various sources")


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

    Raises:
        typer.Exit: Exit with code 1 if ingestion fails.
    """
    try:
        # Validate config path exists
        path = Path(config_path)
        if not path.exists():
            console.print(f"[red]✗ Config file not found: {config_path}[/red]")
            logger.error(f"Config file not found: {config_path}")
            raise typer.Exit(1)

        # Display starting message
        console.print(f"[yellow]Starting SWAG config ingestion: {config_path}[/yellow]")
        logger.info(f"Starting SWAG config ingestion: {config_path}")

        # Create SwagReader
        reader = SwagReader(proxy_name=proxy_name)

        # Parse config file
        logger.info(f"Parsing config file: {config_path}")
        parsed = reader.parse_file(str(config_path))

        proxies = parsed["proxies"]
        routes = parsed["routes"]

        console.print(f"[green]✓ Parsed: {len(proxies)} proxy, {len(routes)} routes[/green]")
        logger.info(f"Parsed {len(proxies)} proxies and {len(routes)} routes")

        # Connect to Neo4j
        logger.info("Connecting to Neo4j")
        neo4j_client = Neo4jClient()
        neo4j_client.connect()

        try:
            # Write Proxy nodes to Neo4j
            with neo4j_client.session() as session:
                # Write Proxy nodes
                for proxy in proxies:
                    query = """
                    MERGE (p:Proxy {name: $name})
                    SET p.proxy_type = $proxy_type,
                        p.created_at = $created_at,
                        p.updated_at = $updated_at,
                        p.metadata = $metadata
                    RETURN p
                    """
                    session.run(
                        query,
                        {
                            "name": proxy.name,
                            "proxy_type": proxy.proxy_type.value,
                            "created_at": proxy.created_at.isoformat(),
                            "updated_at": proxy.updated_at.isoformat(),
                            "metadata": proxy.metadata or {},
                        },
                    )

                console.print(f"[green]✓ Wrote {len(proxies)} Proxy node to Neo4j[/green]")
                logger.info(f"Wrote {len(proxies)} Proxy nodes to Neo4j")

                # Write ROUTES_TO relationships
                # First ensure Service nodes exist
                services = {route["target_service"] for route in routes}
                for service_name in services:
                    query = """
                    MERGE (s:Service {name: $name})
                    RETURN s
                    """
                    session.run(query, {"name": service_name})

                # Now create ROUTES_TO relationships
                for route in routes:
                    query = """
                    MATCH (p:Proxy {name: $proxy_name})
                    MATCH (s:Service {name: $service_name})
                    MERGE (p)-[r:ROUTES_TO]->(s)
                    SET r.host = $host,
                        r.path = $path,
                        r.tls = $tls
                    RETURN r
                    """
                    session.run(
                        query,
                        {
                            "proxy_name": proxy_name,
                            "service_name": route["target_service"],
                            "host": route["host"],
                            "path": route["path"],
                            "tls": route["tls"],
                        },
                    )

                console.print(
                    f"[green]✓ Wrote {len(routes)} ROUTES_TO relationships to Neo4j[/green]"
                )
                logger.info(f"Wrote {len(routes)} ROUTES_TO relationships to Neo4j")

        finally:
            # Always close Neo4j connection
            neo4j_client.close()
            logger.info("Closed Neo4j connection")

        # Success message
        console.print("[green]✓ SWAG config ingestion completed successfully[/green]")
        logger.info("SWAG config ingestion completed successfully")

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit code
        raise
    except SwagReaderError as e:
        # Handle SwagReader-specific errors
        console.print(f"[red]✗ SWAG config parsing failed: {e}[/red]")
        logger.error(f"SWAG config parsing failed: {e}", exc_info=True)
        raise typer.Exit(1) from None
    except Neo4jConnectionError as e:
        # Handle Neo4j connection errors
        console.print(f"[red]✗ Neo4j connection failed: {e}[/red]")
        logger.error(f"Neo4j connection failed: {e}", exc_info=True)
        raise typer.Exit(1) from None
    except FileNotFoundError as e:
        # Handle file not found errors
        console.print(f"[red]✗ Config file not found: {e}[/red]")
        logger.error(f"Config file not found: {e}", exc_info=True)
        raise typer.Exit(1) from None
    except Exception as e:
        # Catch any other errors and report them
        console.print(f"[red]✗ Ingestion failed: {e}[/red]")
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise typer.Exit(1) from None


# Export public API
__all__ = ["app", "ingest_swag_command"]
