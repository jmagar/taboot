"""Tests for PostgreSQL client connection."""

import pytest
from packages.common.db_schema import get_postgres_client


def test_get_postgres_client_returns_connection():
    """Test that get_postgres_client returns a valid connection."""
    conn = get_postgres_client()

    assert conn is not None

    # Verify connection is active
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        result = cur.fetchone()
        assert result[0] == 1

    conn.close()


def test_get_postgres_client_connection_has_dict_cursor():
    """Test that connection uses RealDictCursor for dict results."""
    conn = get_postgres_client()

    # Should be able to access results as dict
    with conn.cursor() as cur:
        cur.execute("SELECT 1 as test_value")
        result = cur.fetchone()
        assert result['test_value'] == 1

    conn.close()
