"""CLI list documents command implementation (T166).

Implements `taboot list documents` with filtering and pagination.
"""

import logging
import os
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from packages.schemas.models import ExtractionState, SourceType

console = Console()
logger = logging.getLogger(__name__)


def list_documents_command(
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum documents to show"),
    offset: int = typer.Option(0, "--offset", "-o", help="Number of documents to skip (pagination)"),
    source_type: Optional[str] = typer.Option(
        None, "--source-type", "-s", help="Filter by source type (web, github, etc.)"
    ),
    extraction_state: Optional[str] = typer.Option(
        None, "--extraction-state", "-e", help="Filter by extraction state (pending, completed, etc.)"
    ),
) -> None:
    """
    List ingested documents with optional filters and pagination.

    Filter options:
        --source-type: web, github, reddit, youtube, gmail, elasticsearch,
                      docker_compose, swag, tailscale, unifi, ai_session
        --extraction-state: pending, tier_a_done, tier_b_done, tier_c_done,
                           completed, failed

    Examples:
        taboot list documents
        taboot list documents --limit 20 --offset 10
        taboot list documents --source-type web
        taboot list documents --extraction-state pending
        taboot list documents --source-type github --extraction-state completed
    """
    console.print(f"\n[bold blue]Listing documents[/bold blue]")
    console.print(
        f"[dim]Filters: limit={limit}, offset={offset}, "
        f"source_type={source_type}, extraction_state={extraction_state}[/dim]\n"
    )

    try:
        # Parse and validate filters
        source_type_enum: Optional[SourceType] = None
        if source_type:
            try:
                source_type_enum = SourceType(source_type)
            except ValueError:
                valid_values = ", ".join([s.value for s in SourceType])
                console.print(
                    f"[red]Error:[/red] Invalid source_type '{source_type}'. "
                    f"Valid values: {valid_values}"
                )
                raise typer.Exit(1)

        extraction_state_enum: Optional[ExtractionState] = None
        if extraction_state:
            try:
                extraction_state_enum = ExtractionState(extraction_state)
            except ValueError:
                valid_values = ", ".join([e.value for e in ExtractionState])
                console.print(
                    f"[red]Error:[/red] Invalid extraction_state '{extraction_state}'. "
                    f"Valid values: {valid_values}"
                )
                raise typer.Exit(1)

        # Import use case and dependencies
        from packages.core.use_cases.list_documents import ListDocumentsUseCase
        from packages.common.db_schema import get_postgres_client

        # Get PostgreSQL client
        postgres_url = os.getenv("POSTGRES_URL", "postgresql://taboot:changeme@localhost:5432/taboot")
        db_client = get_postgres_client(postgres_url)

        # Execute use case
        import asyncio

        async def _execute():
            async with db_client as client:
                use_case = ListDocumentsUseCase(db_client=client)
                return await use_case.execute(
                    limit=limit,
                    offset=offset,
                    source_type=source_type_enum,
                    extraction_state=extraction_state_enum,
                )

        result = asyncio.run(_execute())

        # Display results
        if not result.documents:
            console.print("[yellow]No documents found matching filters.[/yellow]")
            return

        # Create rich table
        table = Table(title=f"Documents ({len(result.documents)} of {result.total} total)")
        table.add_column("Doc ID", style="cyan", no_wrap=True)
        table.add_column("Source Type", style="green")
        table.add_column("Source URL", style="blue", max_width=50)
        table.add_column("State", style="magenta")
        table.add_column("Ingested At", style="yellow")

        for doc in result.documents:
            table.add_row(
                str(doc.doc_id)[:8] + "...",  # Shortened UUID
                doc.source_type.value,
                doc.source_url[:47] + "..." if len(doc.source_url) > 50 else doc.source_url,
                doc.extraction_state.value,
                doc.ingested_at.strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)

        # Show pagination info
        if result.total > result.limit:
            pages = (result.total + result.limit - 1) // result.limit
            current_page = (result.offset // result.limit) + 1
            console.print(
                f"\n[dim]Page {current_page} of {pages} "
                f"(showing {result.offset + 1}-{result.offset + len(result.documents)} "
                f"of {result.total})[/dim]"
            )

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        logger.error(f"List documents command failed: {e}", exc_info=True)
        raise typer.Exit(1)
