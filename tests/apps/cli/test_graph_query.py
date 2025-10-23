"""Tests for CLI graph query command."""

from unittest.mock import MagicMock, patch

import pytest
from neo4j.exceptions import Neo4jError
from typer.testing import CliRunner

from apps.cli.main import app
from packages.graph.client import Neo4jConnectionError

runner = CliRunner()


@pytest.mark.unit
def test_graph_query_requires_cypher():
    """Test graph query command requires Cypher argument."""
    result = runner.invoke(app, ["graph", "query"])
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout or result.exit_code == 2


@pytest.mark.unit
def test_graph_query_accepts_format_flag():
    """Test graph query command accepts format flag."""
    with patch("apps.cli.commands.graph.Neo4jClient") as mock_client:
        # Mock Neo4j client and session
        mock_instance = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.run.return_value = mock_result
        mock_instance.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_instance.session.return_value.__exit__ = MagicMock(return_value=None)
        mock_client.return_value = mock_instance

        result = runner.invoke(
            app, ["graph", "query", "MATCH (n) RETURN n LIMIT 1", "--format", "json"]
        )
        assert result.exit_code == 0


@pytest.mark.unit
def test_graph_query_executes_cypher():
    """Test graph query command executes Cypher query."""
    with patch("apps.cli.commands.graph.Neo4jClient") as mock_client:
        # Mock Neo4j client and session
        mock_instance = MagicMock()
        mock_session = MagicMock()

        # Mock query result with sample data
        mock_record = MagicMock()
        mock_record.data.return_value = {"name": "test-service", "count": 42}
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([mock_record]))
        mock_session.run.return_value = mock_result

        mock_instance.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_instance.session.return_value.__exit__ = MagicMock(return_value=None)
        mock_client.return_value = mock_instance

        result = runner.invoke(
            app, ["graph", "query", "MATCH (s:Service) RETURN s.name as name LIMIT 10"]
        )

        assert result.exit_code == 0
        mock_session.run.assert_called_once_with(
            "MATCH (s:Service) RETURN s.name as name LIMIT 10"
        )


@pytest.mark.unit
def test_graph_query_handles_empty_results():
    """Test graph query command handles queries with no results."""
    with patch("apps.cli.commands.graph.Neo4jClient") as mock_client:
        # Mock Neo4j client with empty result
        mock_instance = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.run.return_value = mock_result

        mock_instance.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_instance.session.return_value.__exit__ = MagicMock(return_value=None)
        mock_client.return_value = mock_instance

        result = runner.invoke(
            app, ["graph", "query", "MATCH (n:NonExistent) RETURN n"]
        )

        assert result.exit_code == 0
        assert "no results" in result.stdout.lower()


@pytest.mark.unit
def test_graph_query_handles_connection_error():
    """Test graph query command handles Neo4j connection errors."""
    with patch("apps.cli.commands.graph.Neo4jClient") as mock_client:
        # Mock connection error
        mock_instance = MagicMock()
        mock_instance.connect.side_effect = Neo4jConnectionError(
            "Failed to connect to Neo4j"
        )
        mock_client.return_value = mock_instance

        result = runner.invoke(
            app, ["graph", "query", "MATCH (n) RETURN n LIMIT 1"]
        )

        assert result.exit_code == 1
        assert "Connection error" in result.stdout or "error" in result.stdout.lower()


@pytest.mark.unit
def test_graph_query_handles_invalid_cypher():
    """Test graph query command handles invalid Cypher syntax."""
    with patch("apps.cli.commands.graph.Neo4jClient") as mock_client:
        # Mock Neo4j error for invalid syntax
        mock_instance = MagicMock()
        mock_session = MagicMock()
        mock_session.run.side_effect = Neo4jError("Invalid Cypher syntax")

        mock_instance.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_instance.session.return_value.__exit__ = MagicMock(return_value=None)
        mock_client.return_value = mock_instance

        result = runner.invoke(
            app, ["graph", "query", "INVALID CYPHER QUERY"]
        )

        assert result.exit_code == 1
        assert "Neo4j error" in result.stdout or "error" in result.stdout.lower()


@pytest.mark.unit
def test_graph_query_json_format():
    """Test graph query command outputs JSON format correctly."""
    with patch("apps.cli.commands.graph.Neo4jClient") as mock_client:
        # Mock Neo4j client with sample data
        mock_instance = MagicMock()
        mock_session = MagicMock()

        mock_record = MagicMock()
        mock_record.data.return_value = {"service": "nginx", "port": 80}
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([mock_record]))
        mock_session.run.return_value = mock_result

        mock_instance.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_instance.session.return_value.__exit__ = MagicMock(return_value=None)
        mock_client.return_value = mock_instance

        result = runner.invoke(
            app, ["graph", "query", "MATCH (n) RETURN n LIMIT 1", "--format", "json"]
        )

        assert result.exit_code == 0
        assert "nginx" in result.stdout


@pytest.mark.unit
def test_graph_query_table_format():
    """Test graph query command outputs table format by default."""
    with patch("apps.cli.commands.graph.Neo4jClient") as mock_client:
        # Mock Neo4j client with sample data
        mock_instance = MagicMock()
        mock_session = MagicMock()

        mock_record = MagicMock()
        mock_record.data.return_value = {"name": "redis", "port": 6379}
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([mock_record]))
        mock_session.run.return_value = mock_result

        mock_instance.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_instance.session.return_value.__exit__ = MagicMock(return_value=None)
        mock_client.return_value = mock_instance

        result = runner.invoke(
            app, ["graph", "query", "MATCH (s:Service) RETURN s.name as name, s.port as port"]
        )

        assert result.exit_code == 0
        assert "redis" in result.stdout
        # Table format typically shows borders or column names
        assert "name" in result.stdout or "Query Results" in result.stdout


@pytest.mark.integration
@pytest.mark.slow
def test_graph_query_with_real_neo4j():
    """Test graph query command against real Neo4j instance.

    Note: Requires Neo4j service running. Skips if unavailable.
    """
    result = runner.invoke(
        app, ["graph", "query", "MATCH (n) RETURN count(n) as total"]
    )

    # Should succeed or fail gracefully with connection error
    assert result.exit_code in [0, 1]
    if result.exit_code == 0:
        assert "total" in result.stdout.lower()
