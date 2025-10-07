"""Firecrawl-specific CLI commands for LlamaCrawl.

This module provides direct URL-based commands for Firecrawl operations:
- scrape: Single page scraping
- crawl: Full website crawling
- map: Sitemap-based URL discovery
- extract: AI-powered structured data extraction

Usage:
    llamacrawl scrape <url>
    llamacrawl crawl <url> --limit 100 --max-depth 2
    llamacrawl map <url> --limit 1000
    llamacrawl extract <url> --prompt "Extract product info"
"""

from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from llamacrawl.config import load_config
from llamacrawl.embeddings.tei import TEIEmbedding
from llamacrawl.ingestion.language_filter import (
    build_language_filter_from_config,
    filter_documents_by_language,
)
from llamacrawl.ingestion.pipeline import IngestionPipeline
from llamacrawl.readers.firecrawl import FirecrawlReader
from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.storage.qdrant import QdrantClient
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


def _validate_url(url: str) -> bool:
    """Validate URL format.

    Args:
        url: URL to validate

    Returns:
        True if valid, raises typer.BadParameter if invalid

    Raises:
        typer.BadParameter: If URL is invalid
    """
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise typer.BadParameter(f"Invalid URL format: {url}")
        if result.scheme not in ["http", "https"]:
            raise typer.BadParameter(f"URL must use http or https: {url}")
        return True
    except ValueError as e:
        raise typer.BadParameter(f"Invalid URL: {e}")


def _run_firecrawl_map(url: str, limit: int) -> None:
    """Map URLs from a website without ingesting content.

    Args:
        url: Base URL to map
        limit: Maximum number of URLs to discover

    Raises:
        typer.Exit: If map operation fails
    """
    # Validate URL
    _validate_url(url)

    # Load minimal config (only need Firecrawl API access)
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        raise typer.Exit(1)

    # Initialize only Redis (for Firecrawl reader state)
    try:
        redis_client = RedisClient(config.redis_url)
    except Exception as e:
        console.print(f"[red]Error initializing Redis:[/red] {e}")
        raise typer.Exit(1)

    language_filter_component = build_language_filter_from_config(
        getattr(getattr(config, "ingestion", None), "language_filter", None),
        log_filtered_override=False,
    )

    # Create Firecrawl reader
    reader_config = {"limit": limit}
    try:
        reader = FirecrawlReader(
            source_name="firecrawl_map",
            config=reader_config,
            redis_client=redis_client,
        )
    except Exception as e:
        console.print(f"[red]Error initializing Firecrawl reader:[/red] {e}")
        raise typer.Exit(1)

    # Run map operation
    console.print(f"[cyan]Discovering URLs from:[/cyan] {url}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Mapping URLs...", total=None)

        try:
            documents = reader.load_data(url=url, mode="map", limit=limit)
            progress.update(task, description="[green]✓ URL discovery complete")

            if not documents:
                console.print("[yellow]No URLs discovered")
                return

            original_count = len(documents)
            filtered_count = 0

            if language_filter_component:
                filtered_documents = filter_documents_by_language(
                    documents, language_filter_component
                )
                filtered_count = original_count - len(filtered_documents)
                documents = filtered_documents

                if filtered_count:
                    logger.info(
                        "Language filter removed %s Firecrawl map documents",
                        filtered_count,
                        extra={
                            "mode": "map",
                            "filtered": filtered_count,
                            "original_count": original_count,
                        },
                    )

            if not documents:
                console.print(
                    "[yellow]All discovered URLs were filtered out by language settings"
                )
                return

            if filtered_count:
                console.print(
                    f"[yellow]Language filter kept {len(documents)}/{original_count} URLs"
                )

            # Extract URLs from documents
            urls: list[str] = []
            for doc in documents:
                # Map mode returns documents with URL metadata
                doc_url = doc.metadata.source_url
                if doc_url and doc_url not in urls:
                    urls.append(doc_url)

                # Also check content for URL list (Firecrawl may return URLs in content)
                if doc.content:
                    for line in doc.content.split("\n"):
                        line = line.strip()
                        if line.startswith("http"):
                            if line not in urls:
                                urls.append(line)

            # Display results
            console.print(f"\n[green]Discovered {len(urls)} URLs:[/green]\n")
            for url_item in urls:
                console.print(f"  {url_item}")

        except Exception as e:
            progress.update(task, description="[red]✗ Map operation failed")
            console.print(f"[red]Error during map:[/red] {e}")
            logger.exception("Firecrawl map failed")
            raise typer.Exit(1)


