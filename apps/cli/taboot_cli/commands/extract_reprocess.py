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
        if days <= 0:
            console.print(f"[red]✗ Period must be > 0 days: {since}[/red]")
            raise typer.Exit(code=1)

        since_date = datetime.now(UTC) - timedelta(days=days)

        console.print(f"[yellow]Reprocessing documents since {since_date.isoformat()}...[/yellow]")

        # Import and use ReprocessUseCase
        from packages.common.db_schema import get_postgres_client
        from packages.clients.postgres_document_store import PostgresDocumentStore
        from packages.core.use_cases.reprocess import ReprocessUseCase

        conn = get_postgres_client()
        try:
            document_store = PostgresDocumentStore(conn)
            use_case = ReprocessUseCase(document_store=document_store)
            result = use_case.execute(since_date=since_date)
            count = result["documents_queued"]
            console.print(f"[green]✓ Queued {count} documents for reprocessing[/green]")
        finally:
            conn.close()

    except ValueError as err:
        console.print(f"[red]✗ Invalid period: {err}[/red]")
        raise typer.Exit(code=1) from err
    except Exception as err:
        logger.exception("Reprocessing failed")
        console.print(f"[red]✗ Reprocessing failed: {err}[/red]")
        raise typer.Exit(code=1) from err
