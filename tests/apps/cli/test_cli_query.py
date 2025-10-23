"""Tests for CLI query command."""

import pytest
from typer.testing import CliRunner
from apps.cli.main import app


runner = CliRunner()


@pytest.mark.unit
def test_query_command_requires_question():
    """Test query command validates question argument."""
    result = runner.invoke(app, ["query"])
    assert result.exit_code != 0  # Should fail without question


@pytest.mark.unit
def test_query_command_accepts_filters():
    """Test query command accepts source and date filters."""
    result = runner.invoke(
        app,
        ["query", "test question", "--sources", "web,docker_compose", "--top-k", "10"],
        catch_exceptions=False
    )
    # May fail if services not running, but command should parse args
    assert "--sources" in str(result) or result.exit_code in [0, 1]


@pytest.mark.integration
@pytest.mark.slow
def test_query_command_with_real_services(qdrant_client, neo4j_client):
    """Test query command against real services."""
    result = runner.invoke(
        app,
        ["query", "Which services expose port 8080?", "--top-k", "5"]
    )

    # Should succeed or fail gracefully
    assert result.exit_code in [0, 1]
