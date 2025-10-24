"""Extract reprocess command for Taboot CLI.

Implements document reprocessing workflow.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

import typer
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


def extract_reprocess_command(
    since: Annotated[
        str,
        typer.Option("--since", help="Reprocess documents from this period (e.g., '7d', '30d')"),
    ],
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

    def _parse_since(spec: str) -> datetime:
        """Parse period specification into datetime.

        Args:
            spec: Period specification (e.g., '7d', '30d').

        Returns:
            Datetime representing the start of the period.

        Raises:
            typer.BadParameter: If period format is invalid.
        """
        if not spec.endswith("d"):
            raise typer.BadParameter("Expected format like '7d' or '30d'.")
        try:
            days = int(spec[:-1])
        except ValueError as err:
            raise typer.BadParameter(f"Invalid number in period: {spec}") from err
        if days <= 0:
            raise typer.BadParameter("Period must be > 0.")
        return datetime.now(UTC) - timedelta(days=days)

    try:
        since_date = _parse_since(since)
    except typer.BadParameter as err:
        console.print(f"[red]✗ Invalid period: {err}[/red]")
        raise typer.Exit(code=1) from err

    try:
        console.print(f"[yellow]Reprocessing documents since {since_date.isoformat()}...[/yellow]")

        from packages.common.factories import make_reprocess_use_case

        use_case, cleanup = make_reprocess_use_case()
        try:
            result = use_case.execute(since_date=since_date)
            count = result["documents_queued"]
            console.print(f"[green]✓ Queued {count} documents for reprocessing[/green]")
        finally:
            cleanup()

    except Exception as err:
        logger.exception("Reprocessing failed")
        console.print(f"[red]✗ Reprocessing failed: {err}[/red]")
        raise typer.Exit(code=1) from err
