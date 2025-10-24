"""Migration commands for PostgreSQL, Neo4j, and Qdrant schema evolution.

Provides CLI commands to run database migrations:
- postgres: Apply Alembic migrations to PostgreSQL
- neo4j: Apply Cypher migrations to Neo4j
- all: Apply all migrations in correct order

Per MIGRATIONS.md:
- PostgreSQL: Use Alembic for schema versioning
- Neo4j: Idempotent Cypher migrations tracked in PostgreSQL
- Qdrant: Collection versioning via aliases (no explicit migrations)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def migrate_postgres() -> None:
    """Apply PostgreSQL Alembic migrations.

    Runs `alembic upgrade head` to apply all pending migrations.

    Raises:
        SystemExit: If migration fails.

    Example:
        $ taboot migrate postgres
        Applying PostgreSQL migrations...
        ✅ PostgreSQL migrations applied successfully
    """
    console.print("[blue]Applying PostgreSQL migrations...[/blue]")

    try:
        result = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)
        console.print("[green]✅ PostgreSQL migrations applied successfully[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ PostgreSQL migration failed:[/red] {e.stderr}")
        raise typer.Exit(code=1) from e


def migrate_neo4j() -> None:
    """Apply Neo4j Cypher migrations.

    Reads migrations from packages/graph/migrations/*.cypher and applies them
    in version order. Tracks applied versions in PostgreSQL schema_versions table.

    Raises:
        SystemExit: If migration fails.

    Example:
        $ taboot migrate neo4j
        Applying Neo4j migrations...
        ✅ Neo4j migrations applied successfully
    """
    console.print("[blue]Applying Neo4j migrations...[/blue]")

    try:
        from packages.common.config import get_config
        from packages.common.postgres_pool import PostgresPool
        from packages.graph.client import Neo4jClient
        from packages.graph.migrations.runner import Neo4jMigrationRunner

        # Initialize clients
        config = get_config()
        neo4j_client = Neo4jClient()
        neo4j_client.connect()

        postgres_pool = PostgresPool(config)

        # Run migrations
        runner = Neo4jMigrationRunner(neo4j_client.get_driver())
        migrations_dir = Path(__file__).parents[4] / "packages" / "graph" / "migrations"

        with postgres_pool.get_connection() as postgres_conn:
            runner.apply_migrations(migrations_dir, postgres_conn)

        # Cleanup
        postgres_pool.close_all()
        neo4j_client.close()

        console.print("[green]✅ Neo4j migrations applied successfully[/green]")

    except Exception as e:
        console.print(f"[red]❌ Neo4j migration failed:[/red] {e}")
        raise typer.Exit(code=1) from e


def migrate_all() -> None:
    """Apply all migrations in correct dependency order.

    Applies migrations in this order:
    1. PostgreSQL (creates schema_versions table)
    2. Neo4j (uses schema_versions for tracking)

    Qdrant collections are created on-demand by the application.

    Example:
        $ taboot migrate all
        Applying all migrations...
        ✅ All migrations completed successfully
    """
    console.print("[blue]Applying all migrations...[/blue]")

    # Apply PostgreSQL migrations first (creates schema_versions table)
    migrate_postgres()

    # Apply Neo4j migrations (uses schema_versions)
    migrate_neo4j()

    console.print("[green]✅ All migrations completed successfully[/green]")


# Export public API
__all__ = ["migrate_postgres", "migrate_neo4j", "migrate_all"]
