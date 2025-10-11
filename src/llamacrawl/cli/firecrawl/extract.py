"""Firecrawl extract command."""

from __future__ import annotations

from typing import Annotated

import typer

from llamacrawl.utils.logging import get_logger

from ..context import CLIState
from .common import read_schema_file, run_firecrawl_ingestion

logger = get_logger(__name__)


def extract(
    ctx: typer.Context,
    url: Annotated[str, typer.Argument(help="URL to extract data from")],
    prompt: Annotated[
        str | None,
        typer.Option(help="Extraction prompt describing what to extract"),
    ] = None,
    schema: Annotated[
        str | None,
        typer.Option(help="JSON schema file path for structured extraction"),
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
    """Extract structured data from a URL using Firecrawl."""
    state = ctx.ensure_object(CLIState)

    if not prompt and not schema:
        raise typer.BadParameter("Must provide either --prompt or --schema")
    if prompt and schema:
        raise typer.BadParameter("Cannot provide both --prompt and --schema")

    schema_content = read_schema_file(schema) if schema else None

    logger.info(
        "Firecrawl extract command invoked",
        extra={
            "url": url,
            "schema": schema,
            "only_english": only_english,
        },
    )

    run_firecrawl_ingestion(
        state,
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
