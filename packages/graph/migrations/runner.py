"""Neo4j migration runner for applying Cypher schema migrations.

Applies versioned Cypher migrations in order, tracking applied versions in PostgreSQL.
Follows MIGRATIONS.md guidelines for idempotent constraint creation and zero-downtime changes.

Migration files should be named: {version}_{description}.cypher
Example: 001_initial_constraints.cypher

Each migration should be idempotent using `IF NOT EXISTS` clauses.
"""

from __future__ import annotations

from pathlib import Path

from neo4j import Driver

from packages.common.logging import get_logger

logger = get_logger(__name__)


class Neo4jMigrationRunner:
    """Runner for Neo4j Cypher migrations.

    Applies migrations in version order and tracks applied versions in PostgreSQL.
    Ensures idempotency and supports zero-downtime migrations.

    Attributes:
        driver: Neo4j driver for executing Cypher statements.

    Example:
        >>> from packages.graph.client import Neo4jClient
        >>> client = Neo4jClient()
        >>> client.connect()
        >>> runner = Neo4jMigrationRunner(client.get_driver())
        >>> migrations_dir = Path("packages/graph/migrations")
        >>> runner.apply_migrations(migrations_dir)
    """

    def __init__(self, driver: Driver) -> None:
        """Initialize migration runner.

        Args:
            driver: Neo4j driver for executing migrations.
        """
        self.driver = driver

    def apply_migrations(self, migrations_dir: Path, postgres_conn) -> None:  # type: ignore
        """Apply all pending Cypher migrations.

        Reads .cypher files from migrations_dir, applies them in version order,
        and records applied versions in PostgreSQL schema_versions table.

        Args:
            migrations_dir: Directory containing .cypher migration files.
            postgres_conn: PostgreSQL connection for tracking versions.

        Raises:
            FileNotFoundError: If migrations_dir does not exist.
            ValueError: If migration file naming is invalid.

        Example:
            >>> runner.apply_migrations(
            ...     Path("packages/graph/migrations"),
            ...     postgres_conn
            ... )
        """
        if not migrations_dir.exists():
            raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

        # Get currently applied versions from PostgreSQL
        applied_versions = self._get_applied_versions(postgres_conn)

        # Find all .cypher migration files
        migration_files = sorted(migrations_dir.glob("*.cypher"))

        if not migration_files:
            logger.info("No Neo4j migrations found", extra={"migrations_dir": str(migrations_dir)})
            return

        # Apply pending migrations
        for migration_file in migration_files:
            version, description = self._parse_migration_filename(migration_file)

            if version in applied_versions:
                logger.debug(
                    "Skipping already applied migration",
                    extra={
                        "version": version,
                        "description": description,
                        "file": migration_file.name,
                    },
                )
                continue

            logger.info(
                "Applying Neo4j migration",
                extra={
                    "version": version,
                    "description": description,
                    "file": migration_file.name,
                },
            )

            # Read and execute migration
            cypher = migration_file.read_text()
            self._execute_migration(cypher)

            # Record applied version in PostgreSQL
            self._record_version(postgres_conn, version, description)

            logger.info(
                "Neo4j migration applied successfully",
                extra={"version": version, "description": description},
            )

        logger.info("All Neo4j migrations applied successfully")

    def _get_applied_versions(self, postgres_conn) -> set[str]:  # type: ignore
        """Get set of applied migration versions from PostgreSQL.

        Args:
            postgres_conn: PostgreSQL connection.

        Returns:
            set[str]: Set of applied version strings.
        """
        cursor = postgres_conn.cursor()
        cursor.execute(
            "SELECT version FROM schema_versions WHERE component = 'neo4j' ORDER BY version"
        )
        versions = {row[0] for row in cursor.fetchall()}
        cursor.close()
        return versions

    def _parse_migration_filename(self, migration_file: Path) -> tuple[str, str]:
        """Parse migration filename to extract version and description.

        Args:
            migration_file: Path to migration file.

        Returns:
            tuple[str, str]: (version, description)

        Raises:
            ValueError: If filename format is invalid.

        Example:
            >>> _parse_migration_filename(Path("001_initial_constraints.cypher"))
            ('001', 'initial_constraints')
        """
        stem = migration_file.stem
        parts = stem.split("_", 1)

        if len(parts) != 2:
            raise ValueError(
                f"Invalid migration filename: {migration_file.name}. "
                f"Expected format: {{version}}_{{description}}.cypher"
            )

        version, description = parts
        return version, description

    def _execute_migration(self, cypher: str) -> None:
        """Execute Cypher migration statements.

        Args:
            cypher: Cypher statements to execute.

        Raises:
            Exception: If migration execution fails.
        """
        with self.driver.session() as session:
            # Split on semicolons and execute each statement
            statements = [stmt.strip() for stmt in cypher.split(";") if stmt.strip()]

            for statement in statements:
                try:
                    session.run(statement)
                except Exception as e:
                    logger.error(
                        "Failed to execute migration statement",
                        extra={"statement": statement[:100], "error": str(e)},
                    )
                    raise

    def _record_version(self, postgres_conn, version: str, description: str) -> None:  # type: ignore
        """Record applied migration version in PostgreSQL.

        Args:
            postgres_conn: PostgreSQL connection.
            version: Migration version.
            description: Migration description.
        """
        cursor = postgres_conn.cursor()
        cursor.execute(
            """
            INSERT INTO schema_versions (component, version, description)
            VALUES ('neo4j', %s, %s)
            """,
            (version, description),
        )
        postgres_conn.commit()
        cursor.close()


# Export public API
__all__ = ["Neo4jMigrationRunner"]
