"""Ingest Docker Compose command for Taboot CLI.

Implements the Docker Compose ingestion workflow using the core use-case:
1. Accept file path argument
2. Parse docker-compose.yaml via DockerComposeReader
3. Convert raw dictionaries into Pydantic schema models
4. Persist nodes and relationships with DockerComposeWriter
5. Display ingest statistics and handle errors gracefully
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

import typer
from rich.console import Console

from packages.core.use_cases.ingest_docker_compose import IngestDockerComposeUseCase
from packages.graph.client import Neo4jClient
from packages.graph.writers.docker_compose_writer import DockerComposeWriter
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
        # Display starting message
        console.print(f"[yellow]Starting ingestion: {file_path}[/yellow]")

        # Track start time for duration calculation
        start_time = datetime.now(UTC)

        logger.info("Parsing docker-compose file: %s", file_path)
        reader = DockerComposeReader()

        # Execute use-case within Neo4j client context
        with Neo4jClient() as neo4j_client:
            writer = DockerComposeWriter(neo4j_client)
            use_case = IngestDockerComposeUseCase(reader=reader, writer=writer)
            result = use_case.execute(file_path=file_path)

        console.print(f"[green]✓ Nodes written: {result.total_nodes}[/green]")
        console.print(
            f"[green]✓ DEPENDS_ON relationships written: {result.total_relationships}[/green]"
        )
        console.print(
            f"[green]✓ Compose services: {result.compose_services} | Port bindings: {result.port_bindings}[/green]"
        )

        # Calculate duration
        end_time = datetime.now(UTC)
        duration_seconds = (end_time - start_time).total_seconds()

        # Display success
        console.print(f"[green]✓ Duration: {duration_seconds:.0f}s[/green]")

        logger.info(
            "Docker Compose ingestion completed: nodes=%s relationships=%s duration=%ss",
            result.total_nodes,
            result.total_relationships,
            f"{duration_seconds:.0f}",
        )

    except DockerComposeError as e:
        # Handle specific DockerComposeReader errors
        console.print(f"[red]✗ Docker Compose error: {e}[/red]")
        logger.exception("Docker Compose ingestion failed for %s", file_path)
        raise typer.Exit(1) from None

    except InvalidYAMLError as e:
        # Handle YAML parsing errors
        console.print(f"[red]✗ Invalid YAML: {e}[/red]")
        logger.exception("Invalid YAML in %s", file_path)
        raise typer.Exit(1) from None

    except InvalidPortError as e:
        # Handle port validation errors
        console.print(f"[red]✗ Invalid port: {e}[/red]")
        logger.exception("Invalid port in %s", file_path)
        raise typer.Exit(1) from None

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit code
        raise

    except Exception as e:
        # Catch any other errors and report them
        console.print(f"[red]✗ Ingestion failed: {e}[/red]")
        logger.exception("Ingestion failed for %s", file_path)
        raise typer.Exit(1) from None


# Export public API
__all__ = ["ingest_docker_compose_command"]