def _run_firecrawl_ingestion(
    url: str,
    mode: str,
    limit: int | None = None,
    max_depth: int | None = None,
    formats: list[str] | None = None,
    schema: str | None = None,
    prompt: str | None = None,
    include_paths: list[str] | None = None,
    exclude_paths: list[str] | None = None,
    location_country: str | None = None,
    location_languages: list[str] | None = None,
    filter_non_english_metadata: bool = True,
) -> int:
    """Shared ingestion logic for all Firecrawl commands.

    Args:
        url: URL to process
        mode: Firecrawl mode (scrape, crawl, map, extract)
        limit: Maximum number of pages/URLs
        max_depth: Maximum crawl depth (crawl mode only)
        formats: Output formats for scrape/crawl
        schema: JSON schema for extract mode
        prompt: Extraction prompt for extract mode
        include_paths: URL path patterns to include (regex)
        exclude_paths: URL path patterns to exclude (regex)
        location_country: ISO country code for regional targeting
        location_languages: Language codes for targeting
        filter_non_english_metadata: Filter by Firecrawl's detected language

    Returns:
        Number of documents ingested

    Raises:
        typer.Exit: If ingestion fails
    """
    # Validate URL
    _validate_url(url)

    # Load global config
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        raise typer.Exit(1)

    # Initialize storage clients
    try:
        redis_client = RedisClient(config.redis_url)
        qdrant_client = QdrantClient(
            url=config.qdrant_url,
            collection_name=config.vector_store.collection_name,
            vector_dimension=config.vector_store.vector_dimension,
            distance_metric=config.vector_store.distance_metric,
        )
        neo4j_client = Neo4jClient(config=config)
        embed_model = TEIEmbedding(base_url=config.tei_embedding_url)
    except Exception as e:
        console.print(f"[red]Error initializing clients:[/red] {e}")
        raise typer.Exit(1)

    # Build location config if provided
    location_config = None
    if location_country:
        location_config = {
            "country": location_country,
            "languages": location_languages or [f"en-{location_country.upper()}"],
        }

    # Create Firecrawl reader config dict
    reader_config = {
        "url": url,
        "mode": mode,
        "limit": limit,
        "max_depth": max_depth,
        "formats": formats or ["markdown", "html"],
        "schema": schema,
        "prompt": prompt,
        "include_paths": include_paths or [],
        "exclude_paths": exclude_paths or [],
        "location": location_config,
        "filter_non_english_metadata": filter_non_english_metadata,
    }

    # Initialize reader
    try:
        reader = FirecrawlReader(
            source_name=f"firecrawl_{mode}",
            config=reader_config,
            redis_client=redis_client,
        )
    except Exception as e:
        console.print(f"[red]Error initializing Firecrawl reader:[/red] {e}")
        raise typer.Exit(1)

    # Initialize pipeline
    try:
        pipeline = IngestionPipeline(
            config=config,
            redis_client=redis_client,
            qdrant_client=qdrant_client,
            neo4j_client=neo4j_client,
            embed_model=embed_model,
        )
    except Exception as e:
        console.print(f"[red]Error initializing pipeline:[/red] {e}")
        raise typer.Exit(1)

    language_filter_component = None
    if filter_non_english_metadata:
        language_filter_component = build_language_filter_from_config(
            getattr(getattr(config, "ingestion", None), "language_filter", None),
            log_filtered_override=False,
        )
    else:
        logger.info(
            "Language filtering disabled via CLI flag for Firecrawl %s",
            mode,
            extra={"mode": mode},
        )

    # Run ingestion with progress
    console.print(f"[cyan]Starting Firecrawl {mode} ingestion for:[/cyan] {url}")

    doc_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,  # Auto-cleanup on exit to prevent terminal corruption
    ) as progress:
        task = progress.add_task(f"Processing with {mode} mode...", total=None)

        try:
            # Load documents from Firecrawl
            documents = reader.load_data(
                url=url,
                mode=mode,
                limit=limit,
                max_depth=max_depth,
                formats=formats,
            )
            original_count = len(documents)
            filtered_count = 0

            if language_filter_component:
                filtered_documents = filter_documents_by_language(
                    documents, language_filter_component
                )
                filtered_count = original_count - len(filtered_documents)
                documents = filtered_documents

                if filtered_count:
                    logger.info(
                        "Language filter removed %s Firecrawl documents",
                        filtered_count,
                        extra={
                            "mode": mode,
                            "filtered": filtered_count,
                            "original_count": original_count,
                        },
                    )

            doc_count = len(documents)

            if doc_count == 0:
                description = (
                    "[yellow]All documents filtered by language"
                    if filtered_count
                    else "[yellow]No documents found"
                )
                progress.update(task, description=description)
                console.print(
                    "[yellow]Warning: No documents available after language filtering"
                    if filtered_count
                    else "[yellow]Warning: No documents were retrieved"
                )
                return 0

            if filtered_count:
                progress.update(
                    task,
                    description=(
                        f"Language filter kept {doc_count}/{original_count} documents; ingesting..."
                    ),
                )
            else:
                progress.update(
                    task,
                    description=f"Loaded {doc_count} documents, ingesting...",
                )

            # Ingest into pipeline
            summary = pipeline.ingest_documents(
                source=f"firecrawl_{mode}", documents=documents
            )

            progress.update(
                task,
                description=(
                    f"[green]✓ Processed {summary.processed}/{doc_count} documents "
                    f"(deduplicated: {summary.deduplicated}, failed: {summary.failed})"
                ),
            )

        except Exception as e:
            progress.update(task, description="[red]✗ Ingestion failed")
            console.print(f"[red]Error during ingestion:[/red] {e}")
            logger.exception("Firecrawl ingestion failed")
            raise typer.Exit(1)

    console.print(f"[green]Successfully ingested {doc_count} documents from {url}")
    return doc_count


