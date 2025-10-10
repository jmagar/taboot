"""Firecrawl scrape command."""

from __future__ import annotations

from typing import Annotated

import typer

from llamacrawl.utils.logging import get_logger

from ..context import CLIState
from .common import run_firecrawl_ingestion

logger = get_logger(__name__)


def scrape(
    ctx: typer.Context,
    url: Annotated[str, typer.Argument(help="URL to scrape")],
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
    """Scrape a single URL using Firecrawl."""
    state = ctx.ensure_object(CLIState)
    logger.info(
        "Firecrawl scrape command invoked",
        extra={
            "url": url,
            "formats": formats,
            "only_english": only_english,
        },
    )
    run_firecrawl_ingestion(
        state,
        url=url,
        mode="scrape",
        formats=formats,
        include_paths=include_paths,
        exclude_paths=exclude_paths,
        location_country=location_country,
        location_languages=location_languages,
        filter_non_english_metadata=only_english,
    )
