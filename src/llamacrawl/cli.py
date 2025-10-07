"""CLI interface for LlamaCrawl using Typer.

This module provides the command-line interface for the LlamaCrawl RAG pipeline.
Commands include: ingest, query, status, and init.

Usage:
    llamacrawl --help
    llamacrawl ingest <source>
    llamacrawl query "<question>"
    llamacrawl status
    llamacrawl init
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from llama_index.core import Settings
from rich.console import Console

from llamacrawl.config import (
    ElasticsearchSourceConfig,
    FirecrawlSourceConfig,
    GmailSourceConfig,
    GitHubSourceConfig,
    RedditSourceConfig,
    load_config,
)
from llamacrawl.utils.logging import get_logger, setup_logging

# Import Firecrawl commands for registration
from llamacrawl import cli_firecrawl

if TYPE_CHECKING:
    from llamacrawl.models.document import QueryResult
    from llamacrawl.readers.base import BaseReader

# Version
__version__ = "0.1.0"

# Create Typer app
app = typer.Typer(
    name="llamacrawl",
    help="Multi-source RAG pipeline built on LlamaIndex",
    add_completion=False,
    no_args_is_help=True,
)

# Rich console for formatted output
console = Console()

# Register Firecrawl commands as top-level commands
app.command()(cli_firecrawl.scrape)
app.command()(cli_firecrawl.crawl)
app.command()(cli_firecrawl.map)
app.command()(cli_firecrawl.extract)

# Logger
logger = get_logger(__name__)


# =============================================================================
# Global Options and Callbacks
# =============================================================================


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to config.yaml file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    log_level: Annotated[
        str | None,
        typer.Option(
            "--log-level",
            "-l",
            help="Override LOG_LEVEL environment variable (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        ),
    ] = None,
) -> None:
    """LlamaCrawl - Multi-source RAG pipeline.

    Global options:
        --config: Path to config.yaml (default: ./config.yaml)
        --log-level: Override LOG_LEVEL environment variable
    """
    # Skip setup for commands that don't need config (version, help)
    if ctx.invoked_subcommand is None or ctx.invoked_subcommand == "version":
        return

    # Load configuration
    config_source = "default paths"
    config = None
    try:
        if config_path:
            # Load from specified path
            env_file = config_path.parent / ".env"
            config = load_config(env_file=env_file, config_file=config_path)
            config_source = str(config_path)
        else:
            # Load from default paths (./config.yaml and ./.env)
            config = load_config()

    except FileNotFoundError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        raise typer.Exit(code=2) from e
    except ValueError as e:
        console.print(f"[bold red]Configuration Validation Error:[/bold red] {e}")
        raise typer.Exit(code=2) from e
    except Exception as e:
        if not logging.getLogger().handlers:
            setup_logging(log_format="text")
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        logger.exception("Failed to load configuration")
        raise typer.Exit(code=1) from e

    if config is None:
        console.print("[bold red]Failed to load configuration[/bold red]")
        raise typer.Exit(code=1)

    effective_log_level = log_level.upper() if log_level else config.logging.level.upper()
    setup_logging(log_level=effective_log_level, log_format=config.logging.format)
    logger.info(
        "Configuration loaded",
        extra={
            "config_source": config_source,
            "log_level": effective_log_level,
            "log_format": config.logging.format,
        },
    )


# =============================================================================
# Commands
# =============================================================================


@app.command()
def version() -> None:
    """Display version information."""
    console.print(f"[bold]LlamaCrawl[/bold] version [cyan]{__version__}[/cyan]")


@app.command()
def ingest(
    source: Annotated[
        str,
        typer.Argument(help="Source to ingest (firecrawl, github, reddit, gmail, elasticsearch)"),
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
    """Trigger ingestion for a data source.

    This command loads documents from the specified source and ingests them into
    the vector store, graph database, and Redis cache.

    Examples:
        llamacrawl ingest firecrawl
        llamacrawl ingest github --full
        llamacrawl ingest reddit --limit 100
    """
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    from llamacrawl.config import get_config
    from llamacrawl.storage.redis import RedisClient

    logger.info(
        "Ingest command called",
        extra={"source": source, "full": full, "limit": limit},
    )

    # Validate source name
    valid_sources = ["firecrawl", "github", "reddit", "gmail", "elasticsearch"]
    if source not in valid_sources:
        console.print(
            f"[bold red]Error:[/bold red] Invalid source '{source}'. "
            f"Valid sources: {', '.join(valid_sources)}"
        )
        logger.error(
            f"Invalid source specified: {source}",
            extra={"source": source, "valid_sources": valid_sources},
        )
        raise typer.Exit(code=2)

    try:
        # Get configuration
        config = get_config()

        # Check if source is enabled in config
        source_config: (
            FirecrawlSourceConfig
            | GitHubSourceConfig
            | RedditSourceConfig
            | ElasticsearchSourceConfig
            | GmailSourceConfig
        )
        if source == "firecrawl":
            source_config = config.sources.firecrawl
        elif source == "github":
            source_config = config.sources.github
        elif source == "reddit":
            source_config = config.sources.reddit
        elif source == "gmail":
            source_config = config.sources.gmail
        else:  # elasticsearch
            source_config = config.sources.elasticsearch

        if not source_config.enabled:
            console.print(
                f"[bold yellow]Warning:[/bold yellow] Source '{source}' is disabled in config.yaml"
            )
            console.print("Enable it by setting 'enabled: true' in the source configuration")
            logger.warning(
                f"Attempted to ingest from disabled source: {source}",
                extra={"source": source},
            )
            raise typer.Exit(code=2)

        # Initialize Redis client
        redis_client = RedisClient(config.redis_url)

        # Check Redis health
        if not redis_client.health_check():
            console.print("[bold red]Error:[/bold red] Cannot connect to Redis")
            console.print(f"Redis URL: {config.redis_url}")
            logger.error("Redis health check failed", extra={"redis_url": config.redis_url})
            raise typer.Exit(code=1)

        # Instantiate appropriate reader class
        reader_instance: BaseReader | None = None
        try:
            if source == "firecrawl":
                from llamacrawl.readers.firecrawl import FirecrawlReader

                reader_instance = FirecrawlReader(
                    source_name=source,
                    config=source_config.model_dump(),
                    redis_client=redis_client,
                )
            elif source == "github":
                from llamacrawl.readers.github import GitHubReader

                reader_instance = GitHubReader(
                    source_name=source,
                    config=source_config.model_dump(),
                    redis_client=redis_client,
                )
            elif source == "reddit":
                from llamacrawl.readers.reddit import RedditReader

                reader_instance = RedditReader(
                    source_name=source,
                    config=source_config.model_dump(),
                    redis_client=redis_client,
                )
            elif source == "gmail":
                from llamacrawl.readers.gmail import GmailReader

                reader_instance = GmailReader(
                    source_name=source,
                    config=source_config.model_dump(),
                    redis_client=redis_client,
                )
            elif source == "elasticsearch":
                from llamacrawl.readers.elasticsearch import ElasticsearchReader

                reader_instance = ElasticsearchReader(
                    source_name=source,
                    config=source_config.model_dump(),
                    redis_client=redis_client,
                )
        except ImportError as e:
            console.print(f"[bold red]Error:[/bold red] Failed to import reader for {source}")
            console.print(f"Details: {e}")
            logger.error(
                f"Failed to import reader for source: {source}",
                extra={"source": source, "error": str(e)},
            )
            raise typer.Exit(code=1) from e
        except ValueError as e:
            # Credential validation errors from reader constructor
            console.print(f"[bold red]Credential Error:[/bold red] {e}")
            logger.error(
                f"Credential validation failed for source: {source}",
                extra={"source": source, "error": str(e)},
            )
            raise typer.Exit(code=2) from e

        # Check for distributed lock
        lock_key = f"ingest:{source}"
        with redis_client.with_lock(lock_key, ttl=3600) as lock:
            if not lock:
                console.print(
                    f"[bold yellow]Lock Error:[/bold yellow] "
                    f"Another ingestion process is already running for {source}"
                )
                console.print("Wait for the other process to complete or clear the lock manually")
                logger.warning(
                    "Failed to acquire lock for source ingestion",
                    extra={"source": source, "lock_key": lock_key},
                )
                raise typer.Exit(code=1)

            # Handle --full flag (clear cursor for full re-ingestion)
            if full:
                last_cursor = redis_client.get_cursor(source)
                if last_cursor:
                    console.print(
                        f"[bold yellow]Full re-ingestion:[/bold yellow] "
                        f"Ignoring last cursor: {last_cursor}"
                    )
                    logger.info(
                        "Full re-ingestion requested, clearing cursor",
                        extra={"source": source, "last_cursor": last_cursor},
                    )
                    # Don't delete cursor, just don't pass it to reader
                    # (reader will fetch all data)

            console.print(f"\n[bold]Starting ingestion for source:[/bold] {source}")
            if limit:
                console.print(f"Document limit: {limit}")

            # Load data from reader with progress indicator
            try:
                # Import pipeline and initialize storage clients
                from llamacrawl.embeddings.tei import TEIEmbedding
                from llamacrawl.ingestion.pipeline import IngestionPipeline
                from llamacrawl.storage.neo4j import Neo4jClient
                from llamacrawl.storage.qdrant import QdrantClient

                # Load documents from reader with progress tracking
                load_kwargs = {}
                if limit:
                    load_kwargs["limit"] = limit
                if full and reader_instance is not None:
                    # For full re-ingestion, some readers may need explicit flag
                    load_kwargs["ignore_cursor"] = True

                if reader_instance is None:
                    console.print("[bold red]Error:[/bold red] Reader instance was not initialized")
                    logger.error(
                        "Reader instance is None - this should not happen",
                        extra={"source": source},
                    )
                    raise typer.Exit(code=1)

                # Estimate total for progress bar (will be refined by reader)
                # For Reddit: limit * num_subreddits, for others: use limit or default to 100
                estimated_total = limit if limit else 100
                if source == "reddit" and source_config:
                    subreddit_count = len(source_config.model_dump().get("subreddits", []))
                    estimated_total = (limit or 1000) * max(subreddit_count, 1)

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                    console=console,
                    transient=True,  # Auto-cleanup on exit to prevent terminal corruption
                ) as progress:
                    load_task = progress.add_task(
                        "[cyan]Loading documents from source...",
                        total=estimated_total
                    )

                    # Progress callback to update the progress bar
                    def update_progress(current: int, total: int) -> None:
                        progress.update(load_task, completed=current, total=total)

                    load_kwargs["progress_callback"] = update_progress
                    documents = reader_instance.load_data(**load_kwargs)
                    progress.update(load_task, completed=estimated_total)

                console.print(f"[green]Loaded {len(documents)} documents from {source}[/green]")
                logger.info(
                    "Documents loaded from source",
                    extra={"source": source, "document_count": len(documents)},
                )

                if len(documents) == 0:
                    console.print("[yellow]No documents to ingest[/yellow]")
                    raise typer.Exit(code=0)

                # Initialize storage clients
                console.print("[cyan]Initializing storage clients...[/cyan]")
                qdrant_client = QdrantClient(
                    url=config.qdrant_url,
                    collection_name=config.vector_store.collection_name,
                    vector_dimension=config.vector_store.vector_dimension,
                    distance_metric=config.vector_store.distance_metric,
                )
                neo4j_client = Neo4jClient(config=config)
                embedding_model = TEIEmbedding(
                    base_url=config.tei_embedding_url,
                    embed_batch_size=config.ingestion.embedding_batch_size,
                )

                # Instantiate IngestionPipeline
                pipeline = IngestionPipeline(
                    config=config,
                    redis_client=redis_client,
                    qdrant_client=qdrant_client,
                    neo4j_client=neo4j_client,
                    embed_model=embedding_model,
                )

                # Process documents through pipeline
                console.print(f"[cyan]Processing {len(documents)} documents through pipeline...[/cyan]")
                summary = pipeline.ingest_documents(source, documents)

                # Display summary
                console.print("\n[bold]Ingestion Summary:[/bold]")
                console.print(f"  Total documents loaded: {summary.total}")
                console.print(f"  [green]Successfully processed: {summary.processed}[/green]")
                console.print(f"  [yellow]Deduplicated: {summary.deduplicated}[/yellow]")
                console.print(f"  [red]Failed: {summary.failed}[/red]")
                console.print(f"  Duration: {summary.duration_seconds:.2f}s")
                if summary.failed > 0:
                    console.print(f"  [dim](Check DLQ for failed documents)[/dim]")

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

                # Cleanup
                neo4j_client.close()

            except KeyboardInterrupt:
                console.print("\n[bold yellow]Ingestion interrupted by user (Ctrl+C)[/bold yellow]")
                logger.warning(
                    "Ingestion interrupted by user",
                    extra={"source": source},
                )
                raise typer.Exit(code=130) from None

            except Exception as e:
                # Reader errors (auth failures, network issues, API errors)
                console.print(f"\n[bold red]Ingestion Error:[/bold red] {e}")
                logger.exception(
                    f"Ingestion failed for source: {source}",
                    extra={"source": source},
                )
                raise typer.Exit(code=1) from e

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit codes
        raise
    except Exception as e:
        console.print(f"\n[bold red]Unexpected Error:[/bold red] {e}")
        logger.exception(
            "Unexpected error during ingestion",
            extra={"source": source},
        )
        raise typer.Exit(code=1) from e


@app.command()
def query(
    text: Annotated[
        str,
        typer.Argument(help="Query text to search for"),
    ],
    sources: Annotated[
        str | None,
        typer.Option(
            "--sources",
            help=(
                "Filter by source types "
                "(comma-separated: firecrawl,github,reddit,gmail,elasticsearch)"
            ),
        ),
    ] = None,
    after: Annotated[
        str | None,
        typer.Option(
            "--after",
            help="Filter documents after this date (YYYY-MM-DD or ISO 8601 format)",
        ),
    ] = None,
    before: Annotated[
        str | None,
        typer.Option(
            "--before",
            help="Filter documents before this date (YYYY-MM-DD or ISO 8601 format)",
        ),
    ] = None,
    top_k: Annotated[
        int | None,
        typer.Option(
            "--top-k",
            help="Number of candidates to retrieve (default from config)",
            min=1,
            max=100,
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option(
            "--output-format",
            help="Output format: text (pretty-print) or json",
        ),
    ] = "text",
) -> None:
    """Query the RAG system.

    This command searches the vector store and knowledge graph for relevant documents,
    then synthesizes an answer using the configured LLM.

    Examples:
        llamacrawl query "What are the authentication methods?"
        llamacrawl query "Recent issues" --sources github --after 2025-01-01
        llamacrawl query "Email about deployment" --sources gmail --output-format json
    """
    import json as json_lib
    from datetime import datetime

    from llamacrawl.config import get_config
    from llamacrawl.embeddings.reranker import TEIRerank
    from llamacrawl.embeddings.tei import TEIEmbedding
    from llamacrawl.query.engine import QueryEngine
    from llamacrawl.query.synthesis import AnswerSynthesizer
    from llamacrawl.storage.neo4j import Neo4jClient
    from llamacrawl.storage.qdrant import QdrantClient

    logger.info("Query command called", extra={"query": text})

    try:
        # Get configuration
        config = get_config()

        # Parse and validate sources filter
        sources_list: list[str] | None = None
        if sources:
            sources_list = [s.strip() for s in sources.split(",")]
            valid_sources = {"firecrawl", "github", "reddit", "gmail", "elasticsearch"}
            invalid_sources = [s for s in sources_list if s not in valid_sources]
            if invalid_sources:
                console.print(
                    f"[bold red]Error:[/bold red] "
                    f"Invalid source types: {', '.join(invalid_sources)}"
                )
                console.print(f"Valid sources: {', '.join(sorted(valid_sources))}")
                raise typer.Exit(code=2)

        # Parse date filters
        after_dt: datetime | None = None
        before_dt: datetime | None = None

        if after:
            try:
                after_dt = _parse_date(after)
            except ValueError as e:
                console.print(f"[bold red]Error:[/bold red] Invalid --after date: {e}")
                console.print(
                    "Use format: YYYY-MM-DD or ISO 8601 (e.g., 2025-01-01 or 2025-01-01T10:30:00Z)"
                )
                raise typer.Exit(code=2) from e

        if before:
            try:
                before_dt = _parse_date(before)
            except ValueError as e:
                console.print(f"[bold red]Error:[/bold red] Invalid --before date: {e}")
                console.print(
                    "Use format: YYYY-MM-DD or ISO 8601 (e.g., 2025-01-01 or 2025-01-01T10:30:00Z)"
                )
                raise typer.Exit(code=2) from e

        # Validate output format
        if output_format not in ["text", "json"]:
            console.print(f"[bold red]Error:[/bold red] Invalid output format: {output_format}")
            console.print("Valid formats: text, json")
            raise typer.Exit(code=2)

        # Initialize storage clients
        logger.debug("Initializing storage clients")
        qdrant_client = QdrantClient(
            url=config.qdrant_url,
            collection_name=config.vector_store.collection_name,
            vector_dimension=config.vector_store.vector_dimension,
            distance_metric=config.vector_store.distance_metric,
        )
        neo4j_client = Neo4jClient(config=config)

        # Initialize embedding model and reranker
        logger.debug("Initializing embedding model and reranker")
        embed_model = TEIEmbedding(base_url=config.tei_embedding_url)
        reranker = TEIRerank(
            base_url=config.tei_reranker_url,
            top_n=config.query.rerank_top_n,
        )

        # Initialize query engine
        logger.debug("Initializing query engine")
        query_engine = QueryEngine(
            config=config,
            qdrant_client=qdrant_client,
            neo4j_client=neo4j_client,
            embed_model=embed_model,
            reranker=reranker,
        )

        # Initialize answer synthesizer
        logger.debug("Initializing answer synthesizer")
        synthesizer = AnswerSynthesizer(config)

        # Execute query
        console.print("[bold]Executing query...[/bold]")
        logger.info(
            "Executing query",
            extra={
                "sources": sources_list,
                "after": after_dt.isoformat() if after_dt else None,
                "before": before_dt.isoformat() if before_dt else None,
                "top_k": top_k,
            },
        )

        results = query_engine.query(
            query_text=text,
            sources=sources_list,
            after=after_dt,
            before=before_dt,
            top_k=top_k,
        )

        # Check if any results found
        if not results["results"]:
            if output_format == "text":
                console.print("\n[yellow]No results found for your query.[/yellow]")
                if sources_list:
                    console.print(f"Sources filter: {', '.join(sources_list)}")
                if after_dt or before_dt:
                    console.print(f"Date range: {after or 'any'} to {before or 'any'}")
            else:
                # JSON output for no results
                empty_result = {
                    "answer": "No results found for your query.",
                    "sources": [],
                    "query_time_ms": int(results["metrics"]["total_time_ms"]),
                    "retrieved_docs": 0,
                    "reranked_docs": 0,
                }
                console.print(json_lib.dumps(empty_result, indent=2))
            raise typer.Exit(code=0)

        # Stream answer synthesis for text output, use blocking for JSON
        if output_format == "text":
            # Stream the answer token by token
            console.print("\n[bold]Answer:[/bold]")
            console.print()

            answer_parts: list[str] = []
            for delta in synthesizer.stream_synthesize(text, results["results"]):
                console.print(delta, end="")  # Print immediately without newline
                answer_parts.append(delta)

            console.print("\n")  # Final newlines after answer

            # Build query result for sources display
            from llamacrawl.models.document import QueryResult
            query_result = QueryResult(
                answer="".join(answer_parts),
                sources=synthesizer._create_source_attributions(
                    results["results"],
                    include_snippets=True
                ),
                query_time_ms=int(results["metrics"]["total_time_ms"]),
                retrieved_docs=len(results["results"]),
                reranked_docs=len(results["results"]),
            )

            # Display sources (not answer since we already streamed it)
            _display_sources_and_stats(query_result, console)
        else:
            # JSON output - use blocking synthesis
            query_result = synthesizer.synthesize(
                query_text=text,
                retrieved_docs=results["results"]
            )
            _display_json_output(query_result, console)

        logger.info(
            "Query completed successfully",
            extra={
                "num_results": len(query_result.sources),
                "query_time_ms": query_result.query_time_ms,
            },
        )

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"\n[bold red]Error executing query:[/bold red] {e}")
        logger.exception("Query execution failed")
        raise typer.Exit(code=1) from e


@app.command()
def status(
    source: Annotated[
        str | None,
        typer.Option(
            "--source",
            "-s",
            help=(
                "Show status for specific source "
                "(firecrawl, github, reddit, gmail, elasticsearch)"
            ),
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: text or json",
        ),
    ] = "text",
) -> None:
    """Show system status.

    Display the status of all infrastructure services, document counts per source,
    last sync timestamps, and any errors in the dead letter queue.

    Example:
        llamacrawl status
        llamacrawl status --source github
        llamacrawl status --format json
    """
    import json as json_lib
    from datetime import datetime

    import httpx

    from llamacrawl.config import get_config
    from llamacrawl.storage.neo4j import Neo4jClient
    from llamacrawl.storage.qdrant import QdrantClient
    from llamacrawl.storage.redis import RedisClient

    logger.info("Status command called", extra={"source": source, "format": output_format})

    # Get configuration
    config = get_config()

    # Initialize status dictionary
    status_data: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "storage": {},
        "sources": {},
    }

    # =========================================================================
    # Health Checks (with 5s timeout)
    # =========================================================================

    def check_service_health(name: str, url: str, endpoint: str = "") -> bool:
        """Check health of a service with short timeout."""
        try:
            full_url = f"{url.rstrip('/')}/{endpoint.lstrip('/')}" if endpoint else url
            response = httpx.get(full_url, timeout=5.0, follow_redirects=True)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"{name} health check failed: {e}")
            return False

    console.print("[bold]Checking service health...[/bold]")

    # Qdrant health check
    try:
        qdrant_client = QdrantClient(
            url=config.qdrant_url,
            collection_name=config.vector_store.collection_name,
            vector_dimension=config.vector_store.vector_dimension,
            distance_metric=config.vector_store.distance_metric,
        )
        qdrant_healthy = qdrant_client.health_check()
    except Exception as e:
        logger.error(f"Qdrant health check error: {e}")
        qdrant_healthy = False

    status_data["services"]["qdrant"] = {
        "healthy": qdrant_healthy,
        "url": config.qdrant_url,
    }

    # Neo4j health check
    try:
        neo4j_client = Neo4jClient(config)
        neo4j_healthy = neo4j_client.health_check()
    except Exception as e:
        logger.error(f"Neo4j health check error: {e}")
        neo4j_healthy = False

    status_data["services"]["neo4j"] = {
        "healthy": neo4j_healthy,
        "url": config.neo4j_uri,
    }

    # Redis health check
    try:
        redis_client = RedisClient(config.redis_url)
        redis_healthy = redis_client.health_check()
    except Exception as e:
        logger.error(f"Redis health check error: {e}")
        redis_healthy = False

    status_data["services"]["redis"] = {
        "healthy": redis_healthy,
        "url": config.redis_url,
    }

    # TEI Embeddings health check
    tei_embedding_healthy = check_service_health(
        "TEI Embeddings", config.tei_embedding_url, "/health"
    )
    status_data["services"]["tei_embeddings"] = {
        "healthy": tei_embedding_healthy,
        "url": config.tei_embedding_url,
    }

    # TEI Reranker health check
    tei_reranker_healthy = check_service_health(
        "TEI Reranker", config.tei_reranker_url, "/health"
    )
    status_data["services"]["tei_reranker"] = {
        "healthy": tei_reranker_healthy,
        "url": config.tei_reranker_url,
    }

    # =========================================================================
    # Storage Statistics
    # =========================================================================

    console.print("[bold]Gathering storage statistics...[/bold]")

    # Qdrant document counts
    if qdrant_healthy:
        try:
            # Total documents
            total_docs = qdrant_client.get_document_count()
            status_data["storage"]["total_documents"] = total_docs

            # Per-source document counts
            source_types = ["firecrawl", "github", "reddit", "gmail", "elasticsearch"]
            per_source_counts = {}
            for src in source_types:
                count = qdrant_client.get_document_count(source_type=src)
                if count > 0:
                    per_source_counts[src] = count

            status_data["storage"]["documents_per_source"] = per_source_counts
        except Exception as e:
            logger.error(f"Failed to get Qdrant document counts: {e}")
            status_data["storage"]["total_documents"] = 0
            status_data["storage"]["documents_per_source"] = {}
    else:
        status_data["storage"]["total_documents"] = 0
        status_data["storage"]["documents_per_source"] = {}

    # Neo4j node counts
    if neo4j_healthy:
        try:
            node_counts = neo4j_client.get_node_counts()
            status_data["storage"]["neo4j_nodes"] = node_counts
        except Exception as e:
            logger.error(f"Failed to get Neo4j node counts: {e}")
            status_data["storage"]["neo4j_nodes"] = {}
    else:
        status_data["storage"]["neo4j_nodes"] = {}

    # =========================================================================
    # Source-Specific Information
    # =========================================================================

    console.print("[bold]Gathering source information...[/bold]")

    if redis_healthy:
        try:
            # Get all sources with cursors
            sources_with_cursors = redis_client.get_all_sources_with_cursors()

            # Get DLQ information
            all_sources = ["firecrawl", "github", "reddit", "gmail", "elasticsearch"]
            if source:
                # If specific source requested, only show that one
                all_sources = [source] if source in all_sources else []

            for src in all_sources:
                source_info: dict[str, Any] = {
                    "enabled": False,
                    "last_sync": None,
                    "dlq_size": 0,
                    "dlq_sample_errors": [],
                }

                # Check if source is enabled in config
                if src == "firecrawl":
                    source_info["enabled"] = config.sources.firecrawl.enabled
                elif src == "github":
                    source_info["enabled"] = config.sources.github.enabled
                elif src == "reddit":
                    source_info["enabled"] = config.sources.reddit.enabled
                elif src == "gmail":
                    source_info["enabled"] = config.sources.gmail.enabled
                elif src == "elasticsearch":
                    source_info["enabled"] = config.sources.elasticsearch.enabled

                # Get last sync cursor
                if src in sources_with_cursors:
                    source_info["last_sync"] = sources_with_cursors[src]

                # Get DLQ size and sample errors
                dlq_size = redis_client.get_dlq_size(src)
                source_info["dlq_size"] = dlq_size

                if dlq_size > 0:
                    # Get up to 3 sample error messages
                    dlq_entries = redis_client.get_dlq(src, limit=3)
                    source_info["dlq_sample_errors"] = [
                        {
                            "error": entry.get("error", "Unknown error"),
                            "timestamp": entry.get("timestamp", 0),
                        }
                        for entry in dlq_entries
                    ]

                # Get document count from Qdrant
                if qdrant_healthy:
                    doc_count = status_data["storage"]["documents_per_source"].get(src, 0)
                    source_info["document_count"] = doc_count

                status_data["sources"][src] = source_info

        except Exception as e:
            logger.error(f"Failed to get Redis source information: {e}")
            status_data["sources"] = {}
    else:
        status_data["sources"] = {}

    # =========================================================================
    # Output Formatting
    # =========================================================================

    if output_format == "json":
        # JSON output
        console.print(json_lib.dumps(status_data, indent=2))
    else:
        # Text output (pretty-printed)
        console.print("\n[bold cyan]LlamaCrawl System Status[/bold cyan]")
        console.print(f"Timestamp: {status_data['timestamp']}\n")

        # Service health
        console.print("[bold]Infrastructure Services:[/bold]")
        for service_name, service_info in status_data["services"].items():
            health_symbol = "[green]✓[/green]" if service_info["healthy"] else "[red]✗[/red]"
            service_display = service_name.replace("_", " ").title()
            console.print(f"  {health_symbol} {service_display}: {service_info['url']}")

        # Storage statistics
        console.print("\n[bold]Storage Statistics:[/bold]")
        console.print(f"  Total Documents: {status_data['storage']['total_documents']}")

        if status_data["storage"].get("neo4j_nodes"):
            console.print("  Neo4j Nodes:")
            for label, count in status_data["storage"]["neo4j_nodes"].items():
                console.print(f"    - {label}: {count}")

        # Source information
        console.print("\n[bold]Data Sources:[/bold]")
        if status_data["sources"]:
            for src_name, src_info in status_data["sources"].items():
                enabled_text = (
                    "[green]enabled[/green]" if src_info["enabled"] else "[dim]disabled[/dim]"
                )
                console.print(f"\n  [bold]{src_name.title()}[/bold] ({enabled_text})")

                # Document count
                doc_count = src_info.get("document_count", 0)
                console.print(f"    Documents: {doc_count}")

                # Last sync
                last_sync = src_info.get("last_sync")
                if last_sync:
                    console.print(f"    Last Sync: {last_sync}")
                else:
                    console.print("    Last Sync: [dim]Never ingested[/dim]")

                # DLQ information
                dlq_size = src_info.get("dlq_size", 0)
                if dlq_size > 0:
                    console.print(f"    [yellow]DLQ Errors: {dlq_size}[/yellow]")

                    # Show sample errors
                    sample_errors = src_info.get("dlq_sample_errors", [])
                    if sample_errors:
                        console.print("    Sample Errors:")
                        for err in sample_errors[:3]:
                            error_msg = err["error"]
                            # Truncate long error messages
                            if len(error_msg) > 100:
                                error_msg = error_msg[:100] + "..."
                            console.print(f"      - {error_msg}")
                else:
                    console.print("    DLQ Errors: [green]0[/green]")
        else:
            console.print("  [dim]No source information available (Redis unavailable)[/dim]")

        console.print()

    logger.info("Status command completed successfully")


@app.command()
def init(
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force recreate collections/indexes even if they exist",
        ),
    ] = False,
) -> None:
    """Initialize infrastructure.

    Create collections in Qdrant, initialize schema in Neo4j, and verify Redis connection.
    This should be run once before first use.

    Example:
        llamacrawl init
        llamacrawl init --force  # Recreate everything (destructive!)
    """
    from llamacrawl.config import get_config
    from llamacrawl.storage.neo4j import Neo4jClient
    from llamacrawl.storage.qdrant import QdrantClient
    from llamacrawl.storage.redis import RedisClient

    logger.info("Init command called", extra={"force": force})

    # Get configuration
    config = get_config()

    # Force mode warning and confirmation
    if force:
        console.print(
            "[bold red]WARNING:[/bold red] "
            "--force will delete existing collections and data!"
        )
        console.print(
            "This operation is [bold red]destructive[/bold red] and cannot be undone."
        )
        console.print()

        confirmed = typer.confirm("Are you sure you want to proceed?", default=False)

        if not confirmed:
            console.print("[yellow]Operation cancelled by user.[/yellow]")
            logger.info("Init --force cancelled by user")
            raise typer.Exit(code=0)

        logger.warning("Init --force confirmed by user - proceeding with destructive operations")

    console.print("\n[bold cyan]Initializing LlamaCrawl Infrastructure[/bold cyan]")
    console.print("=" * 50)

    # Track overall success
    all_success = True
    steps_completed = 0
    total_steps = 3

    # =========================================================================
    # Step 1: Redis Health Check
    # =========================================================================

    console.print("\n[bold]1/3 Redis[/bold]")
    logger.info("Checking Redis connection")

    try:
        redis_client = RedisClient(config.redis_url)
        redis_healthy = redis_client.health_check()

        if redis_healthy:
            console.print("  [green]✓[/green] Redis connection successful")
            logger.info("Redis health check passed")
            steps_completed += 1
        else:
            console.print("  [red]✗[/red] Redis connection failed")
            logger.error("Redis health check failed")
            all_success = False

    except Exception as e:
        console.print(f"  [red]✗[/red] Redis connection error: {e}")
        logger.error(f"Redis connection error: {e}")
        all_success = False

    # =========================================================================
    # Step 2: Qdrant Collection Creation
    # =========================================================================

    console.print("\n[bold]2/3 Qdrant[/bold]")
    logger.info("Initializing Qdrant collection")

    try:
        qdrant_client = QdrantClient(
            url=config.qdrant_url,
            collection_name=config.vector_store.collection_name,
            vector_dimension=config.vector_store.vector_dimension,
            distance_metric=config.vector_store.distance_metric,
        )

        # Check health
        if not qdrant_client.health_check():
            console.print(f"  [red]✗[/red] Qdrant server is not accessible at {config.qdrant_url}")
            logger.error("Qdrant health check failed")
            all_success = False
        else:
            console.print("  [green]✓[/green] Qdrant server accessible")

            # Check if collection exists
            collection_exists = qdrant_client.collection_exists()

            if force and collection_exists:
                console.print(
                    f"  [yellow]![/yellow] Deleting existing collection "
                    f"'{config.vector_store.collection_name}'..."
                )
                logger.info(
                    f"Deleting existing Qdrant collection: "
                    f"{config.vector_store.collection_name}"
                )

                try:
                    qdrant_client.client.delete_collection(config.vector_store.collection_name)
                    console.print("  [green]✓[/green] Existing collection deleted")
                    collection_exists = False
                except Exception as e:
                    console.print(f"  [red]✗[/red] Failed to delete collection: {e}")
                    logger.error(f"Failed to delete Qdrant collection: {e}")
                    all_success = False

            # Create collection if it doesn't exist
            if not collection_exists:
                console.print(
                    f"  [yellow]![/yellow] Creating collection "
                    f"'{config.vector_store.collection_name}'..."
                )
                logger.info(
                    f"Creating Qdrant collection: {config.vector_store.collection_name}"
                )

                try:
                    qdrant_client.create_collection(
                        hnsw_m=config.vector_store.hnsw.m,
                        hnsw_ef_construct=config.vector_store.hnsw.ef_construct,
                        enable_quantization=config.vector_store.enable_quantization,
                    )
                    console.print("  [green]✓[/green] Collection created successfully")
                    console.print(f"    - Vector dimension: {config.vector_store.vector_dimension}")
                    console.print(f"    - Distance metric: {config.vector_store.distance_metric}")
                    quant_status = (
                        "enabled" if config.vector_store.enable_quantization else "disabled"
                    )
                    console.print(f"    - Quantization: {quant_status}")
                    logger.info("Qdrant collection created successfully")
                    steps_completed += 1
                except Exception as e:
                    console.print(f"  [red]✗[/red] Failed to create collection: {e}")
                    logger.error(f"Failed to create Qdrant collection: {e}")
                    all_success = False
            else:
                console.print(
                    f"  [green]✓[/green] Collection "
                    f"'{config.vector_store.collection_name}' already exists"
                )
                logger.info("Qdrant collection already exists")
                steps_completed += 1

    except Exception as e:
        console.print(f"  [red]✗[/red] Qdrant initialization error: {e}")
        logger.error(f"Qdrant initialization error: {e}")
        all_success = False

    # =========================================================================
    # Step 3: Neo4j Schema Initialization
    # =========================================================================

    console.print("\n[bold]3/3 Neo4j[/bold]")
    logger.info("Initializing Neo4j schema")

    try:
        neo4j_client = Neo4jClient(config)

        # Check health
        if not neo4j_client.health_check():
            console.print(f"  [red]✗[/red] Neo4j server is not accessible at {config.neo4j_uri}")
            logger.error("Neo4j health check failed")
            all_success = False
        else:
            console.print("  [green]✓[/green] Neo4j server accessible")

            # Initialize schema (constraints and indexes)
            console.print("  [yellow]![/yellow] Initializing schema (constraints and indexes)...")
            logger.info("Initializing Neo4j schema")

            try:
                neo4j_client.initialize_schema()
                console.print("  [green]✓[/green] Schema initialized successfully")
                console.print("    - Constraints created for unique identifiers")
                console.print("    - Indexes created for query optimization")
                logger.info("Neo4j schema initialized successfully")
                steps_completed += 1
            except Exception as e:
                console.print(f"  [red]✗[/red] Failed to initialize schema: {e}")
                logger.error(f"Failed to initialize Neo4j schema: {e}")
                all_success = False

        # Clean up connection
        neo4j_client.close()

    except Exception as e:
        console.print(f"  [red]✗[/red] Neo4j initialization error: {e}")
        logger.error(f"Neo4j initialization error: {e}")
        all_success = False

    # =========================================================================
    # Summary
    # =========================================================================

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
    else:
        console.print("[bold red]✗ Infrastructure initialization failed[/bold red]")
        console.print(f"Completed {steps_completed}/{total_steps} steps.")
        console.print()
        console.print(
            "[dim]Please check the errors above and "
            "ensure all services are running:[/dim]"
        )
        console.print(f"  - Qdrant: {config.qdrant_url}")
        console.print(f"  - Neo4j: {config.neo4j_uri}")
        console.print(f"  - Redis: {config.redis_url}")
        logger.error("Infrastructure initialization failed")
        raise typer.Exit(code=1)


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_date(date_str: str) -> datetime:
    """Parse date string in multiple formats.

    Supports:
    - YYYY-MM-DD (e.g., 2025-01-01)
    - ISO 8601 (e.g., 2025-01-01T10:30:00Z, 2025-01-01T10:30:00+00:00)

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If date string cannot be parsed
    """
    # Try YYYY-MM-DD format first
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass

    # Try ISO 8601 format
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        pass

    # If both fail, raise error
    raise ValueError(
        f"Could not parse date '{date_str}'. Use YYYY-MM-DD or ISO 8601 format."
    )


def _build_query_result_from_engine_output(engine_output: dict[str, Any]) -> "QueryResult":
    """Use AnswerSynthesizer for proper synthesis."""
    from llamacrawl.config import get_config
    from llamacrawl.query.synthesis import AnswerSynthesizer
    
    config = get_config()
    synthesizer = AnswerSynthesizer(config)
    return synthesizer.synthesize(
        query_text=engine_output["query"],
        retrieved_docs=engine_output["results"]
    )


def _display_sources_and_stats(query_result: "QueryResult", console: Console) -> None:
    """Display sources and statistics (for streaming mode where answer already shown).

    Args:
        query_result: QueryResult model
        console: Rich console instance
    """
    from rich.table import Table

    # Display sources
    console.print("\n[bold cyan]Sources:[/bold cyan]")
    if query_result.sources:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="cyan")
        table.add_column("Source", style="green")
        table.add_column("Score", justify="right", style="yellow")
        table.add_column("Timestamp", style="dim")

        for i, source in enumerate(query_result.sources, 1):
            table.add_row(
                str(i),
                source.title[:50] + "..." if len(source.title) > 50 else source.title,
                source.source_type,
                f"{source.score:.3f}",
                source.timestamp.strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)

        # Display snippets
        console.print("\n[bold cyan]Snippets:[/bold cyan]")
        for i, source in enumerate(query_result.sources, 1):
            console.print(f"\n[bold][{i}] {source.title}[/bold]")
            console.print(f"  {source.snippet}")
            console.print(f"  [dim]{source.url}[/dim]")
    else:
        console.print("[dim]No sources found[/dim]")

    # Display stats
    console.print("\n[bold]Query Statistics:[/bold]")
    console.print(f"  Retrieved: {query_result.retrieved_docs} documents")
    console.print(f"  Reranked: {query_result.reranked_docs} documents")
    console.print(f"  Query time: {query_result.query_time_ms}ms")


def _display_text_output(query_result: "QueryResult", console: Console) -> None:
    """Display query results in pretty text format (blocking mode).

    Args:
        query_result: QueryResult model
        console: Rich console instance
    """
    from rich.panel import Panel

    # Display answer
    console.print("\n[bold cyan]Answer:[/bold cyan]")
    console.print(Panel(query_result.answer, border_style="cyan"))

    # Display sources and stats
    _display_sources_and_stats(query_result, console)


def _display_json_output(query_result: "QueryResult", console: Console) -> None:
    """Display query results in JSON format.

    Args:
        query_result: QueryResult model
        console: Rich console instance
    """

    # Serialize QueryResult to JSON
    json_output = query_result.model_dump_json(indent=2)
    console.print(json_output)


# =============================================================================
# Entry Point
# =============================================================================


def cli() -> None:
    """Main CLI entry point with error handling."""
    try:
        app()
    except typer.Exit:
        # Typer.Exit is expected, just re-raise
        raise
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupted by user[/bold yellow]")
        logger.info("Application interrupted by user (Ctrl+C)")
        # Reset terminal state
        sys.stdout.write('\033[0m')
        sys.stdout.flush()
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        console.print(f"\n[bold red]Unexpected Error:[/bold red] {e}")
        logger.exception("Unexpected error in CLI")
        # Reset terminal state to prevent corruption
        sys.stdout.write('\033[0m')
        sys.stdout.flush()
        sys.exit(1)


if __name__ == "__main__":
    cli()