def scrape(
    url: Annotated[str, typer.Argument(help="URL to scrape")],
    formats: Annotated[
        list[str] | None,
        typer.Option(help="Output formats (markdown, html, links, screenshot)")
    ] = None,
    include_paths: Annotated[
        list[str] | None,
        typer.Option("--include-paths", help="URL patterns to include (regex)")
    ] = None,
    exclude_paths: Annotated[
        list[str] | None,
        typer.Option("--exclude-paths", help="URL patterns to exclude (regex)")
    ] = None,
    location_country: Annotated[
        str | None,
        typer.Option("--location-country", help="ISO country code (e.g., US, GB)")
    ] = None,
    location_languages: Annotated[
        list[str] | None,
        typer.Option("--location-languages", help="Language codes (e.g., en-US)")
    ] = None,
    only_english: Annotated[
        bool,
        typer.Option("--only-english/--all-languages", help="Filter non-English content")
    ] = True,
) -> None:
    """Scrape a single URL using Firecrawl with language filtering.

    This command fetches and processes a single web page, extracting content
    in the specified formats. Language filtering is enabled by default.

    Examples:
        llamacrawl scrape https://example.com
        llamacrawl scrape https://docs.python.org/3/ --formats markdown --formats links
        llamacrawl scrape https://example.com --only-english
        llamacrawl scrape https://multilingual.com --all-languages
    """
    _run_firecrawl_ingestion(
        url=url,
        mode="scrape",
        formats=formats,
        include_paths=include_paths,
        exclude_paths=exclude_paths,
        location_country=location_country,
        location_languages=location_languages,
        filter_non_english_metadata=only_english,
    )


