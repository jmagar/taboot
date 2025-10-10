"""Async shared helpers for Firecrawl commands."""

from __future__ import annotations

from typing import Any
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
from llamacrawl.readers.async_firecrawl import AsyncFirecrawlReader
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


async def run_async_firecrawl_ingestion(
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
    """Async shared ingestion logic for scrape/crawl/extract commands."""
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

    try:
        reader = AsyncFirecrawlReader(
            source_name=f"firecrawl_{mode}",
            config=reader_config,
            redis_client=redis_client,
        )
    except Exception as error:
        console.print(f"[red]Error initializing Async Firecrawl reader:[/red] {error}")
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
            "Language filtering disabled via CLI flag for Async Firecrawl %s",
            mode,
            extra={"mode": mode},
        )

    console.print(f"[cyan]Starting Async Firecrawl {mode} ingestion for:[/cyan] {url}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task(f"Processing with async {mode} mode...", total=None)
        try:
            # Use async load_data
            documents = await reader.aload_data(
                url=url,
                mode=mode,
                limit=limit,
                max_depth=max_depth,
                formats=formats,
            )
        except Exception as error:
            progress.update(task_id, description="[red]✗ Async ingestion failed")
            console.print(f"[red]Error during async ingestion:[/red] {error}")
            logger.exception("Async Firecrawl ingestion failed")
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
                    "Language filter removed %s Async Firecrawl documents",
                    filtered_count,
                    extra={
                        "mode": mode,
                        "filtered": filtered_count,
                        "original_count": original_count,
                    },
                )

        if not documents:
            description = (
                "[yellow]All documents filtered by language"
                if filtered_count
                else "[yellow]No documents found"
            )
            progress.update(task_id, description=description)
            console.print(
                "[yellow]Warning: No documents available after language filtering[/yellow]"
                if filtered_count
                else "[yellow]Warning: No documents were retrieved[/yellow]"
            )
            return 0

        if filtered_count:
            progress.update(
                task_id,
                description=(
                    f"Language filter kept {len(documents)}/{original_count} documents; ingesting..."
                ),
            )
        else:
            progress.update(
                task_id,
                description=f"Loaded {len(documents)} documents asynchronously, ingesting...",
            )

        try:
            summary = pipeline.ingest_documents(
                source=f"async_firecrawl_{mode}",
                documents=documents,
            )
        finally:
            try:
                neo4j_client.close()
            except Exception:  # pragma: no cover - defensive
                logger.debug("Failed to close Neo4j client after Async Firecrawl ingestion")

        progress.update(
            task_id,
            description=(
                f"[green]✓ Processed {summary.processed}/{len(documents)} documents "
                f"(deduplicated: {summary.deduplicated}, failed: {summary.failed})"
            ),
        )

    console.print(f"[green]Successfully ingested {len(documents)} documents from {url} using async mode")
    return len(documents)