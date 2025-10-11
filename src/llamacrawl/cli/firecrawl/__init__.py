"""Firecrawl subcommands."""

from __future__ import annotations

import typer

from . import crawl as crawl_cmd
from . import extract as extract_cmd
from . import map as map_cmd
from . import scrape as scrape_cmd

firecrawl_app = typer.Typer(
    name="firecrawl",
    help="Firecrawl-specific operations",
    add_completion=False,
    no_args_is_help=True,
)


def register_firecrawl_commands(app: typer.Typer) -> None:
    """Register Firecrawl commands with the root CLI."""
    app.command()(scrape_cmd.scrape)
    app.command()(crawl_cmd.crawl)
    app.command(name="map")(map_cmd.map_urls)
    app.command()(extract_cmd.extract)
