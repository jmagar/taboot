"""Unit tests for PostgreSQL schema creation.

Tests the db_schema module for loading and executing SQL schema files.
Following TDD methodology - these tests should fail until T024 implements db_schema.py.
"""

from pathlib import Path
from typing import Any
import logging

import pytest

from packages.common.config import TabootConfig


@pytest.mark.unit
def test_load_schema_file_success(postgres_schema_path: Path) -> None:
    """Test that schema SQL file is loaded correctly."""
    # Import will fail until T024 implements the module
    from packages.common.db_schema import load_schema_file

    sql_content = load_schema_file(postgres_schema_path)

    # Verify SQL contains expected table definitions
    assert "CREATE TABLE IF NOT EXISTS documents" in sql_content
    assert "CREATE TABLE IF NOT EXISTS extraction_windows" in sql_content
    assert "CREATE TABLE IF NOT EXISTS ingestion_jobs" in sql_content
    assert "CREATE TABLE IF NOT EXISTS extraction_jobs" in sql_content
    assert 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"' in sql_content


@pytest.mark.unit
def test_load_schema_file_not_found() -> None:
    """Test error handling when schema file doesn't exist."""
    from packages.common.db_schema import load_schema_file

    non_existent_path = Path("/nonexistent/schema.sql")

    with pytest.raises(FileNotFoundError):
        load_schema_file(non_existent_path)


@pytest.mark.unit
def test_create_schema_executes_sql(test_config: TabootConfig, mocker: Any) -> None:
    """Test that create_schema function executes SQL statements."""
    from packages.common.db_schema import create_schema

    # Mock database connection and cursor (implementation-agnostic)
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Mock the actual connection function used in implementation
    # This will need to match whatever the implementation uses (psycopg2, asyncpg, etc.)
    mock_connect = mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)

    # Mock file reading to avoid actual file I/O
    mock_sql = """-- THIS VERSION: 1.0.0
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE TABLE IF NOT EXISTS documents (doc_id UUID PRIMARY KEY);
    CREATE TABLE IF NOT EXISTS extraction_windows (window_id UUID PRIMARY KEY);
    """
    mocker.patch("packages.common.db_schema.load_schema_file", return_value=mock_sql)

    # Execute schema creation
    create_schema(test_config)

    # Verify connection was established
    mock_connect.assert_called_once_with(test_config)

    # Verify SQL was executed
    mock_cursor.execute.assert_called_once_with(mock_sql)
    mock_conn.commit.assert_called_once()


@pytest.mark.unit
def test_create_schema_tables_created(test_config: TabootConfig, mocker: Any) -> None:
    """Test that all required tables are created."""
    from packages.common.db_schema import create_schema, verify_schema

    # Mock connection and cursor
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)

    # Mock load_schema_file to return minimal schema
    mock_sql = """-- THIS VERSION: 1.0.0
    CREATE TABLE IF NOT EXISTS documents (doc_id UUID PRIMARY KEY);
    CREATE TABLE IF NOT EXISTS extraction_windows (window_id UUID PRIMARY KEY);
    CREATE TABLE IF NOT EXISTS ingestion_jobs (job_id UUID PRIMARY KEY);
    CREATE TABLE IF NOT EXISTS extraction_jobs (job_id UUID PRIMARY KEY);
    """
    mocker.patch("packages.common.db_schema.load_schema_file", return_value=mock_sql)

    # Execute schema creation
    create_schema(test_config)

    # Mock fetchall for verification query
    mock_cursor.fetchall.return_value = [
        ("documents",),
        ("extraction_windows",),
        ("ingestion_jobs",),
        ("extraction_jobs",),
    ]

    # Verify schema
    tables = verify_schema(test_config)

    # All required tables should exist
    assert "documents" in tables
    assert "extraction_windows" in tables
    assert "ingestion_jobs" in tables
    assert "extraction_jobs" in tables


@pytest.mark.unit
def test_create_schema_idempotent(test_config: TabootConfig, mocker: Any) -> None:
    """Test that create_schema can be run multiple times safely."""
    from packages.common.db_schema import create_schema

    # Mock connection
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)

    # Mock schema file with CREATE IF NOT EXISTS statements
    mock_sql = """-- THIS VERSION: 1.0.0
    CREATE TABLE IF NOT EXISTS documents (doc_id UUID PRIMARY KEY);
    """
    mocker.patch("packages.common.db_schema.load_schema_file", return_value=mock_sql)

    # Execute schema creation twice
    create_schema(test_config)
    create_schema(test_config)

    # Should not raise errors - execute called twice
    assert mock_cursor.execute.call_count == 2
    assert mock_conn.commit.call_count == 2


