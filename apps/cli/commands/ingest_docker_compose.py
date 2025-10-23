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

import logging
from datetime import UTC, datetime
from typing import Annotated

import typer
from rich.console import Console

from packages.common.config import get_config
from packages.graph.client import Neo4jClient
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

        # Create reader and load data
        logger.info("Parsing docker-compose file: %s", file_path)
        reader = DockerComposeReader()
        data = reader.load_data(file_path=file_path)

        # Extract services and relationships
        services = data["services"]
        relationships = data["relationships"]

        console.print(f"[green]✓ {len(services)} services extracted[/green]")
        console.print(f"[green]✓ {len(relationships)} relationships extracted[/green]")

        # Write to Neo4j
        logger.info("Writing services and relationships to Neo4j")
        _write_to_neo4j(
            services=services,
            relationships=relationships,
        )

        # Calculate duration
        end_time = datetime.now(UTC)
        duration_seconds = (end_time - start_time).total_seconds()

        # Display success
        console.print(f"[green]✓ {len(services)} services written to Neo4j[/green]")
        console.print(f"[green]✓ {len(relationships)} relationships written to Neo4j[/green]")
        console.print(f"[green]✓ Duration: {duration_seconds:.0f}s[/green]")

        logger.info(
            "Docker Compose ingestion completed: %s services, %s relationships in %ss",
            len(services),
            len(relationships),
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


def _write_to_neo4j(
    services: list[dict[str, str]],
    relationships: list[dict[str, str | int]],
) -> None:
    """Write services and relationships to Neo4j using direct Cypher queries.

    Args:
        services: List of service dictionaries with name, image, version.
        relationships: List of relationship dictionaries with type, source, target/port.
    """
    # Create Neo4j client
    client = Neo4jClient()
    client.connect()

    try:
        with client.session() as session:
            # Write Service nodes
            for service in services:
                query = """
                MERGE (s:Service {name: $name})
                SET s.image = $image,
                    s.version = $version
                RETURN s
                """
                session.run(
                    query,
                    {
                        "name": service["name"],
                        "image": service.get("image", ""),
                        "version": service.get("version", ""),
                    },
                )

            # Write relationships
            for rel in relationships:
                if rel["type"] == "DEPENDS_ON":
                    query = """
                    MATCH (source:Service {name: $source}),
                          (target:Service {name: $target})
                    MERGE (source)-[:DEPENDS_ON]->(target)
                    """
                    session.run(
                        query,
                        {
                            "source": str(rel["source"]),
                            "target": str(rel["target"]),
                        },
                    )

                elif rel["type"] == "BINDS":
                    query = """
                    MATCH (s:Service {name: $service})
                    MERGE (s)-[b:BINDS]->(s)
                    SET b.port = $port,
                        b.protocol = $protocol
                    """
                    session.run(
                        query,
                        {
                            "service": rel["source"],
                            "port": rel["port"],
                            "protocol": rel["protocol"],
                        },
                    )

    finally:
        # Clean up client connection
        client.close()


# Export public API
__all__ = ["ingest_docker_compose_command"]
