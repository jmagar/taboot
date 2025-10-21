"""Tests for init CLI command (T025).

Following TDD: Write failing tests first (RED), then implement to pass (GREEN).

The init command should orchestrate:
1. Neo4j constraint creation (packages/graph/constraints.py)
2. Qdrant collection creation (packages/vector/collections.py)
3. PostgreSQL schema creation (packages/common/db_schema.py)
4. Service health verification before proceeding
5. Proper error handling and reporting
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from apps.cli.main import app


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide Typer CLI test runner.

    Returns:
        CliRunner: Typer test runner instance.
    """
    return CliRunner()


@pytest.mark.unit
class TestInitCommand:
    """Test init CLI command orchestration."""

    def test_init_command_exists(self, cli_runner: CliRunner) -> None:
        """Test that init command is registered in the CLI."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.stdout

    @patch("apps.cli.commands.init.check_system_health")
    @patch("apps.cli.commands.init.create_neo4j_constraints")
    @patch("apps.cli.commands.init.create_qdrant_collections")
    @patch("apps.cli.commands.init.create_postgresql_schema")
    def test_init_calls_all_initialization_functions(
        self,
        mock_create_postgresql: MagicMock,
        mock_create_qdrant: MagicMock,
        mock_create_neo4j: MagicMock,
        mock_check_health: AsyncMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that init command calls all initialization functions in correct order.

        Expected flow:
        1. Check system health
        2. Create Neo4j constraints
        3. Create Qdrant collections
        4. Create PostgreSQL schema
        5. Report success
        """
        # Mock health check to return all services healthy
        mock_check_health.return_value = {
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

        # All initialization functions succeed
        mock_create_neo4j.return_value = None
        mock_create_qdrant.return_value = None
        mock_create_postgresql.return_value = None

        result = cli_runner.invoke(app, ["init"])

        # Verify exit code
        assert result.exit_code == 0

        # Verify all functions were called
        mock_check_health.assert_called_once()
        mock_create_neo4j.assert_called_once()
        mock_create_qdrant.assert_called_once()
        mock_create_postgresql.assert_called_once()

        # Verify success message
        assert "success" in result.stdout.lower() or "initialized" in result.stdout.lower()

    @patch("apps.cli.commands.init.check_system_health")
    def test_init_checks_health_before_proceeding(
        self, mock_check_health: AsyncMock, cli_runner: CliRunner
    ) -> None:
        """Test that init command verifies service health before proceeding."""
        # Mock health check to return all services healthy
        mock_check_health.return_value = {
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

        with patch("apps.cli.commands.init.create_neo4j_constraints"):
            with patch("apps.cli.commands.init.create_qdrant_collections"):
                with patch("apps.cli.commands.init.create_postgresql_schema"):
                    result = cli_runner.invoke(app, ["init"])

                    # Health check should be called first
                    mock_check_health.assert_called_once()
                    assert result.exit_code == 0

    @patch("apps.cli.commands.init.check_system_health")
    def test_init_fails_when_services_unhealthy(
        self, mock_check_health: AsyncMock, cli_runner: CliRunner
    ) -> None:
        """Test that init command fails and reports error when services are unhealthy."""
        # Mock health check to return some services unhealthy
        mock_check_health.return_value = {
            "healthy": False,
            "services": {
                "neo4j": True,
                "qdrant": False,  # Qdrant is down
                "redis": True,
                "tei": False,  # TEI is down
                "ollama": True,
                "firecrawl": True,
                "playwright": True,
            },
        }

        result = cli_runner.invoke(app, ["init"])

        # Should fail with non-zero exit code
        assert result.exit_code != 0

        # Should report which services are unhealthy
        assert "unhealthy" in result.stdout.lower() or "failed" in result.stdout.lower()

        # Should mention the failed services
        output_lower = result.stdout.lower()
        assert "qdrant" in output_lower or "tei" in output_lower

    @patch("apps.cli.commands.init.check_system_health")
    @patch("apps.cli.commands.init.create_neo4j_constraints")
    @patch("apps.cli.commands.init.create_qdrant_collections")
    @patch("apps.cli.commands.init.create_postgresql_schema")
    def test_init_handles_neo4j_constraint_failure(
        self,
        mock_create_postgresql: MagicMock,
        mock_create_qdrant: MagicMock,
        mock_create_neo4j: MagicMock,
        mock_check_health: AsyncMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that init command handles Neo4j constraint creation failure gracefully."""
        # Mock health check to succeed
        mock_check_health.return_value = {
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

        # Mock Neo4j constraint creation to fail
        mock_create_neo4j.side_effect = Exception("Neo4j constraint creation failed")

        result = cli_runner.invoke(app, ["init"])

        # Should fail with non-zero exit code
        assert result.exit_code != 0

        # Should report the error
        assert "error" in result.stdout.lower() or "failed" in result.stdout.lower()
        assert "neo4j" in result.stdout.lower()

    @patch("apps.cli.commands.init.check_system_health")
    @patch("apps.cli.commands.init.create_neo4j_constraints")
    @patch("apps.cli.commands.init.create_qdrant_collections")
    @patch("apps.cli.commands.init.create_postgresql_schema")
    def test_init_handles_qdrant_collection_failure(
        self,
        mock_create_postgresql: MagicMock,
        mock_create_qdrant: MagicMock,
        mock_create_neo4j: MagicMock,
        mock_check_health: AsyncMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that init command handles Qdrant collection creation failure gracefully."""
        # Mock health check to succeed
        mock_check_health.return_value = {
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

        # Neo4j succeeds
        mock_create_neo4j.return_value = None

        # Mock Qdrant collection creation to fail
        mock_create_qdrant.side_effect = Exception("Qdrant collection creation failed")

        result = cli_runner.invoke(app, ["init"])

        # Should fail with non-zero exit code
        assert result.exit_code != 0

        # Should report the error
        assert "error" in result.stdout.lower() or "failed" in result.stdout.lower()
        assert "qdrant" in result.stdout.lower()

    @patch("apps.cli.commands.init.check_system_health")
    @patch("apps.cli.commands.init.create_neo4j_constraints")
    @patch("apps.cli.commands.init.create_qdrant_collections")
    @patch("apps.cli.commands.init.create_postgresql_schema")
    def test_init_handles_postgresql_schema_failure(
        self,
        mock_create_postgresql: MagicMock,
        mock_create_qdrant: MagicMock,
        mock_create_neo4j: MagicMock,
        mock_check_health: AsyncMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that init command handles PostgreSQL schema creation failure gracefully."""
        # Mock health check to succeed
        mock_check_health.return_value = {
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

        # Neo4j and Qdrant succeed
        mock_create_neo4j.return_value = None
        mock_create_qdrant.return_value = None

        # Mock PostgreSQL schema creation to fail
        mock_create_postgresql.side_effect = Exception("PostgreSQL schema creation failed")

        result = cli_runner.invoke(app, ["init"])

        # Should fail with non-zero exit code
        assert result.exit_code != 0

        # Should report the error
        assert "error" in result.stdout.lower() or "failed" in result.stdout.lower()
        assert "postgresql" in result.stdout.lower() or "schema" in result.stdout.lower()

    @patch("apps.cli.commands.init.check_system_health")
    @patch("apps.cli.commands.init.create_neo4j_constraints")
    @patch("apps.cli.commands.init.create_qdrant_collections")
    @patch("apps.cli.commands.init.create_postgresql_schema")
    def test_init_reports_success_correctly(
        self,
        mock_create_postgresql: MagicMock,
        mock_create_qdrant: MagicMock,
        mock_create_neo4j: MagicMock,
        mock_check_health: AsyncMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that init command reports success with appropriate messaging."""
        # Mock all operations to succeed
        mock_check_health.return_value = {
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
        mock_create_neo4j.return_value = None
        mock_create_qdrant.return_value = None
        mock_create_postgresql.return_value = None

        result = cli_runner.invoke(app, ["init"])

        # Should succeed
        assert result.exit_code == 0

        # Should contain success indicators
        output_lower = result.stdout.lower()
        assert (
            "success" in output_lower
            or "initialized" in output_lower
            or "complete" in output_lower
        )

        # Should mention key components that were initialized
        assert "neo4j" in output_lower or "constraints" in output_lower
        assert "qdrant" in output_lower or "collection" in output_lower

    def test_init_command_no_arguments_required(self, cli_runner: CliRunner) -> None:
        """Test that init command does not require any command-line arguments."""
        # This test verifies that the command can be invoked without arguments
        # The actual command will fail if not implemented, but we're testing the signature
        result = cli_runner.invoke(app, ["init"])

        # Should not fail due to missing arguments
        # (may fail for other reasons like NotImplementedError, which is expected in RED phase)
        assert "missing" not in result.stdout.lower()
        assert "required" not in result.stdout.lower()