def crawl(
    url: Annotated[str, typer.Argument(help="Base URL to crawl")],
    limit: Annotated[
        int,
        typer.Option(help="Maximum number of pages to crawl")
    ] = 1000,
    max_depth: Annotated[
        int,
        typer.Option(help="Maximum crawl depth from base URL")
    ] = 3,
    formats: Annotated[
        list[str] | None,
        typer.Option(help="Output formats (markdown, html, links, screenshot)")
    ] = None,
    include_paths: Annotated[
        list[str] | None,
        typer.Option("--include-paths", help="URL patterns to include (regex)")
    ] = None,
    exclude_paths: Annotated[
        list[str] | None,
        typer.Option("--exclude-paths", help="URL patterns to exclude (regex)")
    ] = None,
    location_country: Annotated[
        str | None,
        typer.Option("--location-country", help="ISO country code (e.g., US, GB)")
    ] = None,
    location_languages: Annotated[
        list[str] | None,
        typer.Option("--location-languages", help="Language codes (e.g., en-US)")
    ] = None,
    only_english: Annotated[
        bool,
        typer.Option("--only-english/--all-languages", help="Filter non-English content")
    ] = True,
) -> None:
    """Crawl an entire website with language filtering.

    This command recursively crawls a website, following links up to the specified
    depth and page limit. Language filtering is enabled by default to save resources.

    Examples:
        llamacrawl crawl https://example.com
        llamacrawl crawl https://docs.python.org/ --limit 50 --max-depth 2
        llamacrawl crawl https://example.com --include-paths "^/en/" --exclude-paths "^/fr/"
        llamacrawl crawl https://example.com --location-country US --location-languages en-US
        llamacrawl crawl https://multilingual.com --all-languages
    """
    _run_firecrawl_ingestion(
        url=url,
        mode="crawl",
        limit=limit,
        max_depth=max_depth,
        formats=formats,
        include_paths=include_paths,
        exclude_paths=exclude_paths,
        location_country=location_country,
        location_languages=location_languages,
        filter_non_english_metadata=only_english,
    )


def map(
    url: Annotated[str, typer.Argument(help="Base URL to map")],
    limit: Annotated[
        int,
        typer.Option(help="Maximum number of URLs to discover")
    ] = 1000,
) -> None:
    """Discover and map URLs from a website using sitemap and crawling.

    This command discovers URLs from a website without fetching full content.
    It's useful for understanding site structure or preparing for selective crawling.

    Examples:
        llamacrawl map https://example.com
        llamacrawl map https://docs.python.org/ --limit 500
    """
    _run_firecrawl_map(url=url, limit=limit)


def extract(
    url: Annotated[str, typer.Argument(help="URL to extract data from")],
    prompt: Annotated[
        str | None,
        typer.Option(help="Extraction prompt describing what to extract")
    ] = None,
    schema: Annotated[
        str | None,
        typer.Option(help="JSON schema file path for structured extraction")
    ] = None,
    include_paths: Annotated[
        list[str] | None,
        typer.Option("--include-paths", help="URL patterns to include (regex)")
    ] = None,
    exclude_paths: Annotated[
        list[str] | None,
        typer.Option("--exclude-paths", help="URL patterns to exclude (regex)")
    ] = None,
    location_country: Annotated[
        str | None,
        typer.Option("--location-country", help="ISO country code (e.g., US, GB)")
    ] = None,
    location_languages: Annotated[
        list[str] | None,
        typer.Option("--location-languages", help="Language codes (e.g., en-US)")
    ] = None,
    only_english: Annotated[
        bool,
        typer.Option("--only-english/--all-languages", help="Filter non-English content")
    ] = True,
) -> None:
    """Extract structured data from a URL using AI with language filtering.

    This command uses AI to extract structured information from a web page based
    on either a natural language prompt or a JSON schema definition.
    Language filtering is enabled by default.

    You must provide either --prompt or --schema (but not both).

    Examples:
        llamacrawl extract https://example.com/product --prompt "Extract product name, price, and description"
        llamacrawl extract https://news.example.com/article --schema schema.json
        llamacrawl extract https://example.com --prompt "Extract data" --only-english
    """
    if not prompt and not schema:
        console.print("[red]Error: Must provide either --prompt or --schema")
        raise typer.Exit(1)

    if prompt and schema:
        console.print("[red]Error: Cannot provide both --prompt and --schema")
        raise typer.Exit(1)

    # Load schema if provided
    schema_content = None
    if schema:
        schema_path = Path(schema)
        if not schema_path.exists():
            console.print(f"[red]Error: Schema file not found:[/red] {schema}")
            raise typer.Exit(1)
        try:
            schema_content = schema_path.read_text()
        except Exception as e:
            console.print(f"[red]Error reading schema file:[/red] {e}")
            raise typer.Exit(1)

    _run_firecrawl_ingestion(
        url=url,
        mode="extract",
        prompt=prompt,
        schema=schema_content,
        include_paths=include_paths,
        exclude_paths=exclude_paths,
        location_country=location_country,
        location_languages=location_languages,
        filter_non_english_metadata=only_english,
    )
