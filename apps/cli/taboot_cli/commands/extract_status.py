"""Extract status command for Taboot CLI.

Implements the system status display using GetStatusUseCase:
1. Create and configure all dependencies (Redis client, health checker)
2. Execute GetStatusUseCase
3. Display formatted status with Rich tables
4. Handle errors gracefully

This command is thin - all business logic is in packages/core/use_cases/get_status.py.
"""

from __future__ import annotations

import logging

import redis.asyncio
import typer
from redis.asyncio import Redis
from rich.console import Console
from rich.table import Table

from packages.common.config import get_config
from packages.common.health import check_system_health
from packages.core.use_cases.get_status import GetStatusUseCase, SystemStatus

console = Console()
logger = logging.getLogger(__name__)


async def extract_status_command() -> None:
    """Display system status including service health, queue depths, and metrics.

    Orchestrates the full status collection pipeline:
    GetStatusUseCase → Service Health + Queue Depths + Metrics → Rich Tables

    Expected output:
        System Status
        ─────────────────────

        Service Health
        ┏━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
        ┃ Service    ┃ Status  ┃ Message                ┃
        ┡━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
        │ neo4j      │ ✓       │                        │
        │ qdrant     │ ✓       │                        │
        │ redis      │ ✓       │                        │
        │ tei        │ ✓       │                        │
        │ ollama     │ ✓       │                        │
        │ firecrawl  │ ✓       │                        │
        │ playwright │ ✓       │                        │
        └────────────┴─────────┴────────────────────────┘

        Queue Depth
        ┏━━━━━━━━━━━━━━━━┳━━━━━━━┓
        ┃ Queue          ┃ Depth ┃
        ┡━━━━━━━━━━━━━━━━╇━━━━━━━┩
        │ Ingestion      │ 5     │
        │ Extraction     │ 12    │
        └────────────────┴───────┘

        Metrics
        ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
        ┃ Metric                     ┃ Count  ┃
        ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
        │ Documents Ingested         │ 150    │
        │ Chunks Indexed             │ 3,420  │
        │ Extraction Jobs Completed  │ 138    │
        │ Graph Nodes Created        │ 892    │
        └────────────────────────────┴────────┘

    Raises:
        typer.Exit: Exit with code 1 if status collection fails.
    """
    try:
        # Load config
        config = get_config()

        # Display starting message
        console.print("\n[bold cyan]System Status[/bold cyan]")
        console.print("─────────────────────\n")

        # Create dependencies
        logger.info("Creating status collection dependencies")

        # Redis client for queue depth queries
        redis_client: Redis[bytes] = await redis.asyncio.from_url(config.redis_url)

        # Create use case
        use_case = GetStatusUseCase(
            redis_client=redis_client,
            health_checker=check_system_health,
        )

        # Execute status collection
        logger.info("Executing system status collection")
        status: SystemStatus = await use_case.execute()

        # Close Redis connection
        await redis_client.close()

        # Display results
        _display_service_health(status)
        _display_queue_depth(status)
        _display_metrics(status)

        logger.info("Status display complete")

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit code
        raise
    except Exception as e:
        # Catch any other errors and report them
        console.print(f"[red]✗ Failed to retrieve system status: {e}[/red]")
        logger.exception("Status collection failed")
        raise typer.Exit(1) from None


def _display_service_health(status: SystemStatus) -> None:
    """Display service health table with colored status indicators.

    Args:
        status: SystemStatus containing service health information.
    """
    table = Table(title="Service Health")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Message")

    for service_name in sorted(status.services.keys()):
        service = status.services[service_name]

        # Color-code status
        status_display = "[green]✓[/green]" if service.healthy else "[red]✗[/red]"
        message = service.message or ""

        table.add_row(service_name, status_display, message)

    console.print(table)
    console.print()


def _display_queue_depth(status: SystemStatus) -> None:
    """Display queue depth table.

    Args:
        status: SystemStatus containing queue depth information.
    """
    table = Table(title="Queue Depth")
    table.add_column("Queue", style="cyan")
    table.add_column("Depth", justify="right", style="bold")

    table.add_row("Ingestion", str(status.queue_depth.ingestion))
    table.add_row("Extraction", str(status.queue_depth.extraction))

    console.print(table)
    console.print()


def _display_metrics(status: SystemStatus) -> None:
    """Display metrics snapshot table.

    Args:
        status: SystemStatus containing metrics information.
    """
    table = Table(title="Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="bold")

    # Format numbers with thousands separators
    table.add_row(
        "Documents Ingested",
        f"{status.metrics.documents_ingested:,}",
    )
    table.add_row(
        "Chunks Indexed",
        f"{status.metrics.chunks_indexed:,}",
    )
    table.add_row(
        "Extraction Jobs Completed",
        f"{status.metrics.extraction_jobs_completed:,}",
    )
    table.add_row(
        "Graph Nodes Created",
        f"{status.metrics.graph_nodes_created:,}",
    )

    console.print(table)


# Export public API
__all__ = ["extract_status_command"]
