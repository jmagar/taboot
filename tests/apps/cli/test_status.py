"""Tests for CLI status command (top-level, not extract status).

TDD: Tests for real health check integration.
"""

from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


@pytest.mark.unit
def test_status_command_exists() -> None:
    """Test that status command is callable and not NotImplementedError."""
    with patch(
        "apps.cli.commands.status.check_system_health", new_callable=AsyncMock
    ) as mock_health:
        mock_health.return_value = {
            "healthy": True,
            "services": {
                "neo4j": True,
                "qdrant": True,
                "redis": True,
                "tei": True,
                "ollama": True,
                "firecrawl": True,
                "playwright": True,
            },
        }

        result = runner.invoke(app, ["status"])

        assert "NotImplementedError" not in result.stdout
        assert result.exit_code == 0


@pytest.mark.unit
def test_status_command_uses_real_health_checks() -> None:
    """Test status command calls real health check functions."""
    with patch(
        "apps.cli.commands.status.check_system_health", new_callable=AsyncMock
    ) as mock_health:
        mock_health.return_value = {
            "healthy": True,
            "services": {
                "neo4j": True,
                "qdrant": True,
                "redis": True,
                "tei": True,
                "ollama": True,
                "firecrawl": True,
                "playwright": True,
            },
        }

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        mock_health.assert_called_once()
        assert "neo4j" in result.stdout.lower()
        assert "qdrant" in result.stdout.lower()


@pytest.mark.unit
def test_status_command_with_component_filter() -> None:
    """Test status command with --component flag filters output."""
    with patch(
        "apps.cli.commands.status.check_system_health", new_callable=AsyncMock
    ) as mock_health:
        mock_health.return_value = {
            "healthy": True,
            "services": {"neo4j": True, "qdrant": True, "redis": True},
        }

        result = runner.invoke(app, ["status", "--component", "neo4j"])

        assert result.exit_code == 0
        assert "neo4j" in result.stdout.lower()
        # Component filter should only show neo4j
        assert "qdrant" not in result.stdout.lower()


@pytest.mark.unit
def test_status_command_with_verbose_flag() -> None:
    """Test status command with --verbose shows detailed info."""
    with patch(
        "apps.cli.commands.status.check_system_health", new_callable=AsyncMock
    ) as mock_health:
        mock_health.return_value = {"healthy": True, "services": {"neo4j": True}}

        result = runner.invoke(app, ["status", "--verbose"])

        assert result.exit_code == 0
        # Verbose should show details column
        assert "details" in result.stdout.lower()


@pytest.mark.unit
def test_status_command_handles_unhealthy_service() -> None:
    """Test status command displays unhealthy services with error messages."""
    with patch(
        "apps.cli.commands.status.check_system_health", new_callable=AsyncMock
    ) as mock_health:
        mock_health.return_value = {"healthy": False, "services": {"neo4j": False, "qdrant": True}}

        result = runner.invoke(app, ["status"])

        # Should exit with error if any service unhealthy
        assert result.exit_code == 1
        assert "neo4j" in result.stdout.lower()
        assert "unavailable" in result.stdout.lower()


@pytest.mark.unit
def test_status_command_handles_errors_gracefully() -> None:
    """Test status command handles exceptions during status check."""
    with patch(
        "apps.cli.commands.status.check_system_health", new_callable=AsyncMock
    ) as mock_health:
        mock_health.side_effect = Exception("Status check failed")

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


@pytest.mark.integration
@pytest.mark.slow
def test_status_command_with_real_services() -> None:
    """Test status command against real running services.

    Note: Requires services running. May fail if services unavailable.
    """
    result = runner.invoke(app, ["status"])

    # Should succeed or fail gracefully
    assert result.exit_code in [0, 1]
    if result.exit_code == 0:
        # Should show at least some service names
        assert "neo4j" in result.stdout.lower() or "qdrant" in result.stdout.lower()