@pytest.mark.unit
def test_create_schema_handles_sql_error(test_config: TabootConfig, mocker: Any) -> None:
    """Test error handling when SQL execution fails."""
    from packages.common.db_schema import create_schema

    # Mock connection that raises error on execute
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_cursor.execute.side_effect = Exception("SQL syntax error")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)
    mocker.patch("packages.common.db_schema.load_schema_file", return_value="INVALID SQL")

    # Should raise RuntimeError on SQL error
    with pytest.raises(RuntimeError):
        create_schema(test_config)

    # Connection should be rolled back on error
    mock_conn.rollback.assert_called_once()


@pytest.mark.unit
def test_create_schema_connection_error(test_config: TabootConfig, mocker: Any) -> None:
    """Test error handling when database connection fails."""
    from packages.common.db_schema import create_schema

    # Mock connection failure
    mocker.patch(
        "packages.common.db_schema._get_connection",
        side_effect=ConnectionError("Connection refused"),
    )

    # Should raise ConnectionError
    with pytest.raises(ConnectionError):
        create_schema(test_config)


@pytest.mark.unit
def test_verify_schema_returns_table_list(test_config: TabootConfig, mocker: Any) -> None:
    """Test that verify_schema returns list of existing tables."""
    from packages.common.db_schema import verify_schema

    # Mock connection and cursor
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchall.return_value = [
        ("documents",),
        ("extraction_windows",),
        ("ingestion_jobs",),
    ]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)

    # Verify schema
    tables = verify_schema(test_config)

    # Should return dict of schema tables
    assert isinstance(tables, dict)
    assert "rag" in tables
    assert len(tables["rag"]) == 3
    assert "documents" in tables["rag"]
    assert "extraction_windows" in tables["rag"]
    assert "ingestion_jobs" in tables["rag"]


@pytest.mark.unit
def test_verify_schema_query_structure(test_config: TabootConfig, mocker: Any) -> None:
    """Test that verify_schema uses correct SQL query."""
    from packages.common.db_schema import verify_schema

    # Mock connection and cursor
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)

    # Verify schema
    verify_schema(test_config)

    # Check that execute was called with information_schema query
    execute_call = mock_cursor.execute.call_args[0][0]
    assert "information_schema.tables" in execute_call.lower()
    assert "table_schema in ('rag', 'auth')" in execute_call.lower() or "table_schema = 'rag'" in execute_call.lower()


@pytest.mark.integration
def test_document_content_table_exists() -> None:
    """Test that document_content table is created in schema."""
    # Ensure schema is created
    # This is async but we need to run it synchronously for this test
    import asyncio

    from packages.common.db_schema import create_postgresql_schema, get_postgres_client

    asyncio.run(create_postgresql_schema())

    conn = get_postgres_client()
    with conn.cursor() as cur:
        # Check table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'document_content'
            );
        """)
        result = cur.fetchone()
        assert result[0] is True

        # Check required columns exist
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'document_content'
        """)
        columns = {row[0] for row in cur.fetchall()}

        assert "doc_id" in columns
        assert "content" in columns
        assert "created_at" in columns

    conn.close()


# Version Tracking Tests


@pytest.mark.unit
def test_get_schema_checksum() -> None:
    """Test checksum calculation for schema SQL content."""
    from packages.common.db_schema import get_schema_checksum

    sql = "CREATE TABLE test (id INT PRIMARY KEY);"
    checksum = get_schema_checksum(sql)

    # Checksum should be 64-character hex string (SHA-256)
    assert isinstance(checksum, str)
    assert len(checksum) == 64
    assert all(c in "0123456789abcdef" for c in checksum)

    # Same content should produce same checksum
    checksum2 = get_schema_checksum(sql)
    assert checksum == checksum2

    # Different content should produce different checksum
    sql_modified = "CREATE TABLE test (id INT PRIMARY KEY, name TEXT);"
    checksum3 = get_schema_checksum(sql_modified)
    assert checksum != checksum3


