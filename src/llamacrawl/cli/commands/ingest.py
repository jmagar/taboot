"""Ingestion command implementation."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from llamacrawl.cli.context import CLIState
from llamacrawl.config import (
    ElasticsearchSourceConfig,
    FirecrawlSourceConfig,
    GitHubSourceConfig,
    GmailSourceConfig,
    RedditSourceConfig,
)
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)


def _ensure_state(ctx: typer.Context) -> CLIState:
    """Retrieve CLI state that was initialized during the callback."""
    state = ctx.ensure_object(CLIState)
    if not isinstance(state, CLIState):
        console = Console()
        console.print("[bold red]Failed to initialize CLI state[/bold red]")
        raise typer.Exit(code=1)
    return state


def _build_reader(
    source: str,
    source_config: (
        FirecrawlSourceConfig
        | GitHubSourceConfig
        | RedditSourceConfig
        | ElasticsearchSourceConfig
        | GmailSourceConfig
    ),
    redis_client: RedisClient,
) -> Any:
    """Instantiate the reader for the requested source."""
    if source == "firecrawl":
        from llamacrawl.readers.firecrawl import FirecrawlReader

        return FirecrawlReader(
            source_name=source,
            config=source_config.model_dump(),
            redis_client=redis_client,
        )

    if source == "github":
        from llamacrawl.readers.github import GitHubReader

        return GitHubReader(
            source_name=source,
            config=source_config.model_dump(),
            redis_client=redis_client,
        )

    if source == "reddit":
        from llamacrawl.readers.reddit import RedditReader

        return RedditReader(
            source_name=source,
            config=source_config.model_dump(),
            redis_client=redis_client,
        )

    if source == "gmail":
        from llamacrawl.readers.gmail import GmailReader

        return GmailReader(
            source_name=source,
            config=source_config.model_dump(),
            redis_client=redis_client,
        )

    from llamacrawl.readers.elasticsearch import ElasticsearchReader

    return ElasticsearchReader(
        source_name=source,
        config=source_config.model_dump(),
        redis_client=redis_client,
    )


def ingest(
    ctx: typer.Context,
    source: Annotated[
        str,
        typer.Argument(
            help="Source to ingest (firecrawl, github, reddit, gmail, elasticsearch)",
        ),
    ],
    full: Annotated[
        bool,
        typer.Option(
            "--full",
            "-f",
            help="Force full re-ingestion (ignore cursor and re-process all documents)",
        ),
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-n",
            help="Limit number of documents to ingest",
            min=1,
        ),
    ] = None,
) -> None:
    """Trigger ingestion for a data source."""
    state = _ensure_state(ctx)
    console = state.console
    config = state.config

    logger.info(
        "Ingest command invoked",
        extra={"source": source, "full": full, "limit": limit},
    )

    valid_sources = {"firecrawl", "github", "reddit", "gmail", "elasticsearch"}
    if source not in valid_sources:
        console.print(
            f"[bold red]Error:[/bold red] Invalid source '{source}'. "
            f"Valid sources: {', '.join(sorted(valid_sources))}",
        )
        raise typer.Exit(code=2)

    if source == "firecrawl":
        source_config = config.sources.firecrawl
    elif source == "github":
        source_config = config.sources.github
    elif source == "reddit":
        source_config = config.sources.reddit
    elif source == "gmail":
        source_config = config.sources.gmail
    else:
        source_config = config.sources.elasticsearch

    if not source_config.enabled:
        console.print(
            f"[bold yellow]Warning:[/bold yellow] Source '{source}' is disabled in config.yaml",
        )
        console.print("Enable it by setting 'enabled: true' in the source configuration")
        raise typer.Exit(code=2)

    redis_client = RedisClient(config.redis_url)

    if not redis_client.health_check():
        console.print("[bold red]Error:[/bold red] Cannot connect to Redis")
        console.print(f"Redis URL: {config.redis_url}")
        raise typer.Exit(code=1)

    try:
        reader_instance = _build_reader(source, source_config, redis_client)
    except ImportError as error:
        console.print(
            f"[bold red]Error:[/bold red] Failed to import reader for {source}",
        )
        console.print(f"Details: {error}")
        raise typer.Exit(code=1) from error
    except ValueError as error:
        console.print(f"[bold red]Credential Error:[/bold red] {error}")
        raise typer.Exit(code=2) from error

    lock_key = f"ingest:{source}"
    with redis_client.with_lock(lock_key, ttl=3600) as lock:
        if not lock:
            console.print(
                f"[bold yellow]Lock Error:[/bold yellow] "
                f"Another ingestion process is already running for {source}",
            )
            console.print("Wait for the other process to complete or clear the lock manually")
            raise typer.Exit(code=1)

        console.print(f"\n[bold]Starting ingestion for source:[/bold] {source}")
        if limit:
            console.print(f"Document limit: {limit}")

        load_kwargs: dict[str, Any] = {}
        if limit is not None:
            load_kwargs["limit"] = limit
        if full:
            load_kwargs["ignore_cursor"] = True

        last_progress: dict[str, int] = {"completed": 0}

        def _progress_callback(current: int, total: int) -> None:
            last_progress["completed"] = current
            progress.update(
                task_id,
                completed=current,
                total=max(total, 1),
            )

        def _status_callback(message: str) -> None:
            progress.update(
                task_id,
                description=f"[cyan]{message}",
            )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task_id = progress.add_task(
                "[cyan]Loading documents from source...",
                total=1,
            )
            load_kwargs["progress_callback"] = _progress_callback
            load_kwargs["status_callback"] = _status_callback

            try:
                documents = reader_instance.load_data(**load_kwargs)
            finally:
                final_completed = max(last_progress["completed"], 1)
                progress.update(
                    task_id,
                    completed=final_completed,
                    total=final_completed,
                )

        console.print(f"[green]Loaded {len(documents)} documents from {source}[/green]")

        if not documents:
            console.print("[yellow]No documents to ingest[/yellow]")
            return

        console.print("[cyan]Initializing storage clients...[/cyan]")

        from llamacrawl.embeddings.tei import TEIEmbedding
        from llamacrawl.ingestion.pipeline import IngestionPipeline
        from llamacrawl.storage.neo4j import Neo4jClient
        from llamacrawl.storage.qdrant import QdrantClient

        qdrant_client = QdrantClient(
            url=config.qdrant_url,
            collection_name=config.vector_store.collection_name,
            vector_dimension=config.vector_store.vector_dimension,
            distance_metric=config.vector_store.distance_metric,
        )
        neo4j_client = Neo4jClient(config=config)
        embed_model = TEIEmbedding(
            base_url=config.tei_embedding_url,
            embed_batch_size=config.ingestion.embedding_batch_size,
        )

        pipeline = IngestionPipeline(
            config=config,
            redis_client=redis_client,
            qdrant_client=qdrant_client,
            neo4j_client=neo4j_client,
            embed_model=embed_model,
        )

        try:
            console.print(
                f"[cyan]Processing {len(documents)} documents through pipeline...[/cyan]",
            )
            summary = pipeline.ingest_documents(source, documents)
        finally:
            neo4j_client.close()

        console.print("\n[bold]Ingestion Summary:[/bold]")
        console.print(f"  Total documents loaded: {summary.total}")
        console.print(f"  [green]Successfully processed: {summary.processed}[/green]")
        console.print(f"  [yellow]Deduplicated: {summary.deduplicated}[/yellow]")
        console.print(f"  [red]Failed: {summary.failed}[/red]")
        console.print(f"  Duration: {summary.duration_seconds:.2f}s")
        if summary.failed > 0:
            console.print("  [dim](Check DLQ for failed documents)[/dim]")

        logger.info(
            "Ingestion completed",
            extra={
                "source": source,
                "total": summary.total,
                "processed": summary.processed,
                "deduplicated": summary.deduplicated,
                "failed": summary.failed,
                "duration_seconds": summary.duration_seconds,
            },
        )
