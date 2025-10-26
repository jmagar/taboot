"""PostgreSQL schema creation and verification for Taboot platform.

Provides utilities for loading and executing SQL schema files, creating database
schema, and verifying table existence. Used during initialization (taboot init).
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extensions import connection
from psycopg2.extensions import cursor as Cursor  # noqa: N812
from psycopg2.extras import RealDictCursor

from packages.common.config import TabootConfig, _is_running_in_container, get_config
from packages.common.logging import get_logger
from packages.common.tracing import TracingContext

logger = get_logger(__name__)

# Current schema version - must match "THIS VERSION:" comment in postgresql-schema.sql
CURRENT_SCHEMA_VERSION = "2.0.0"


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


def get_schema_checksum(sql_content: str) -> str:
    """Calculate SHA-256 checksum of schema SQL.

    Args:
        sql_content: SQL content as string.

    Returns:
        str: SHA-256 checksum as hex digest.

    Example:
        >>> sql = "CREATE TABLE test (id INT PRIMARY KEY);"
        >>> checksum = get_schema_checksum(sql)
        >>> len(checksum)
        64
    """
    return hashlib.sha256(sql_content.encode("utf-8")).hexdigest()


def extract_schema_version(sql_content: str) -> str | None:
    """Extract schema version from SQL file comment.

    Parses the "THIS VERSION: X.Y.Z" comment from the schema SQL file.

    Args:
        sql_content: SQL content as string.

    Returns:
        str | None: Version string if found, None otherwise.

    Example:
        >>> sql = "-- THIS VERSION: 1.0.0\\nCREATE TABLE test (id INT);"
        >>> extract_schema_version(sql)
        '1.0.0'
    """
    match = re.search(r"--\s*THIS\s+VERSION:\s*(\S+)", sql_content, re.IGNORECASE)
    return match.group(1) if match else None


def get_current_version(cursor: Cursor) -> str | None:
    """Get the currently applied schema version from database.

    Args:
        cursor: Database cursor object.

    Returns:
        str | None: Current version string if found, None if no version recorded.

    Example:
        >>> from packages.common.config import get_config
        >>> config = get_config()
        >>> conn = _get_connection(config)
        >>> cursor = conn.cursor()
        >>> version = get_current_version(cursor)
        >>> cursor.close()
        >>> conn.close()
    """
    try:
        cursor.execute(
            "SELECT version FROM schema_versions "
            "WHERE status = 'success' "
            "ORDER BY applied_at DESC LIMIT 1"
        )
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception:
        # Table doesn't exist yet (first run)
        return None


def _get_connection(config: TabootConfig) -> connection:
    """Create PostgreSQL connection using config (private implementation).

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
        return conn
    except psycopg2.Error as e:
        raise ConnectionError(f"Failed to connect to PostgreSQL: {e}") from e


def get_connection(config: TabootConfig) -> connection:
    """Create PostgreSQL connection using config (public API).

    Args:
        config: Taboot configuration containing postgres_connection_string.

    Returns:
        PgConnection: PostgreSQL connection object.

    Raises:
        ConnectionError: On connection failure.

    Example:
        >>> from packages.common.config import get_config
        >>> config = get_config()
        >>> conn = get_connection(config)
        >>> conn.close()
    """
    return _get_connection(config)


