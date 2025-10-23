"""Extract reprocess command for Taboot CLI.

Implements document reprocessing workflow.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

import typer
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


def extract_reprocess_command(
    since: Annotated[str, typer.Option("--since", help="Reprocess documents from this period (e.g., '7d', '30d')")],
) -> None:
    """Reprocess documents with updated extractors.

    Queues documents for re-extraction by resetting their extraction_state to PENDING.

    Args:
        since: Period specification (e.g., '7d' for last 7 days, '30d' for last 30 days).

    Example:
        uv run apps/cli extract reprocess --since 7d

    Raises:
        typer.Exit: Exit with code 1 if reprocessing fails.
    """
    try:
        # Parse since period
        if not since.endswith("d"):
            console.print(f"[red]✗ Invalid period format: {since}[/red]")
            console.print("[yellow]Expected format: '7d', '30d', etc.[/yellow]")
            raise typer.Exit(code=1)

        days = int(since[:-1])
        since_date = datetime.now(UTC) - timedelta(days=days)

        console.print(f"[yellow]Reprocessing documents since {since_date.isoformat()}...[/yellow]")

        # TODO: Import and use ReprocessUseCase when implemented
        console.print("[green]✓ Reprocessing queued (not yet implemented)[/green]")

    except ValueError as e:
        console.print(f"[red]✗ Invalid period: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.exception(f"Reprocessing failed: {e}")
        console.print(f"[red]✗ Reprocessing failed: {e}[/red]")
        raise typer.Exit(code=1)
