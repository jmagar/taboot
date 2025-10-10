"""Firecrawl map command."""

from __future__ import annotations

from typing import Annotated

import typer

from llamacrawl.utils.logging import get_logger

from ..context import CLIState
from .common import run_firecrawl_map

logger = get_logger(__name__)


def map(
    ctx: typer.Context,
    url: Annotated[str, typer.Argument(help="Base URL to map")],
    limit: Annotated[
        int,
        typer.Option(help="Maximum number of URLs to discover"),
    ] = 1000,
) -> None:
    """Discover URLs from a website without ingesting content."""
    state = ctx.ensure_object(CLIState)
    logger.info("Firecrawl map command invoked", extra={"url": url, "limit": limit})
    run_firecrawl_map(state, url=url, limit=limit)
