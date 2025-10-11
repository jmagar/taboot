"""Version command."""

from __future__ import annotations

import typer
from rich.console import Console

from ..context import CLIState

__version__ = "0.1.0"


def version(
    ctx: typer.Context,
) -> None:
    """Display version information."""
    state = ctx.obj if isinstance(ctx.obj, CLIState) else None
    console: Console = state.console if state else Console()
    console.print(f"[bold]LlamaCrawl[/bold] version [cyan]{__version__}[/cyan]")
