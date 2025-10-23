"""Ingest Docker Compose command for Taboot CLI.

Implements Docker Compose YAML ingestion workflow:
1. Accept file path argument
2. Parse docker-compose.yaml file using DockerComposeReader
3. Extract Service nodes with image and version
4. Extract DEPENDS_ON and BINDS relationships
5. Write nodes and relationships to Neo4j using BatchedGraphWriter
6. Display progress and results

This command is thin - parsing logic is in packages/ingest/readers/docker_compose.py,
and graph writing is in packages/graph/writers/batched.py.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Annotated

import typer
from rich.console import Console

from packages.common.config import get_config
from packages.graph.client import Neo4jClient
from packages.graph.writers.batched import BatchedGraphWriter
from packages.ingest.readers.docker_compose import (
    DockerComposeError,
    DockerComposeReader,
    InvalidPortError,
    InvalidYAMLError,
)

console = Console()
logger = logging.getLogger(__name__)


def ingest_docker_compose_command(
    file_path: Annotated[str, typer.Argument(..., help="Path to docker-compose.yaml file")],
) -> None:
    """Ingest Docker Compose YAML into the knowledge graph.

    Parses docker-compose.yaml and extracts:
    - Service nodes (name, image, version)
    - DEPENDS_ON relationships
    - BINDS relationships (port bindings)

    Args:
        file_path: Path to docker-compose.yaml file.

    Example:
        uv run apps/cli ingest docker-compose docker-compose.yaml
        uv run apps/cli ingest docker-compose /path/to/docker-compose.yaml

    Expected output:
        ✓ Starting ingestion: docker-compose.yaml
        ✓ 3 services extracted
        ✓ 5 relationships extracted
        ✓ 3 services written to Neo4j
        ✓ 5 relationships written to Neo4j
        ✓ Duration: 2s

    Raises:
        typer.Exit: Exit with code 1 if ingestion fails.
    """
    try:
        # Load config
        config = get_config()

        # Display starting message
        console.print(f"[yellow]Starting ingestion: {file_path}[/yellow]")

        # Track start time for duration calculation
        start_time = datetime.now(UTC)

        # Create reader and load data
        logger.info(f"Parsing docker-compose file: {file_path}")
        reader = DockerComposeReader()
        data = reader.load_data(file_path=file_path)

        # Extract services and relationships
        services = data["services"]
        relationships = data["relationships"]

        console.print(f"[green]✓ {len(services)} services extracted[/green]")
        console.print(f"[green]✓ {len(relationships)} relationships extracted[/green]")

        # Write to Neo4j
        logger.info("Writing services and relationships to Neo4j")
        asyncio.run(
            _write_to_neo4j(
                config=config,
                services=services,
                relationships=relationships,
            )
        )

        # Calculate duration
        end_time = datetime.now(UTC)
        duration_seconds = (end_time - start_time).total_seconds()

        # Display success
        console.print(f"[green]✓ {len(services)} services written to Neo4j[/green]")
        console.print(f"[green]✓ {len(relationships)} relationships written to Neo4j[/green]")
        console.print(f"[green]✓ Duration: {duration_seconds:.0f}s[/green]")

        logger.info(
            f"Docker Compose ingestion completed: {len(services)} services, "
            f"{len(relationships)} relationships in {duration_seconds:.0f}s"
        )

    except DockerComposeError as e:
        # Handle specific DockerComposeReader errors
        console.print(f"[red]✗ Docker Compose error: {e}[/red]")
        logger.error(f"Docker Compose ingestion failed for {file_path}: {e}", exc_info=True)
        raise typer.Exit(1) from None

    except InvalidYAMLError as e:
        # Handle YAML parsing errors
        console.print(f"[red]✗ Invalid YAML: {e}[/red]")
        logger.error(f"Invalid YAML in {file_path}: {e}", exc_info=True)
        raise typer.Exit(1) from None

    except InvalidPortError as e:
        # Handle port validation errors
        console.print(f"[red]✗ Invalid port: {e}[/red]")
        logger.error(f"Invalid port in {file_path}: {e}", exc_info=True)
        raise typer.Exit(1) from None

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit code
        raise

    except Exception as e:
        # Catch any other errors and report them
        console.print(f"[red]✗ Ingestion failed: {e}[/red]")
        logger.error(f"Ingestion failed for {file_path}: {e}", exc_info=True)
        raise typer.Exit(1) from None


async def _write_to_neo4j(
    config: object,
    services: list[dict[str, str]],
    relationships: list[dict[str, str | int]],
) -> None:
    """Write services and relationships to Neo4j using BatchedGraphWriter.

    Args:
        config: Application configuration object.
        services: List of service dictionaries with name, image, version.
        relationships: List of relationship dictionaries with type, source, target/port.
    """
    # Create Neo4j client
    client = Neo4jClient()
    client.connect()

    # Create batched writer
    writer = BatchedGraphWriter(client=client, batch_size=2000)

    try:
        # Write Service nodes
        await writer.batch_write_nodes(
            label="Service",
            nodes=services,
            unique_key="name",
        )

        # Separate DEPENDS_ON and BINDS relationships
        depends_on_rels = [rel for rel in relationships if rel["type"] == "DEPENDS_ON"]
        binds_rels = [rel for rel in relationships if rel["type"] == "BINDS"]

        # Write DEPENDS_ON relationships
        if depends_on_rels:
            # Transform to format expected by batch_write_relationships
            depends_on_formatted: list[dict[str, str | dict[str, str | int]]] = [
                {
                    "source_value": str(rel["source"]),
                    "target_value": str(rel["target"]),
                    "rel_properties": {},
                }
                for rel in depends_on_rels
            ]

            await writer.batch_write_relationships(
                source_label="Service",
                source_key="name",
                target_label="Service",
                target_key="name",
                rel_type="DEPENDS_ON",
                relationships=depends_on_formatted,
            )

        # Write BINDS relationships (Service to Port)
        # Note: For BINDS, we need to handle port/protocol properties
        if binds_rels:
            # For BINDS relationships, we'll store port and protocol as relationship properties
            # Since there's no explicit Port node in the data model, we store as properties
            binds_formatted = [
                {
                    "source_value": rel["source"],
                    "target_value": rel["source"],  # Self-reference for now
                    "rel_properties": {
                        "port": rel["port"],
                        "protocol": rel["protocol"],
                    },
                }
                for rel in binds_rels
            ]

            await writer.batch_write_relationships(
                source_label="Service",
                source_key="name",
                target_label="Service",
                target_key="name",
                rel_type="BINDS",
                relationships=binds_formatted,
            )

    finally:
        # Clean up client connection (not async)
        client.close()


# Export public API
__all__ = ["ingest_docker_compose_command"]
