"""Schema management commands for Taboot CLI.

Provides commands for viewing and managing PostgreSQL schema versions:
- schema version: Show current database schema version
- schema history: Show schema version history
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from packages.common.config import get_config
from packages.common.db_schema import CURRENT_SCHEMA_VERSION, _get_connection, get_current_version
from packages.common.logging import get_logger

console = Console()
logger = get_logger(__name__)


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
        config = get_config()
        conn = _get_connection(config)

        try:
            with conn.cursor() as cursor:
                # Get current version
                current_version = get_current_version(cursor)

                if not current_version:
                    console.print("[yellow]No schema version recorded in database[/yellow]")
                    console.print(f"Expected version: [bold]{CURRENT_SCHEMA_VERSION}[/bold]")
                    console.print("\nRun [bold]taboot init[/bold] to initialize schema")
                    return

                # Get full version details
                cursor.execute(
                    """
                    SELECT version, applied_at, applied_by, execution_time_ms, status, checksum
                    FROM schema_versions
                    WHERE version = %s
                    ORDER BY applied_at DESC
                    LIMIT 1
                    """,
                    (current_version,),
                )
                result = cursor.fetchone()

                if result:
                    version, applied_at, applied_by, exec_time, status, checksum = result

                    # Create status indicator
                    if status == "success":
                        status_icon = "[green]✓[/green]"
                        status_text = f"[green]{status}[/green]"
                    elif status == "failed":
                        status_icon = "[red]✗[/red]"
                        status_text = f"[red]{status}[/red]"
                    else:
                        status_icon = "[yellow]?[/yellow]"
                        status_text = f"[yellow]{status}[/yellow]"

                    # Version match indicator
                    if version == CURRENT_SCHEMA_VERSION:
                        version_match = "[green](matches expected)[/green]"
                    else:
                        version_match = f"[yellow](expected: {CURRENT_SCHEMA_VERSION})[/yellow]"

                    # Display version info
                    version_line = f"{status_icon} Current schema version: "
                    version_line += f"[bold]{version}[/bold] {version_match}"
                    console.print(f"\n{version_line}")
                    console.print(f"  Applied at: {applied_at}")
                    console.print(f"  Applied by: {applied_by}")
                    if exec_time:
                        console.print(f"  Execution time: {exec_time}ms")
                    console.print(f"  Status: {status_text}")
                    console.print(f"  Checksum: {checksum[:16]}...")

        finally:
            conn.close()

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
        config = get_config()
        conn = _get_connection(config)

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT version, applied_at, applied_by, execution_time_ms, status, checksum
                    FROM schema_versions
                    ORDER BY applied_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                results = cursor.fetchall()

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
                    # Status styling
                    if status == "success":
                        status_styled = f"[green]{status}[/green]"
                    elif status == "failed":
                        status_styled = f"[red]{status}[/red]"
                    else:
                        status_styled = f"[yellow]{status}[/yellow]"

                    # Version styling (highlight current)
                    if version == CURRENT_SCHEMA_VERSION:
                        version_styled = f"[bold green]{version}[/bold green]"
                    else:
                        version_styled = version

                    table.add_row(
                        version_styled,
                        str(applied_at),
                        applied_by,
                        f"{exec_time}ms" if exec_time else "-",
                        status_styled,
                        checksum[:16] + "...",
                    )

                console.print(table)

        finally:
            conn.close()

    except Exception as e:
        console.print(f"[red]Error querying schema history: {e}[/red]")
        logger.exception("Failed to query schema history")
        raise typer.Exit(1) from e


# Export public API
__all__ = [
    "history_command",
    "version_command",
]
