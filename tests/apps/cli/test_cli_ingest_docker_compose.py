"""CLI tests for Docker Compose ingestion command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from apps.cli.main import app
from packages.core.use_cases.ingest_docker_compose import DockerComposeIngestionResult


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide Typer CLI runner instance."""
    return CliRunner()


class TestIngestDockerComposeCLI:
    """Validate CLI wiring for docker-compose ingestion."""

    def test_docker_compose_subcommand_registered(self, cli_runner: CliRunner) -> None:
        """Ensure top-level ingest command lists docker-compose subcommand."""
        result = cli_runner.invoke(app, ["ingest", "--help"])
        assert result.exit_code == 0
        assert "docker-compose" in result.stdout

    @patch("apps.cli.taboot_cli.commands.ingest_docker_compose.IngestDockerComposeUseCase")
    @patch("apps.cli.taboot_cli.commands.ingest_docker_compose.Neo4jClient")
    @patch("apps.cli.taboot_cli.commands.ingest_docker_compose.DockerComposeReader")
    def test_cli_invokes_use_case(
        self,
        mock_reader_cls: MagicMock,
        mock_client_cls: MagicMock,
        mock_use_case_cls: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Verify CLI instantiates use case and reports ingestion statistics."""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("version: '3'\nservices: {}\n")

        mock_reader_cls.return_value = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_cls.return_value = mock_client

        ingestion_result = DockerComposeIngestionResult(
            compose_files=1,
            compose_projects=1,
            compose_services=3,
            service_dependencies=2,
        )
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = ingestion_result
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(app, ["ingest", "docker-compose", str(compose_file)])

        assert result.exit_code == 0
        mock_use_case.execute.assert_called_once_with(file_path=str(compose_file))
        assert "Nodes written: 5" in result.stdout
        assert "DEPENDS_ON relationships written: 2" in result.stdout

    @patch("apps.cli.taboot_cli.commands.ingest_docker_compose.IngestDockerComposeUseCase")
    @patch("apps.cli.taboot_cli.commands.ingest_docker_compose.Neo4jClient")
    @patch("apps.cli.taboot_cli.commands.ingest_docker_compose.DockerComposeReader")
    def test_cli_handles_reader_errors(
        self,
        mock_reader_cls: MagicMock,
        mock_client_cls: MagicMock,
        mock_use_case_cls: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Ensure reader exceptions are surfaced to the user with exit code 1."""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("version: '3'\nservices: {}\n")

        mock_reader = MagicMock()
        mock_reader.load_data.side_effect = ValueError("boom")
        mock_reader_cls.return_value = mock_reader

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_cls.return_value = mock_client

        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = ValueError("boom")
        mock_use_case_cls.return_value = mock_use_case

        result = cli_runner.invoke(app, ["ingest", "docker-compose", str(compose_file)])

        assert result.exit_code == 1
        assert "Ingestion failed" in result.stdout
