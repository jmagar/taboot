"""Shared helpers for Firecrawl commands."""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

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

from ..context import CLIState
from ..dependencies import build_neo4j, build_qdrant, build_redis

logger = get_logger(__name__)


def validate_url(url: str) -> None:
    """Validate that the provided URL has an http(s) scheme and hostname."""
    try:
        result = urlparse(url)
    except ValueError as error:
        raise typer.BadParameter(f"Invalid URL: {error}") from error

    if not result.scheme or not result.netloc:
        raise typer.BadParameter(f"Invalid URL format: {url}")
    if result.scheme not in {"http", "https"}:
        raise typer.BadParameter(f"URL must use http or https: {url}")


def run_firecrawl_map(state: CLIState, *, url: str, limit: int) -> None:
    """Perform URL discovery without ingestion."""
    validate_url(url)

    config = state.config
    console: Console = state.console

    try:
        redis_client = build_redis(config)
    except Exception as error:
        console.print(f"[red]Error initializing Redis:[/red] {error}")
        raise typer.Exit(1) from error

    language_filter_component = build_language_filter_from_config(
        getattr(getattr(config, "ingestion", None), "language_filter", None),
        log_filtered_override=False,
    )

    reader_config = {"limit": limit}
    try:
        reader = FirecrawlReader(
            source_name="firecrawl_map",
            config=reader_config,
            redis_client=redis_client,
        )
    except Exception as error:
        console.print(f"[red]Error initializing Firecrawl reader:[/red] {error}")
        raise typer.Exit(1) from error

    console.print(f"[cyan]Discovering URLs from:[/cyan] {url}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task("Mapping URLs...", total=None)
        try:
            documents = asyncio.run(reader.aload_data(url=url, mode="map", limit=limit))
        except Exception as error:
            progress.update(task_id, description="[red]✗ Map operation failed")
            console.print(f"[red]Error during map:[/red] {error}")
            logger.exception("Firecrawl map failed")
            raise typer.Exit(1) from error

        progress.update(task_id, description="[green]✓ URL discovery complete")

    if not documents:
        console.print("[yellow]No URLs discovered[/yellow]")
        return

    if language_filter_component:
        filtered_documents = filter_documents_by_language(documents, language_filter_component)
        removed = len(documents) - len(filtered_documents)
        if removed:
            logger.info(
                "Language filter removed %s Firecrawl map documents",
                removed,
                extra={"mode": "map", "filtered": removed, "original_count": len(documents)},
            )
            console.print(
                f"[yellow]Language filter kept {len(filtered_documents)}/{len(documents)} URLs"
            )
        documents = filtered_documents

    if not documents:
        console.print("[yellow]All discovered URLs were filtered out by language settings[/yellow]")
        return

    urls: list[str] = []
    for doc in documents:
        doc_url = getattr(doc.metadata, "source_url", None)
        if doc_url and doc_url not in urls:
            urls.append(doc_url)
        if doc.content:
            for line in doc.content.splitlines():
                text = line.strip()
                if text.startswith("http") and text not in urls:
                    urls.append(text)

    console.print(f"\n[green]Discovered {len(urls)} URLs:[/green]\n")
    for discovered in urls:
        console.print(f"  {discovered}")


def run_firecrawl_ingestion(
    state: CLIState,
    *,
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
    """Shared ingestion logic for scrape/crawl/extract commands."""
    validate_url(url)

    config = state.config
    console: Console = state.console

    redis_client: RedisClient | None = None
    qdrant_client: QdrantClient | None = None
    neo4j_client: Neo4jClient | None = None

    try:
        redis_client = build_redis(config)
        qdrant_client = build_qdrant(config)
        neo4j_client = build_neo4j(config)
        embed_model = TEIEmbedding(base_url=config.tei_embedding_url)
    except Exception as error:
        console.print(f"[red]Error initializing clients:[/red] {error}")
        raise typer.Exit(1) from error

    location_config = None
    if location_country:
        location_config = {
            "country": location_country,
            "languages": location_languages or [f"en-{location_country.upper()}"],
        }

    # Merge CLI-provided paths with config file paths (CLI takes precedence)
    config_firecrawl = getattr(getattr(config, "sources", None), "firecrawl", None)
    config_include_paths = getattr(config_firecrawl, "include_paths", []) or []
    config_exclude_paths = getattr(config_firecrawl, "exclude_paths", []) or []

    reader_config = {
        "url": url,
        "mode": mode,
        "limit": limit,
        "max_depth": max_depth,
        "formats": formats or ["markdown", "html"],
        "schema": schema,
        "prompt": prompt,
        "include_paths": include_paths if include_paths is not None else config_include_paths,
        "exclude_paths": exclude_paths if exclude_paths is not None else config_exclude_paths,
        "location": location_config,
        "filter_non_english_metadata": filter_non_english_metadata,
    }

    try:
        reader = FirecrawlReader(
            source_name=f"firecrawl_{mode}",
            config=reader_config,
            redis_client=redis_client,
        )
    except Exception as error:
        console.print(f"[red]Error initializing Firecrawl reader:[/red] {error}")
        raise typer.Exit(1) from error

    try:
        pipeline = IngestionPipeline(
            config=config,
            redis_client=redis_client,
            qdrant_client=qdrant_client,
            neo4j_client=neo4j_client,
            embed_model=embed_model,
        )
    except Exception as error:
        console.print(f"[red]Error initializing pipeline:[/red] {error}")
        raise typer.Exit(1) from error

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

    console.print(f"[cyan]Starting Firecrawl {mode} ingestion for:[/cyan] {url}")

    # Temporarily disable progress bar for debugging
    console.print(f"[dim]Processing with {mode} mode...[/dim]")
    try:
        documents = asyncio.run(
            reader.aload_data(
                url=url,
                mode=mode,
                limit=limit,
                max_depth=max_depth,
                formats=formats,
                schema=schema,
                prompt=prompt,
            )
        )
    except Exception as error:
        console.print(f"[red]✗ Ingestion failed: {error}[/red]")
        logger.exception("Firecrawl ingestion failed")
        raise typer.Exit(1) from error

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

    if not documents:
        console.print(
            "[yellow]Warning: No documents available after language filtering[/yellow]"
            if filtered_count
            else "[yellow]Warning: No documents were retrieved[/yellow]"
        )
        return 0

    if filtered_count:
        console.print(
            f"[dim]Language filter kept {len(documents)}/{original_count} "
            f"documents; ingesting...[/dim]"
        )
    else:
        console.print(f"[dim]Loaded {len(documents)} documents, ingesting...[/dim]")

    # Print scraped content for scrape mode
    if mode == "scrape":
        console.print("\n[cyan]═══ Scraped Content ═══[/cyan]\n")
        for i, doc in enumerate(documents, 1):
            if len(documents) > 1:
                console.print(f"[bold]Document {i}:[/bold]")
            console.print(doc.content)
            if i < len(documents):
                console.print("\n[dim]───────────────────────[/dim]\n")
        console.print("\n[cyan]═══════════════════════[/cyan]\n")

    try:
        summary = pipeline.ingest_documents(
            source=f"firecrawl_{mode}",
            documents=documents,
        )
    finally:
        try:
            neo4j_client.close()
        except Exception:  # pragma: no cover - defensive
            logger.debug("Failed to close Neo4j client after Firecrawl ingestion")

    # Show final summary
    console.print(
        f"[green]✓ Processed {summary.processed}/{len(documents)} documents "
        f"(deduplicated: {summary.deduplicated}, failed: {summary.failed})[/green]"
    )

    console.print(f"[green]Successfully ingested {len(documents)} documents from {url}[/green]")
    return len(documents)


def read_schema_file(path: str) -> str:
    schema_path = Path(path)
    if not schema_path.exists():
        raise typer.BadParameter(f"Schema file not found: {path}")
    try:
        return schema_path.read_text(encoding="utf-8")
    except Exception as error:
        raise typer.BadParameter(f"Error reading schema file: {error}") from error
