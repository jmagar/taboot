"""Integration tests for CLI graph query command.

Tests graph query command against real Neo4j.
"""

import pytest
from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


@pytest.mark.integration
@pytest.mark.slow
def test_graph_query_with_real_neo4j(docker_services_ready) -> None:
    """Test graph query command against real Neo4j instance.

    Requires: docker compose up -d (Neo4j service running)

    Verifies:
    - Can connect to Neo4j
    - Can execute basic Cypher queries
    - Returns results in table format
    """
    # Simple count query that works on any Neo4j instance
    result = runner.invoke(app, ["graph", "query", "RETURN 1 as value"])

    # Should succeed
    assert result.exit_code == 0

    # Should show result
    assert "value" in result.stdout or "1" in result.stdout

    # Should show table formatting
    assert "query results" in result.stdout.lower() or "returned" in result.stdout.lower()


@pytest.mark.integration
@pytest.mark.slow
def test_graph_query_node_count_with_real_neo4j(docker_services_ready) -> None:
    """Test counting nodes in Neo4j graph."""
    result = runner.invoke(app, ["graph", "query", "MATCH (n) RETURN count(n) as total"])

    # Should succeed
    assert result.exit_code == 0

    # Should show total count
    assert "total" in result.stdout.lower()

    # Should show numeric result
    import re

    assert re.search(r"\d+", result.stdout), "Should contain numeric count"


@pytest.mark.integration
@pytest.mark.slow
def test_graph_query_json_format_with_real_neo4j(docker_services_ready) -> None:
    """Test graph query with JSON output format."""
    result = runner.invoke(app, ["graph", "query", "RETURN 42 as answer", "--format", "json"])

    # Should succeed
    assert result.exit_code == 0

    # Should be valid JSON-like output
    assert "42" in result.stdout
    assert "answer" in result.stdout


@pytest.mark.integration
@pytest.mark.slow
def test_graph_query_invalid_cypher_with_real_neo4j(docker_services_ready) -> None:
    """Test graph query with invalid Cypher syntax."""
    result = runner.invoke(app, ["graph", "query", "INVALID CYPHER SYNTAX HERE"])

    # Should fail gracefully
    assert result.exit_code == 1

    # Should show error message
    assert "error" in result.stdout.lower()


@pytest.mark.integration
@pytest.mark.slow
def test_graph_query_empty_result_with_real_neo4j(docker_services_ready) -> None:
    """Test graph query that returns no results."""
    result = runner.invoke(app, ["graph", "query", "MATCH (n:NonExistentLabel) RETURN n"])

    # Should succeed but show no results
    assert result.exit_code == 0
    assert "no results" in result.stdout.lower()


@pytest.mark.integration
@pytest.mark.slow
def test_graph_query_multiple_columns_with_real_neo4j(docker_services_ready) -> None:
    """Test graph query returning multiple columns."""
    result = runner.invoke(
        app, ["graph", "query", "RETURN 'test' as name, 123 as count, true as active"]
    )

    # Should succeed
    assert result.exit_code == 0

    # Should show all columns
    assert "name" in result.stdout.lower()
    assert "count" in result.stdout.lower()
    assert "active" in result.stdout.lower()

    # Should show values
    assert "test" in result.stdout
    assert "123" in result.stdout


@pytest.mark.integration
@pytest.mark.slow
def test_graph_query_with_parameters_simulation(docker_services_ready) -> None:
    """Test graph query with inline values (parameter simulation).

    Note: CLI doesn't support parameterized queries yet, but tests inline values.
    """
    result = runner.invoke(app, ["graph", "query", "RETURN 'Service' as type, 'example' as name"])

    # Should succeed
    assert result.exit_code == 0

    # Should show inline values
    assert "service" in result.stdout.lower()
    assert "example" in result.stdout.lower()
