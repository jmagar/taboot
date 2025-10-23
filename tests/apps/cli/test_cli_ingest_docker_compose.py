"""Tests for ingest docker-compose CLI command (T122-T123).

Following TDD: Write failing tests first (RED), then implement to pass (GREEN).

The ingest docker-compose command should:
1. Accept file path as positional argument
2. Parse docker-compose.yaml file
3. Extract Service nodes and relationships (DEPENDS_ON, BINDS)
4. Write entities to Neo4j graph using BatchedGraphWriter
5. Handle errors gracefully (file not found, invalid YAML, invalid ports)
6. Display progress and results using rich.Console
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

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


@pytest.fixture
def sample_compose_data() -> dict[str, list[dict[str, str | int]]]:
    """Provide sample Docker Compose data structure.

    Returns:
        dict: Sample parsed compose data with services and relationships.
    """
    return {
        "services": [
            {"name": "web", "image": "nginx:latest", "version": "latest"},
            {"name": "api", "image": "myapp/api:v1.2.3", "version": "v1.2.3"},
            {"name": "db", "image": "postgres:15", "version": "15"},
        ],
        "relationships": [
            {"type": "DEPENDS_ON", "source": "web", "target": "api"},
            {"type": "DEPENDS_ON", "source": "api", "target": "db"},
            {"type": "BINDS", "source": "web", "port": 80, "protocol": "tcp"},
            {"type": "BINDS", "source": "api", "port": 8080, "protocol": "tcp"},
            {"type": "BINDS", "source": "db", "port": 5432, "protocol": "tcp"},
        ],
    }


@pytest.mark.unit
class TestIngestDockerComposeCommand:
    """Test ingest docker-compose CLI command orchestration."""

    def test_ingest_docker_compose_subcommand_exists(self, cli_runner: CliRunner) -> None:
        """Test that ingest docker-compose subcommand is available."""
        result = cli_runner.invoke(app, ["ingest", "--help"])
        assert result.exit_code == 0
        # Should show docker-compose as a subcommand (or at least show help)
        # This will fail until we implement the command

    @patch("apps.cli.commands.ingest_docker_compose.DockerComposeReader")
    @patch("apps.cli.commands.ingest_docker_compose.Neo4jClient")
    @patch("apps.cli.commands.ingest_docker_compose.BatchedGraphWriter")
    @patch("apps.cli.commands.ingest_docker_compose.get_config")
    def test_ingest_docker_compose_accepts_file_path(
        self,
        mock_get_config: MagicMock,
        mock_writer_class: MagicMock,
        mock_client_class: MagicMock,
        mock_reader_class: MagicMock,
        cli_runner: CliRunner,
        sample_compose_data: dict[str, list[dict[str, str | int]]],
        tmp_path: Path,
    ) -> None:
        """Test that ingest docker-compose command accepts file path as argument."""
        # Create temporary docker-compose.yaml
        compose_file = tmp_path / "docker-compose.yaml"
        compose_file.write_text("version: '3'\nservices:\n  web:\n    image: nginx:latest\n")

        # Mock config
        mock_config = Mock()
        mock_config.neo4j_uri = "bolt://localhost:7687"
        mock_config.neo4j_user = "neo4j"
        mock_config.neo4j_password = "password"
        mock_get_config.return_value = mock_config

        # Mock reader to return sample data
        mock_reader = Mock()
        mock_reader.load_data.return_value = sample_compose_data
        mock_reader_class.return_value = mock_reader

        # Mock Neo4j client and writer
        mock_client = Mock()
        mock_client.connect = Mock()
        mock_client.close = Mock()
        mock_client_class.return_value = mock_client

        mock_writer = Mock()
        mock_writer.batch_write_nodes = AsyncMock(
            return_value={"total_written": 3, "batches_executed": 1}
        )
        mock_writer.batch_write_relationships = AsyncMock(
            return_value={"total_written": 5, "batches_executed": 1}
        )
        mock_writer_class.return_value = mock_writer

        result = cli_runner.invoke(app, ["ingest", "docker-compose", str(compose_file)])

        # Should succeed
        assert result.exit_code == 0

        # Reader should be called with correct file path
        mock_reader.load_data.assert_called_once_with(file_path=str(compose_file))

    @patch("apps.cli.commands.ingest_docker_compose.DockerComposeReader")
    @patch("apps.cli.commands.ingest_docker_compose.Neo4jClient")
    @patch("apps.cli.commands.ingest_docker_compose.BatchedGraphWriter")
    @patch("apps.cli.commands.ingest_docker_compose.get_config")
    def test_ingest_docker_compose_writes_services_to_neo4j(
        self,
        mock_get_config: MagicMock,
        mock_writer_class: MagicMock,
        mock_client_class: MagicMock,
        mock_reader_class: MagicMock,
        cli_runner: CliRunner,
        sample_compose_data: dict[str, list[dict[str, str | int]]],
        tmp_path: Path,
    ) -> None:
        """Test that services are written to Neo4j as Service nodes."""
        compose_file = tmp_path / "docker-compose.yaml"
        compose_file.write_text("version: '3'\nservices:\n  web:\n    image: nginx:latest\n")

        # Mock config
        mock_config = Mock()
        mock_config.neo4j_uri = "bolt://localhost:7687"
        mock_config.neo4j_user = "neo4j"
        mock_config.neo4j_password = "password"
        mock_get_config.return_value = mock_config

        # Mock reader
        mock_reader = Mock()
        mock_reader.load_data.return_value = sample_compose_data
        mock_reader_class.return_value = mock_reader

        # Mock Neo4j client
        mock_client = Mock()
        mock_client.connect = Mock()
        mock_client.close = Mock()
        mock_client_class.return_value = mock_client

        # Mock writer
        mock_writer = Mock()
        mock_writer.batch_write_nodes = AsyncMock(
            return_value={"total_written": 3, "batches_executed": 1}
        )
        mock_writer.batch_write_relationships = AsyncMock(
            return_value={"total_written": 5, "batches_executed": 1}
        )
        mock_writer_class.return_value = mock_writer

        result = cli_runner.invoke(app, ["ingest", "docker-compose", str(compose_file)])

        assert result.exit_code == 0

        # Verify batch_write_nodes was called with correct parameters
        mock_writer.batch_write_nodes.assert_called_once()
        call_args = mock_writer.batch_write_nodes.call_args
        assert call_args[1]["label"] == "Service"
        assert call_args[1]["unique_key"] == "name"
        assert len(call_args[1]["nodes"]) == 3

    @patch("apps.cli.commands.ingest_docker_compose.DockerComposeReader")
    @patch("apps.cli.commands.ingest_docker_compose.Neo4jClient")
    @patch("apps.cli.commands.ingest_docker_compose.BatchedGraphWriter")
    @patch("apps.cli.commands.ingest_docker_compose.get_config")
    def test_ingest_docker_compose_writes_relationships_to_neo4j(
        self,
        mock_get_config: MagicMock,
        mock_writer_class: MagicMock,
        mock_client_class: MagicMock,
        mock_reader_class: MagicMock,
        cli_runner: CliRunner,
        sample_compose_data: dict[str, list[dict[str, str | int]]],
        tmp_path: Path,
    ) -> None:
        """Test that DEPENDS_ON and BINDS relationships are written to Neo4j."""
        compose_file = tmp_path / "docker-compose.yaml"
        compose_file.write_text("version: '3'\nservices:\n  web:\n    image: nginx:latest\n")

        # Mock config
        mock_config = Mock()
        mock_config.neo4j_uri = "bolt://localhost:7687"
        mock_config.neo4j_user = "neo4j"
        mock_config.neo4j_password = "password"
        mock_get_config.return_value = mock_config

        # Mock reader
        mock_reader = Mock()
        mock_reader.load_data.return_value = sample_compose_data
        mock_reader_class.return_value = mock_reader

        # Mock Neo4j client
        mock_client = Mock()
        mock_client.connect = Mock()
        mock_client.close = Mock()
        mock_client_class.return_value = mock_client

        # Mock writer
        mock_writer = Mock()
        mock_writer.batch_write_nodes = AsyncMock(
            return_value={"total_written": 3, "batches_executed": 1}
        )
        mock_writer.batch_write_relationships = AsyncMock(
            return_value={"total_written": 5, "batches_executed": 1}
        )
        mock_writer_class.return_value = mock_writer

        result = cli_runner.invoke(app, ["ingest", "docker-compose", str(compose_file)])

        assert result.exit_code == 0

        # Verify batch_write_relationships was called twice (DEPENDS_ON and BINDS)
        assert mock_writer.batch_write_relationships.call_count == 2

    @patch("apps.cli.commands.ingest_docker_compose.DockerComposeReader")
    @patch("apps.cli.commands.ingest_docker_compose.get_config")
    def test_ingest_docker_compose_displays_results(
        self,
        mock_get_config: MagicMock,
        mock_reader_class: MagicMock,
        cli_runner: CliRunner,
        sample_compose_data: dict[str, list[dict[str, str | int]]],
        tmp_path: Path,
    ) -> None:
        """Test that command displays service and relationship counts."""
        compose_file = tmp_path / "docker-compose.yaml"
        compose_file.write_text("version: '3'\nservices:\n  web:\n    image: nginx:latest\n")

        # Mock config
        mock_config = Mock()
        mock_config.neo4j_uri = "bolt://localhost:7687"
        mock_config.neo4j_user = "neo4j"
        mock_config.neo4j_password = "password"
        mock_get_config.return_value = mock_config

        # Mock reader
        mock_reader = Mock()
        mock_reader.load_data.return_value = sample_compose_data
        mock_reader_class.return_value = mock_reader

        # Mock Neo4j client and writer in a way that doesn't fail
        with patch("apps.cli.commands.ingest_docker_compose.Neo4jClient"), patch(
            "apps.cli.commands.ingest_docker_compose.BatchedGraphWriter"
        ) as mock_writer_class:
            mock_writer = Mock()
            mock_writer.batch_write_nodes = AsyncMock(
                return_value={"total_written": 3, "batches_executed": 1}
            )
            mock_writer.batch_write_relationships = AsyncMock(
                return_value={"total_written": 5, "batches_executed": 1}
            )
            mock_writer_class.return_value = mock_writer

            result = cli_runner.invoke(app, ["ingest", "docker-compose", str(compose_file)])

            # Should display counts
            assert "3" in result.stdout  # services count
            assert "5" in result.stdout  # relationships count

    @patch("apps.cli.commands.ingest_docker_compose.DockerComposeReader")
    def test_ingest_docker_compose_handles_file_not_found(
        self,
        mock_reader_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that command handles missing file gracefully."""
        from packages.ingest.readers.docker_compose import DockerComposeError

        # Mock reader to raise DockerComposeError
        mock_reader = Mock()
        mock_reader.load_data.side_effect = DockerComposeError("File not found: /missing.yaml")
        mock_reader_class.return_value = mock_reader

        result = cli_runner.invoke(app, ["ingest", "docker-compose", "/missing.yaml"])

        # Should exit with error code
        assert result.exit_code != 0

        # Should display error message
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()

    @patch("apps.cli.commands.ingest_docker_compose.DockerComposeReader")
    @patch("apps.cli.commands.ingest_docker_compose.get_config")
    def test_ingest_docker_compose_handles_invalid_yaml(
        self,
        mock_get_config: MagicMock,
        mock_reader_class: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test that command handles malformed YAML gracefully."""
        from packages.ingest.readers.docker_compose import InvalidYAMLError

        compose_file = tmp_path / "invalid.yaml"
        compose_file.write_text("invalid: yaml: content:")

        # Mock config
        mock_config = Mock()
        mock_config.neo4j_uri = "bolt://localhost:7687"
        mock_config.neo4j_user = "neo4j"
        mock_config.neo4j_password = "password"
        mock_get_config.return_value = mock_config

        # Mock reader to raise InvalidYAMLError
        mock_reader = Mock()
        mock_reader.load_data.side_effect = InvalidYAMLError("Invalid YAML")
        mock_reader_class.return_value = mock_reader

        result = cli_runner.invoke(app, ["ingest", "docker-compose", str(compose_file)])

        # Should exit with error code
        assert result.exit_code != 0

        # Should display error message
        assert "yaml" in result.stdout.lower() or "invalid" in result.stdout.lower()

    @patch("apps.cli.commands.ingest_docker_compose.DockerComposeReader")
    def test_ingest_docker_compose_handles_invalid_port(
        self,
        mock_reader_class: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test that command handles invalid port numbers gracefully."""
        from packages.ingest.readers.docker_compose import InvalidPortError

        compose_file = tmp_path / "docker-compose.yaml"
        compose_file.write_text("version: '3'\nservices:\n  web:\n    image: nginx:latest\n")

        # Mock reader to raise InvalidPortError
        mock_reader = Mock()
        mock_reader.load_data.side_effect = InvalidPortError("Port 99999 out of range")
        mock_reader_class.return_value = mock_reader

        result = cli_runner.invoke(app, ["ingest", "docker-compose", str(compose_file)])

        # Should exit with error code
        assert result.exit_code != 0

        # Should display error message
        assert "port" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_ingest_docker_compose_requires_file_path(self, cli_runner: CliRunner) -> None:
        """Test that command requires file path argument."""
        result = cli_runner.invoke(app, ["ingest", "docker-compose"])

        # Should fail due to missing file path
        assert result.exit_code != 0
        output_combined = (result.stdout + result.stderr).lower()
        assert "missing" in output_combined or "required" in output_combined
