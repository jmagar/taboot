"""Unit tests for PostgreSQL schema creation.

Tests the db_schema module for loading and executing SQL schema files.
Following TDD methodology - these tests should fail until T024 implements db_schema.py.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

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
    assert "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"" in sql_content


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
    mock_sql = """
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
    mock_sql = """
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
    mock_sql = """
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

    # Should raise Exception on SQL error
    with pytest.raises(Exception):
        create_schema(test_config)

    # Connection should be rolled back on error
    mock_conn.rollback.assert_called_once()


@pytest.mark.unit
def test_create_schema_connection_error(test_config: TabootConfig, mocker: Any) -> None:
    """Test error handling when database connection fails."""
    from packages.common.db_schema import create_schema

    # Mock connection failure
    mocker.patch("packages.common.db_schema._get_connection", side_effect=ConnectionError("Connection refused"))

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

    # Should return list of table names
    assert isinstance(tables, list)
    assert len(tables) == 3
    assert "documents" in tables
    assert "extraction_windows" in tables
    assert "ingestion_jobs" in tables


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
    assert "table_schema = 'public'" in execute_call.lower()


@pytest.mark.integration
def test_document_content_table_exists():
    """Test that document_content table is created in schema."""
    from packages.common.db_schema import create_postgresql_schema, get_postgres_client

    # Ensure schema is created
    # This is async but we need to run it synchronously for this test
    import asyncio
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

        assert 'doc_id' in columns
        assert 'content' in columns
        assert 'created_at' in columns

    conn.close()
