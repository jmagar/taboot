"""Schema management commands for Taboot CLI.

Provides commands for viewing and managing PostgreSQL schema versions:
- schema version: Show current database schema version
- schema history: Show schema version history
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from packages.common.db_schema import (
    CURRENT_SCHEMA_VERSION,
    get_schema_version_details,
    get_schema_version_history,
)
from packages.common.logging import get_logger

console = Console()
logger = get_logger(__name__)


def _style_status(status: str) -> str:
    """Style status text with color coding.

    Args:
        status: Status string (e.g., 'success', 'failed')

    Returns:
        Rich-formatted status string with appropriate color for display.
    """
    if status == "success":
        return f"[green]{status}[/green]"
    elif status == "failed":
        return f"[red]{status}[/red]"
    else:
        return f"[yellow]{status}[/yellow]"


def version_command() -> None:
    """Show current database schema version.

    Displays the currently applied schema version from the database along with:
    - Applied timestamp
    - Applied by (database user)
    - Execution time
    - Status (success/failed)
    - Checksum (first 16 chars)

    Example:
        $ taboot schema version
        Current schema version: 2.0.0
        Expected version: 2.0.0
        Applied at: 2025-10-25 14:30:45
        Applied by: postgres
        Execution time: 1234ms
        Status: success
        Checksum: a1b2c3d4e5f6g7h8...
    """
    try:
        # Get schema version details from service
        details = get_schema_version_details()

        if not details:
            console.print("[yellow]No schema version recorded in database[/yellow]")
            console.print(f"Expected version: [bold]{CURRENT_SCHEMA_VERSION}[/bold]")
            console.print("\nRun [bold]taboot init[/bold] to initialize schema")
            return

        # Extract details for display
        status_text = _style_status(details.status)
        if details.status == "success":
            status_icon = "[green]✓[/green]"
        elif details.status == "failed":
            status_icon = "[red]✗[/red]"
        else:
            status_icon = "[yellow]?[/yellow]"

        # Version match indicator
        if details.version == CURRENT_SCHEMA_VERSION:
            version_match = "[green](matches expected)[/green]"
        else:
            version_match = f"[yellow](expected: {CURRENT_SCHEMA_VERSION})[/yellow]"

        # Display version info
        version_line = f"{status_icon} Current schema version: "
        version_line += f"[bold]{details.version}[/bold] {version_match}"
        console.print(f"\n{version_line}")
        console.print(f"  Applied at: {details.applied_at}")
        console.print(f"  Applied by: {details.applied_by}")
        if details.execution_time_ms is not None:
            console.print(f"  Execution time: {details.execution_time_ms}ms")
        console.print(f"  Status: {status_text}")
        checksum_display = (
            details.checksum[:16] + "..."
            if details.checksum and len(details.checksum) >= 16
            else (details.checksum or "N/A")
        )
        console.print(f"  Checksum: {checksum_display}")

    except Exception as e:
        console.print(f"[red]Error querying schema version: {e}[/red]")
        logger.exception("Failed to query schema version")
        raise typer.Exit(1) from e


def history_command(limit: int = 10) -> None:
    """Show schema version history.

    Displays a table of all schema versions applied to the database, ordered by
    most recent first.

    Args:
        limit: Maximum number of versions to display (default: 10)

    Example:
        $ taboot schema history
        $ taboot schema history --limit 20
    """
    try:
        # Get schema version history from service (handles limit clamping)
        results = get_schema_version_history(limit)

        if not results:
            console.print("[yellow]No schema versions recorded in database[/yellow]")
            console.print("\nRun [bold]taboot init[/bold] to initialize schema")
            return

        # Create table
        table = Table(
            title="Schema Version History",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Version", style="bold")
        table.add_column("Applied At")
        table.add_column("Applied By")
        table.add_column("Exec Time")
        table.add_column("Status")
        table.add_column("Checksum")

        for version, applied_at, applied_by, exec_time, status, checksum in results:
            # Status styling using helper
            status_styled = _style_status(status)

            # Version styling (highlight current)
            if version == CURRENT_SCHEMA_VERSION:
                version_styled = f"[bold green]{version}[/bold green]"
            else:
                version_styled = version

            table.add_row(
                version_styled,
                str(applied_at),
                applied_by,
                f"{exec_time}ms" if exec_time is not None else "-",
                status_styled,
                (checksum[:16] + "..." if checksum and len(checksum) >= 16 else (checksum or "N/A")),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error querying schema history: {e}[/red]")
        logger.exception("Failed to query schema history")
        raise typer.Exit(1) from e


# Export public API
__all__ = [
    "history_command",
    "version_command",
]
