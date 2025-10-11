"""Firecrawl crawl command."""

from __future__ import annotations

from typing import Annotated

import typer

from llamacrawl.utils.logging import get_logger

from ..context import CLIState
from .common import run_firecrawl_ingestion

logger = get_logger(__name__)


def crawl(
    ctx: typer.Context,
    url: Annotated[str, typer.Argument(help="Base URL to crawl")],
    limit: Annotated[
        int,
        typer.Option(help="Maximum number of pages to crawl"),
    ] = 1000,
    max_depth: Annotated[
        int,
        typer.Option(help="Maximum crawl depth from base URL"),
    ] = 3,
    formats: Annotated[
        list[str] | None,
        typer.Option(help="Output formats (markdown, html, links, screenshot)"),
    ] = None,
    include_paths: Annotated[
        list[str] | None,
        typer.Option("--include-paths", help="URL patterns to include (regex)"),
    ] = None,
    exclude_paths: Annotated[
        list[str] | None,
        typer.Option("--exclude-paths", help="URL patterns to exclude (regex)"),
    ] = None,
    location_country: Annotated[
        str | None,
        typer.Option("--location-country", help="ISO country code (e.g., US, GB)"),
    ] = None,
    location_languages: Annotated[
        list[str] | None,
        typer.Option("--location-languages", help="Language codes (e.g., en-US)"),
    ] = None,
    only_english: Annotated[
        bool,
        typer.Option("--only-english/--all-languages", help="Filter non-English content"),
    ] = True,
) -> None:
    """Crawl an entire website using Firecrawl."""
    state = ctx.ensure_object(CLIState)
    logger.info(
        "Firecrawl crawl command invoked",
        extra={
            "url": url,
            "limit": limit,
            "max_depth": max_depth,
            "only_english": only_english,
        },
    )

    run_firecrawl_ingestion(
        state,
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