@pytest.mark.unit
def test_extract_schema_version_success() -> None:
    """Test extraction of version from schema SQL comment."""
    from packages.common.db_schema import extract_schema_version

    sql = "-- THIS VERSION: 1.0.0\nCREATE TABLE test (id INT);"
    version = extract_schema_version(sql)
    assert version == "1.0.0"

    # Test with different formats
    sql2 = "-- this version: 2.0.0\nCREATE TABLE test (id INT);"
    assert extract_schema_version(sql2) == "2.0.0"

    sql3 = "--   THIS   VERSION:   1.5.3   \nCREATE TABLE test (id INT);"
    assert extract_schema_version(sql3) == "1.5.3"


@pytest.mark.unit
def test_extract_schema_version_not_found() -> None:
    """Test extraction when version comment is missing."""
    from packages.common.db_schema import extract_schema_version

    sql_no_version = "CREATE TABLE test (id INT);"
    version = extract_schema_version(sql_no_version)
    assert version is None


@pytest.mark.unit
def test_get_current_version_success(mocker: Any) -> None:
    """Test retrieving current version from database."""
    from packages.common.db_schema import get_current_version

    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = ("1.0.0",)

    version = get_current_version(mock_cursor)
    assert version == "1.0.0"

    # Verify SQL query structure
    execute_call = mock_cursor.execute.call_args[0][0]
    assert "SELECT version FROM schema_versions" in execute_call
    assert "WHERE status = 'success'" in execute_call
    assert "ORDER BY applied_at DESC LIMIT 1" in execute_call


@pytest.mark.unit
def test_get_current_version_no_version(mocker: Any) -> None:
    """Test retrieving current version when no version exists."""
    from packages.common.db_schema import get_current_version

    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = None

    version = get_current_version(mock_cursor)
    assert version is None


@pytest.mark.unit
def test_get_current_version_table_not_exists(mocker: Any) -> None:
    """Test retrieving current version when schema_versions table doesn't exist."""
    from packages.common.db_schema import get_current_version

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute.side_effect = Exception("relation does not exist")

    version = get_current_version(mock_cursor)
    assert version is None


@pytest.mark.unit
def test_create_schema_version_tracking(test_config: TabootConfig, mocker: Any) -> None:
    """Test that create_schema records version metadata."""
    from packages.common.db_schema import create_schema

    # Mock connection and cursor
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)

    # Mock schema file with version
    mock_sql = "-- THIS VERSION: 2.0.0\nCREATE TABLE test (id INT);"
    mocker.patch("packages.common.db_schema.load_schema_file", return_value=mock_sql)

    # Mock get_current_version to return None (first run)
    mocker.patch("packages.common.db_schema.get_current_version", return_value=None)

    # Execute schema creation
    create_schema(test_config)

    # Verify version was recorded
    execute_calls = [call[0][0] for call in mock_cursor.execute.call_args_list]

    # Should have INSERT for version tracking
    version_insert = any("INSERT INTO schema_versions" in call for call in execute_calls)
    assert version_insert, "Version metadata should be recorded"

    # Should have committed
    mock_conn.commit.assert_called()


@pytest.mark.unit
def test_create_schema_version_mismatch_warning(
    test_config: TabootConfig, mocker: Any, caplog: Any
) -> None:
    """Test warning when file version differs from constant."""
    from packages.common.db_schema import CURRENT_SCHEMA_VERSION, create_schema

    # Mock connection and cursor
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)

    # Mock schema file with different version than constant
    different_version = "99.99.99"
    mock_sql = f"-- THIS VERSION: {different_version}\nCREATE TABLE test (id INT);"
    mocker.patch("packages.common.db_schema.load_schema_file", return_value=mock_sql)

    # Mock get_current_version to return None
    mocker.patch("packages.common.db_schema.get_current_version", return_value=None)

    # Execute schema creation
    with caplog.at_level(logging.WARNING):
        create_schema(test_config)

    # Should log warning about version mismatch
    assert any("version mismatch" in record.message.lower() for record in caplog.records)


@pytest.mark.unit
def test_create_schema_checksum_mismatch_warning(
    test_config: TabootConfig, mocker: Any, caplog: Any
) -> None:
    """Test warning when checksum differs but version matches."""
    from packages.common.db_schema import create_schema

    # Mock connection and cursor
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = ("old_checksum_value",)
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)

    # Mock schema file
    mock_sql = "-- THIS VERSION: 2.0.0\nCREATE TABLE test (id INT);"
    mocker.patch("packages.common.db_schema.load_schema_file", return_value=mock_sql)

    # Mock get_current_version to return same version as file
    mocker.patch("packages.common.db_schema.get_current_version", return_value="2.0.0")

    # Execute schema creation
    with caplog.at_level(logging.WARNING):
        create_schema(test_config)

    # Should log warning about checksum mismatch
    assert any("checksum mismatch" in record.message.lower() for record in caplog.records)


