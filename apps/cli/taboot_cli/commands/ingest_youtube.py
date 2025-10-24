"""Ingest YouTube command for Taboot CLI."""

import logging
from typing import Annotated

import typer
from rich.console import Console

from packages.common.factories import make_ingest_youtube_use_case

console = Console()
logger = logging.getLogger(__name__)


def ingest_youtube_command(
    urls: Annotated[list[str], typer.Argument(..., help="YouTube video URLs")],
) -> None:
    """Ingest YouTube video transcripts into the knowledge graph.

from __future__ import annotations

    Example:
        uv run apps/cli ingest youtube https://www.youtube.com/watch?v=...
    """
    try:
        console.print(f"[yellow]Starting YouTube ingestion: {len(urls)} video(s)[/yellow]")

        use_case, cleanup = make_ingest_youtube_use_case()
        try:
            console.print("[yellow]Loading transcripts...[/yellow]")
            result = use_case.execute(urls=urls)

            videos_processed = result["videos_processed"]
            chunks_created = result["chunks_created"]

            console.print(f"[green]✓ Loaded {videos_processed} transcripts[/green]")
            console.print(f"[green]✓ Created {chunks_created} chunks[/green]")
            console.print("[green]✓ YouTube ingestion complete![/green]")
        finally:
            cleanup()

    except Exception as e:
        logger.exception("YouTube ingestion failed")
        console.print(f"[red]✗ YouTube ingestion failed: {e}[/red]")
        raise typer.Exit(code=1) from e