def create_schema(config: TabootConfig, schema_path: str | None = None) -> None:
    """Create PostgreSQL schema by executing schema SQL file with version tracking.

    Loads SQL from specs/001-taboot-rag-platform/contracts/postgresql-schema.sql
    (or from custom path if provided), checks version state, executes within a
    transaction, and records version metadata in schema_versions table.

    Version tracking workflow:
    1. Extract version from schema SQL file (THIS VERSION: comment)
    2. Calculate SHA-256 checksum of SQL content
    3. Check current database version
    4. If version matches, verify checksum or skip if identical
    5. If version differs or checksum mismatch, apply schema
    6. Record version, checksum, and execution metadata on success
    7. Record failure with error details on exception

    Args:
        config: Taboot configuration containing postgres_connection_string.
        schema_path: Optional path to SQL schema file. If None, defaults to
            specs/001-taboot-rag-platform/contracts/postgresql-schema.sql.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
        ConnectionError: If database connection fails.
        ValueError: If schema file missing THIS VERSION comment.
        RuntimeError: If SQL execution fails (transaction will be rolled back).

    Example:
        >>> from packages.common.config import get_config
        >>> config = get_config()
        >>> create_schema(config)
        >>> # Or with custom schema path:
        >>> create_schema(config, schema_path="/custom/schema.sql")
    """
    with TracingContext() as correlation_id:
        logger.info(
            "Starting schema creation with version tracking",
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

        # Extract version from SQL file
        file_version = extract_schema_version(sql_content)
        if not file_version:
            raise ValueError(
                "Schema file missing THIS VERSION comment. "
                "Add '-- THIS VERSION: X.Y.Z' to schema SQL file."
            )

        # Verify version matches constant
        if file_version != CURRENT_SCHEMA_VERSION:
            logger.warning(
                "Schema file version mismatch with CURRENT_SCHEMA_VERSION constant",
                extra={
                    "file_version": file_version,
                    "constant_version": CURRENT_SCHEMA_VERSION,
                },
            )

        # Calculate checksum
        checksum = get_schema_checksum(sql_content)

        logger.info(
            "Loaded schema SQL",
            extra={
                "correlation_id": correlation_id,
                "file_path": str(schema_path_obj),
                "version": file_version,
                "checksum": checksum[:16] + "...",
                "sql_length": len(sql_content),
            },
        )

        # Get database connection
        conn = _get_connection(config)

        try:
            with conn.cursor() as cursor:
                # Check current version
                current_version = get_current_version(cursor)

                if current_version == file_version:
                    # Verify checksum matches
                    cursor.execute(
                        "SELECT checksum FROM schema_versions WHERE version = %s",
                        (current_version,),
                    )
                    result = cursor.fetchone()
                    stored_checksum = result[0] if result else None

                    if stored_checksum == checksum:
                        logger.info(
                            "Schema already at current version with matching checksum - skipping",
                            extra={
                                "correlation_id": correlation_id,
                                "version": current_version,
                                "checksum": checksum[:16] + "...",
                            },
                        )
                        return

                    logger.warning(
                        "Schema checksum mismatch - schema file modified",
                        extra={
                            "correlation_id": correlation_id,
                            "version": current_version,
                            "expected": stored_checksum[:16] + "..." if stored_checksum else "none",
                            "actual": checksum[:16] + "...",
                        },
                    )

                # Apply schema
                start_time = datetime.now()
                logger.info(
                    "Executing schema SQL",
                    extra={
                        "correlation_id": correlation_id,
                        "from_version": current_version or "none",
                        "to_version": file_version,
                    },
                )
                cursor.execute(sql_content)
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

                # Record version
                cursor.execute(
                    """
                    INSERT INTO schema_versions (version, description, checksum, execution_time_ms)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (version) DO UPDATE
                    SET applied_at = NOW(),
                        checksum = EXCLUDED.checksum,
                        execution_time_ms = EXCLUDED.execution_time_ms,
                        status = 'success'
                    """,
                    (
                        file_version,
                        f"Applied schema version {file_version}",
                        checksum,
                        execution_time,
                    ),
                )

            # Commit transaction
            conn.commit()
            logger.info(
                "Schema creation completed successfully",
                extra={
                    "correlation_id": correlation_id,
                    "from_version": current_version or "none",
                    "to_version": file_version,
                    "execution_time_ms": execution_time,
                    "checksum": checksum[:16] + "...",
                },
            )

        except Exception as e:
            # Rollback on error
            conn.rollback()

            # Try to record failed migration (may fail if schema_versions doesn't exist yet)
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO schema_versions (version, description, checksum, status)
                        VALUES (%s, %s, %s, 'failed')
                        ON CONFLICT (version) DO UPDATE
                        SET status = 'failed',
                            applied_at = NOW()
                        """,
                        (
                            file_version,
                            f"Failed to apply version {file_version}: {str(e)[:200]}",
                            checksum,
                        ),
                    )
                conn.commit()
            except Exception:
                # Ignore errors recording failure (table may not exist)
                pass

            logger.exception(
                "Schema creation failed, rolling back",
                extra={
                    "correlation_id": correlation_id,
                    "version": file_version,
                },
            )
            raise RuntimeError("Schema creation failed") from e

        finally:
            conn.close()


def verify_schema(config: TabootConfig) -> dict[str, list[str]]:
    """Verify schema by querying information_schema for existing tables.

    Queries information_schema.tables to get list of table names in rag and auth schemas.
    Expected rag tables: documents, document_content, extraction_windows,
    ingestion_jobs, extraction_jobs.
    Expected auth tables: user, session, account, verification, twoFactor.

    Args:
        config: Taboot configuration containing postgres_connection_string.

    Returns:
        dict[str, list[str]]: Dictionary mapping schema names to table lists.
            Example: {"rag": ["documents", "extraction_windows"], "auth": ["user", "session"]}

    Raises:
        ConnectionError: If database connection fails.

    Example:
        >>> from packages.common.config import get_config
        >>> config = get_config()
        >>> schemas = verify_schema(config)
        >>> "documents" in schemas["rag"]
        True
        >>> "user" in schemas["auth"]
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
                # Query information_schema for table names in both schemas
                query = """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema IN ('rag', 'auth')
                    ORDER BY table_schema, table_name
                """
                cursor.execute(query)

                # Fetch all table names grouped by schema
                rows = cursor.fetchall()
                schema_tables: dict[str, list[str]] = {"rag": [], "auth": []}

                for row in rows:
                    schema_name = row[0]
                    table_name = row[1]
                    if schema_name in schema_tables:
                        schema_tables[schema_name].append(table_name)

                logger.info(
                    "Schema verification completed",
                    extra={
                        "correlation_id": correlation_id,
                        "rag_table_count": len(schema_tables["rag"]),
                        "auth_table_count": len(schema_tables["auth"]),
                        "rag_tables": schema_tables["rag"],
                        "auth_tables": schema_tables["auth"],
                    },
                )

                return schema_tables

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
        return conn
    except psycopg2.Error as e:
        logger.exception("Failed to connect to PostgreSQL")
        raise ConnectionError("Failed to connect to PostgreSQL") from e


class SchemaVersionDetails:
    """Details of a schema version record from the database."""

    def __init__(
        self,
        version: str,
        applied_at: datetime,
        applied_by: str,
        execution_time_ms: int | None,
        status: str,
        checksum: str | None,
    ) -> None:
        """Initialize SchemaVersionDetails.

        Args:
            version: Schema version string (e.g., '2.0.0')
            applied_at: Timestamp when schema was applied
            applied_by: Database user who applied the schema
            execution_time_ms: Time taken to execute schema in milliseconds
            status: Status of schema application ('success' or 'failed')
            checksum: SHA-256 checksum of schema SQL (first 16 chars displayed)
        """
        self.version = version
        self.applied_at = applied_at
        self.applied_by = applied_by
        self.execution_time_ms = execution_time_ms
        self.status = status
        self.checksum = checksum

    def to_tuple(self) -> tuple:
        """Convert to tuple for unpacking."""
        return (self.version, self.applied_at, self.applied_by, self.execution_time_ms, self.status, self.checksum)


def get_schema_version_details() -> SchemaVersionDetails | None:
    """Get current schema version with full details from database.

    Queries the schema_versions table to retrieve the most recently applied
    schema version along with all metadata.

    Returns:
        SchemaVersionDetails if a schema version is recorded, None otherwise.

    Raises:
        ConnectionError: If database connection fails.

    Example:
        >>> details = get_schema_version_details()
        >>> if details:
        ...     print(f"Version: {details.version}")
        ...     print(f"Applied at: {details.applied_at}")
        ...     print(f"Status: {details.status}")
        ... else:
        ...     print("No schema version recorded")
    """
    config = get_config()
    conn = get_connection(config)
    try:
        with conn.cursor() as cursor:
            current_version = get_current_version(cursor)
            if not current_version:
                return None

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
                return SchemaVersionDetails(*result)
            return None
    finally:
        conn.close()


def get_schema_version_history(limit: int = 10) -> list[tuple]:
    """Get schema version history from database with limit clamping.

    Retrieves a historical record of schema versions applied to the database,
    ordered by most recent first. Limits are clamped to [1, 100] for safety.

    Args:
        limit: Maximum number of versions to retrieve (default: 10). Will be
            clamped to the range [1, 100].

    Returns:
        List of tuples containing (version, applied_at, applied_by,
        execution_time_ms, status, checksum) for each recorded schema version.
        Returns empty list if no versions recorded.

    Raises:
        ConnectionError: If database connection fails.

    Example:
        >>> history = get_schema_version_history(limit=20)
        >>> for version, applied_at, applied_by, exec_time, status, checksum in history:
        ...     print(f"{version} - {status}")
    """
    clamped_limit = max(1, min(int(limit), 100))
    config = get_config()
    conn = get_connection(config)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT version, applied_at, applied_by, execution_time_ms, status, checksum
                FROM schema_versions
                ORDER BY applied_at DESC
                LIMIT %s
                """,
                (clamped_limit,),
            )
            return cursor.fetchall()
    finally:
        conn.close()


# Export public API
__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "SchemaVersionDetails",
    "create_postgresql_schema",
    "create_schema",
    "extract_schema_version",
    "get_connection",
    "get_current_version",
    "get_postgres_client",
    "get_schema_checksum",
    "get_schema_version_details",
    "get_schema_version_history",
    "load_schema_file",
    "verify_schema",
]
