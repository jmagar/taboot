"""Ingest web command for Taboot CLI.

Implements the web ingestion workflow using IngestWebUseCase:
1. Accept URL and optional limit
2. Create and configure all dependencies (WebReader, Normalizer, Chunker, Embedder, QdrantWriter)
3. Execute IngestWebUseCase
4. Display progress and results
5. Handle errors gracefully

This command is thin - all business logic is in packages/core/use_cases/ingest_web.py.
"""

from __future__ import annotations

import logging
from contextlib import ExitStack
from datetime import UTC, datetime
from typing import Annotated

import typer
from rich.console import Console

from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.common.config import get_config
from packages.common.db_schema import get_postgres_client
from packages.core.use_cases.ingest_web import IngestWebUseCase
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.web import WebReader
from packages.schemas.models import JobState
from packages.vector.writer import QdrantWriter

console = Console()
logger = logging.getLogger(__name__)

app = typer.Typer(name="ingest", help="Ingest documents from various sources")


@app.command(name="web")
def ingest_web_command(
    url: Annotated[str, typer.Argument(..., help="URL to crawl and ingest")],
    limit: Annotated[
        int | None, typer.Option("--limit", "-l", help="Maximum number of pages to crawl")
    ] = None,
) -> None:
    """Ingest web documents into the knowledge graph.

    Orchestrates the full ingestion pipeline:
    WebReader → Normalizer → Chunker → Embedder → QdrantWriter

    Args:
        url: URL to crawl and ingest.
        limit: Optional maximum number of pages to crawl.

    Example:
        uv run apps/cli ingest web https://example.com --limit 20

    Expected output:
        ✓ Starting ingestion: https://example.com (limit: 20)
        ✓ Job ID: 123e4567-e89b-12d3-a456-426614174000
        ✓ 18 pages crawled
        ✓ 342 chunks created
        ✓ Duration: 45s

    Raises:
        typer.Exit: Exit with code 1 if ingestion fails.
    """
    try:
        # Load config
        config = get_config()

        # Display starting message
        limit_str = f"limit: {limit}" if limit else "no limit"
        console.print(f"[yellow]Starting ingestion: {url} ({limit_str})[/yellow]")

        # Create dependencies
        logger.info("Creating ingestion pipeline dependencies")

        web_reader = WebReader(
            firecrawl_url=config.firecrawl_api_url,
            firecrawl_api_key=config.firecrawl_api_key.get_secret_value(),
        )
        normalizer = Normalizer()
        chunker = Chunker()

        # Initialize resources with ExitStack to ensure cleanup
        with ExitStack() as stack:
            embedder = Embedder(tei_url=config.tei_embedding_url)
            stack.callback(embedder.close)

            qdrant_writer = QdrantWriter(
                url=config.qdrant_url,
                collection_name=config.collection_name,
            )
            stack.callback(qdrant_writer.close)

            pg_conn = get_postgres_client()
            stack.callback(pg_conn.close)

            document_store = PostgresDocumentStore(pg_conn)
            stack.callback(document_store.close)

            # Create use case
            use_case = IngestWebUseCase(
                web_reader=web_reader,
                normalizer=normalizer,
                chunker=chunker,
                embedder=embedder,
                qdrant_writer=qdrant_writer,
                document_store=document_store,
                collection_name=config.collection_name,
            )

            # Track start time for duration calculation
            start_time = datetime.now(UTC)

            # Execute ingestion
            logger.info("Executing web ingestion for %s", url)
            job = use_case.execute(url=url, limit=limit)

            # Calculate duration
            end_time = datetime.now(UTC)
            duration_seconds = (end_time - start_time).total_seconds()

            # Display results based on job state
            if job.state == JobState.COMPLETED:
                console.print(f"[green]✓ Job ID: {job.job_id}[/green]")
                console.print(f"[green]✓ {job.pages_processed} pages crawled[/green]")
                console.print(f"[green]✓ {job.chunks_created} chunks created[/green]")
                console.print(f"[green]✓ Duration: {duration_seconds:.0f}s[/green]")
                logger.info(
                    "Ingestion completed: %s pages, %s chunks in %ss",
                    job.pages_processed,
                    job.chunks_created,
                    f"{duration_seconds:.0f}",
                )

            elif job.state == JobState.FAILED:
                # Display failure message
                console.print(f"[red]✗ Job ID: {job.job_id}[/red]")
                console.print("[red]✗ Ingestion failed[/red]")

                # Display errors if available
                if job.errors:
                    console.print("[red]Errors:[/red]")
                    for error_entry in job.errors:
                        error_msg = error_entry.get("error", "Unknown error")
                        console.print(f"  - {error_msg}")

                logger.error("Ingestion failed for %s", url)
                raise typer.Exit(1)

            else:
                # Unexpected state
                console.print(f"[yellow]⚠ Job ID: {job.job_id}[/yellow]")
                console.print(f"[yellow]⚠ Unexpected job state: {job.state}[/yellow]")
                logger.warning("Unexpected job state: %s", job.state)
                raise typer.Exit(1)

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit code
        raise
    except Exception as e:
        # Catch any other errors and report them
        console.print(f"[red]✗ Ingestion failed: {e}[/red]")
        logger.exception("Ingestion failed for %s", url)
        raise typer.Exit(1) from e


def _register_subcommands() -> None:
    """Register subcommands dynamically to avoid circular imports."""
    # Register docker-compose subcommand
    from taboot_cli.commands.ingest_docker_compose import (
        ingest_docker_compose_command,
    )

    app.command(name="docker-compose")(ingest_docker_compose_command)

    # Register external API subcommands
    from taboot_cli.commands.ingest_elasticsearch import (
        ingest_elasticsearch_command,
    )
    from taboot_cli.commands.ingest_github import ingest_github_command
    from taboot_cli.commands.ingest_gmail import ingest_gmail_command
    from taboot_cli.commands.ingest_reddit import ingest_reddit_command
    from taboot_cli.commands.ingest_youtube import ingest_youtube_command

    app.command(name="github")(ingest_github_command)
    app.command(name="reddit")(ingest_reddit_command)
    app.command(name="youtube")(ingest_youtube_command)
    app.command(name="gmail")(ingest_gmail_command)
    app.command(name="elasticsearch")(ingest_elasticsearch_command)


# Register subcommands on module load
_register_subcommands()


# Export public API
__all__ = ["app", "ingest_web_command"]
