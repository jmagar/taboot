"""Firecrawl subcommands."""

from __future__ import annotations

import typer

from . import async_crawl as async_crawl_cmd
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
    app.command("async-crawl")(async_crawl_cmd.async_crawl)
    app.command()(map_cmd.map)
    app.command()(extract_cmd.extract)
