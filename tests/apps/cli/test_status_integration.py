"""Integration tests for CLI status command.

Tests status command against real Docker services.
"""

import pytest
from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


@pytest.mark.integration
@pytest.mark.slow
def test_status_command_with_real_services(docker_services_ready):
    """Test status command against real running Docker services.

    This test requires Docker services to be running:
    - docker compose up -d

    Verifies:
    - Command executes without errors
    - Shows service health status
    - Displays all expected services
    """
    result = runner.invoke(app, ["status"])

    # Command should execute (exit 0 if all healthy, 1 if any unhealthy)
    assert result.exit_code in [0, 1]

    # Should show all services in output
    assert "neo4j" in result.stdout.lower()
    assert "qdrant" in result.stdout.lower()
    assert "redis" in result.stdout.lower()
    assert "tei" in result.stdout.lower()
    assert "ollama" in result.stdout.lower()
    assert "firecrawl" in result.stdout.lower()
    assert "playwright" in result.stdout.lower()

    # Should show status indicators
    assert "✓" in result.stdout or "✗" in result.stdout

    # Should show table header
    assert "service health" in result.stdout.lower()


@pytest.mark.integration
@pytest.mark.slow
def test_status_command_component_filter_with_real_services(docker_services_ready):
    """Test status command component filtering with real services."""
    result = runner.invoke(app, ["status", "--component", "neo4j"])

    # Should succeed or fail based on Neo4j health
    assert result.exit_code in [0, 1]

    # Should only show neo4j
    assert "neo4j" in result.stdout.lower()

    # Should not show other services
    output_lines = result.stdout.lower()
    # Check that qdrant appears less frequently than neo4j (not in table rows)
    assert output_lines.count("neo4j") > output_lines.count("qdrant")


@pytest.mark.integration
@pytest.mark.slow
def test_status_command_verbose_with_real_services(docker_services_ready):
    """Test status command verbose mode with real services."""
    result = runner.invoke(app, ["status", "--verbose"])

    # Should succeed or fail based on overall health
    assert result.exit_code in [0, 1]

    # Should show details column
    assert "details" in result.stdout.lower()

    # Should show connection info
    assert "connected" in result.stdout.lower() or "disconnected" in result.stdout.lower()


@pytest.mark.integration
@pytest.mark.slow
def test_status_command_handles_unhealthy_services_gracefully(docker_services_ready):
    """Test status command handles mix of healthy and unhealthy services.

    Note: This test verifies graceful handling even when some services
    might be down or unavailable.
    """
    result = runner.invoke(app, ["status"])

    # Should always execute without crashing
    assert result.exit_code in [0, 1]

    # If exit code is 1, should show which services are unavailable
    if result.exit_code == 1:
        assert "unavailable" in result.stdout.lower() or "✗" in result.stdout


@pytest.mark.integration
@pytest.mark.slow
def test_status_command_invalid_component_with_real_services(docker_services_ready):
    """Test status command with invalid component name."""
    result = runner.invoke(app, ["status", "--component", "nonexistent"])

    # Should fail with error
    assert result.exit_code == 1
    assert "unknown component" in result.stdout.lower()