@pytest.mark.unit
def test_create_schema_skips_if_version_and_checksum_match(
    test_config: TabootConfig, mocker: Any, caplog: Any
) -> None:
    """Test that schema creation is skipped if version and checksum match."""
    from packages.common.db_schema import create_schema, get_schema_checksum

    # Mock connection and cursor
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)

    # Mock schema file
    mock_sql = "-- THIS VERSION: 2.0.0\nCREATE TABLE test (id INT);"
    mocker.patch("packages.common.db_schema.load_schema_file", return_value=mock_sql)

    # Calculate actual checksum
    actual_checksum = get_schema_checksum(mock_sql)

    # Mock get_current_version to return same version
    mocker.patch("packages.common.db_schema.get_current_version", return_value="2.0.0")

    # Mock fetchone to return matching checksum
    mock_cursor.fetchone.return_value = (actual_checksum,)

    # Execute schema creation
    with caplog.at_level(logging.INFO):
        create_schema(test_config)

    # Should log that schema was skipped
    assert any("skipping" in record.message.lower() for record in caplog.records)

    # Should NOT execute schema SQL (only checksum query)
    execute_calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
    assert len(execute_calls) == 1  # Only checksum query, no schema execution


@pytest.mark.unit
def test_create_schema_missing_version_raises_error(test_config: TabootConfig, mocker: Any) -> None:
    """Test that missing THIS VERSION comment raises ValueError."""
    from packages.common.db_schema import create_schema

    # Mock schema file without version
    mock_sql = "CREATE TABLE test (id INT);"
    mocker.patch("packages.common.db_schema.load_schema_file", return_value=mock_sql)

    # Should raise ValueError
    with pytest.raises(ValueError, match="missing THIS VERSION comment"):
        create_schema(test_config)


@pytest.mark.unit
def test_create_schema_records_failure_on_error(test_config: TabootConfig, mocker: Any) -> None:
    """Test that failed schema application is recorded."""
    from packages.common.db_schema import create_schema

    # Mock connection and cursor
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_cursor.execute.side_effect = [None, Exception("SQL error")]  # First call for check, second for execution
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mocker.patch("packages.common.db_schema._get_connection", return_value=mock_conn)

    # Mock schema file
    mock_sql = "-- THIS VERSION: 2.0.0\nINVALID SQL;"
    mocker.patch("packages.common.db_schema.load_schema_file", return_value=mock_sql)

    # Mock get_current_version to return None
    mocker.patch("packages.common.db_schema.get_current_version", return_value=None)

    # Should raise RuntimeError
    with pytest.raises(RuntimeError):
        create_schema(test_config)

    # Should have rolled back
    mock_conn.rollback.assert_called()


@pytest.mark.integration
def test_schema_versions_table_created() -> None:
    """Test that schema_versions table is created in schema."""
    import asyncio

    from packages.common.db_schema import create_postgresql_schema, get_postgres_client

    asyncio.run(create_postgresql_schema())

    conn = get_postgres_client()
    with conn.cursor() as cur:
        # Check table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'schema_versions'
            );
        """)
        result = cur.fetchone()
        assert result[0] is True

        # Check required columns exist
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'schema_versions'
        """)
        columns = {row[0] for row in cur.fetchall()}

        assert "version" in columns
        assert "applied_at" in columns
        assert "applied_by" in columns
        assert "description" in columns
        assert "checksum" in columns
        assert "execution_time_ms" in columns
        assert "status" in columns

    conn.close()


@pytest.mark.integration
def test_version_recorded_after_schema_creation() -> None:
    """Test that version is recorded after successful schema creation."""
    import asyncio

    from packages.common.db_schema import CURRENT_SCHEMA_VERSION, create_postgresql_schema, get_postgres_client

    asyncio.run(create_postgresql_schema())

    conn = get_postgres_client()
    with conn.cursor() as cur:
        # Check version was recorded
        cur.execute("""
            SELECT version, status, checksum
            FROM schema_versions
            WHERE status = 'success'
            ORDER BY applied_at DESC
            LIMIT 1
        """)
        result = cur.fetchone()

        assert result is not None
        version, status, checksum = result

        # Should match CURRENT_SCHEMA_VERSION constant
        assert version == CURRENT_SCHEMA_VERSION
        assert status == "success"
        assert len(checksum) == 64  # SHA-256 hex digest

    conn.close()
