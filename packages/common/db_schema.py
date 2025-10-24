"""PostgreSQL schema creation and verification for Taboot platform.

Provides utilities for loading and executing SQL schema files, creating database
schema, and verifying table existence. Used during initialization (taboot init).
"""

from pathlib import Path
from typing import cast

import psycopg2
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor

from packages.common.config import TabootConfig, _is_running_in_container, get_config
from packages.common.logging import get_logger
from packages.common.tracing import TracingContext

logger = get_logger(__name__)


def load_schema_file(path: Path) -> str:
    """Load SQL schema file from given path.

    Args:
        path: Path to the SQL schema file.

    Returns:
        str: SQL content as string.

    Raises:
        FileNotFoundError: If the file doesn't exist.

    Example:
        >>> schema_path = Path("specs/001-taboot-rag-platform/contracts/postgresql-schema.sql")
        >>> sql_content = load_schema_file(schema_path)
        >>> "CREATE TABLE IF NOT EXISTS documents" in sql_content
        True
    """
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path}")

    return path.read_text(encoding="utf-8")


def _get_connection(config: TabootConfig) -> connection:
    """Create PostgreSQL connection using config.

    Args:
        config: Taboot configuration containing postgres_connection_string.

    Returns:
        PgConnection: PostgreSQL connection object.

    Raises:
        ConnectionError: On connection failure.

    Example:
        >>> from packages.common.config import get_config
        >>> config = get_config()
        >>> conn = _get_connection(config)
        >>> conn.close()
    """
    try:
        conn = psycopg2.connect(config.postgres_connection_string)
        return cast(connection, conn)
    except psycopg2.Error as e:
        raise ConnectionError(f"Failed to connect to PostgreSQL: {e}") from e


def create_schema(config: TabootConfig, schema_path: str | None = None) -> None:
    """Create PostgreSQL schema by executing schema SQL file.

    Loads SQL from specs/001-taboot-rag-platform/contracts/postgresql-schema.sql
    (or from custom path if provided), executes it within a transaction, and commits
    on success or rolls back on error.

    Args:
        config: Taboot configuration containing postgres_connection_string.
        schema_path: Optional path to SQL schema file. If None, defaults to
            specs/001-taboot-rag-platform/contracts/postgresql-schema.sql.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
        ConnectionError: If database connection fails.
        Exception: If SQL execution fails (transaction will be rolled back).

    Example:
        >>> from packages.common.config import get_config
        >>> config = get_config()
        >>> create_schema(config)
        >>> # Or with custom schema path:
        >>> create_schema(config, schema_path="/custom/schema.sql")
    """
    with TracingContext() as correlation_id:
        logger.info(
            "Starting schema creation",
            extra={"correlation_id": correlation_id},
        )

        # Load schema SQL
        if schema_path is None:
            schema_path_obj = (
                Path(__file__).resolve().parent.parent.parent
                / "specs"
                / "001-taboot-rag-platform"
                / "contracts"
                / "postgresql-schema.sql"
            )
        else:
            schema_path_obj = Path(schema_path)

        sql_content = load_schema_file(schema_path_obj)

        logger.info(
            "Loaded schema SQL",
            extra={
                "correlation_id": correlation_id,
                "file_path": str(schema_path_obj),
                "sql_length": len(sql_content),
            },
        )

        # Get database connection
        conn = _get_connection(config)

        try:
            with conn.cursor() as cursor:
                # Execute SQL (may contain multiple statements)
                logger.info(
                    "Executing schema SQL",
                    extra={"correlation_id": correlation_id},
                )
                cursor.execute(sql_content)

            # Commit transaction
            conn.commit()
            logger.info(
                "Schema creation completed successfully",
                extra={"correlation_id": correlation_id},
            )

        except Exception as e:
            # Rollback on error
            conn.rollback()
            logger.exception(
                "Schema creation failed, rolling back",
                extra={"correlation_id": correlation_id},
            )
            raise RuntimeError("Schema creation failed") from e

        finally:
            conn.close()


def verify_schema(config: TabootConfig) -> list[str]:
    """Verify schema by querying information_schema for existing tables.

    Queries information_schema.tables to get list of table names in public schema.
    Expected tables: documents, extraction_windows, ingestion_jobs, extraction_jobs.

    Args:
        config: Taboot configuration containing postgres_connection_string.

    Returns:
        list[str]: List of table names found in the public schema.

    Raises:
        ConnectionError: If database connection fails.

    Example:
        >>> from packages.common.config import get_config
        >>> config = get_config()
        >>> tables = verify_schema(config)
        >>> "documents" in tables
        True
    """
    with TracingContext() as correlation_id:
        logger.info(
            "Verifying schema",
            extra={"correlation_id": correlation_id},
        )

        # Get database connection
        conn = _get_connection(config)

        try:
            with conn.cursor() as cursor:
                # Query information_schema for table names
                query = """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """
                cursor.execute(query)

                # Fetch all table names
                rows = cursor.fetchall()
                tables = [row[0] for row in rows]

                logger.info(
                    "Schema verification completed",
                    extra={
                        "correlation_id": correlation_id,
                        "table_count": len(tables),
                        "tables": tables,
                    },
                )

                return tables

        finally:
            conn.close()


async def create_postgresql_schema() -> None:
    """Create PostgreSQL schema asynchronously (async wrapper for create_schema).

    This async function is used by the /init endpoint and other async contexts.
    It wraps the synchronous create_schema function.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
        ConnectionError: If database connection fails.
        Exception: If SQL execution fails.

    Example:
        >>> await create_postgresql_schema()
    """
    import asyncio

    from packages.common.config import get_config

    config = get_config()
    await asyncio.to_thread(create_schema, config)


def get_postgres_client() -> connection:
    """Get PostgreSQL client connection.

    Returns:
        connection: PostgreSQL connection object with RealDictCursor factory.

    Raises:
        ConnectionError: If connection fails.

    Example:
        >>> conn = get_postgres_client()
        >>> cursor = conn.cursor()
        >>> cursor.execute("SELECT * FROM documents LIMIT 1")
        >>> conn.close()
    """
    config = get_config()

    # Determine host based on runtime environment
    host = "taboot-db" if _is_running_in_container() else "localhost"

    # Create connection with RealDictCursor for dict-like results
    try:
        conn = psycopg2.connect(
            host=host,
            port=config.postgres_port,
            user=config.postgres_user,
            password=config.postgres_password,
            database=config.postgres_db,
            cursor_factory=RealDictCursor,
        )
        logger.info("PostgreSQL client connected", extra={"host": host})
        return cast(connection, conn)
    except psycopg2.Error as e:
        logger.exception("Failed to connect to PostgreSQL")
        raise ConnectionError("Failed to connect to PostgreSQL") from e


# Export public API
__all__ = [
    "load_schema_file",
    "create_schema",
    "verify_schema",
    "create_postgresql_schema",
    "get_postgres_client",
]
