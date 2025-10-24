"""CLI status command implementation.

Top-level system status display showing health of all services.
"""


import typer
from rich.console import Console
from rich.table import Table

from packages.common.health import check_system_health

console = Console()


async def status_command(
    component: str | None = None,
    verbose: bool = False,
) -> None:
    """Display system status, health checks, and performance metrics.

    Args:
        component: Optional component to filter (neo4j, qdrant, redis, etc.)
        verbose: Show detailed metrics and configuration.
    """
    try:
        console.print("\n[bold cyan]System Status[/bold cyan]\n")

        # Get real health status from all services
        health_status = await check_system_health()
        services = health_status["services"]

        # Filter by component if specified
        if component:
            if component not in services:
                console.print(f"[red]Unknown component: {component}[/red]")
                raise typer.Exit(1)
            services = {component: services[component]}

        # Create status table
        table = Table(title="Service Health")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Message")

        if verbose:
            table.add_column("Details")

        # Add rows
        for service_name in sorted(services.keys()):
            healthy = services[service_name]
            status_display = "[green]✓[/green]" if healthy else "[red]✗[/red]"
            message = "" if healthy else "Service unavailable"

            if verbose:
                # TODO: Add actual detailed metrics per service
                details_str = "Connected" if healthy else "Disconnected"
                table.add_row(service_name, status_display, message, details_str)
            else:
                table.add_row(service_name, status_display, message)

        console.print(table)
        console.print()

        # Exit with error if any service unhealthy
        if not health_status["healthy"]:
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error retrieving status: {e}[/red]")
        raise typer.Exit(1)
