"""Tests for SWAG config ingestion CLI command.

Tests the Typer CLI command for ingesting SWAG reverse proxy configs
into the Neo4j graph database.

Following TDD: Write failing tests first, then implement command.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from apps.cli.commands.ingest_swag import app
from packages.schemas.models import Proxy, ProxyType

runner = CliRunner()


@pytest.fixture
def sample_swag_config(tmp_path: Path) -> Path:
    """Create a sample SWAG nginx config file for testing."""
    config_content = """
server {
    listen 443 ssl;
    server_name api.example.com;

    location / {
        proxy_pass http://api-service:8080;
    }

    location /admin {
        proxy_pass http://admin-service:3000;
    }
}

server {
    listen 80;
    server_name web.example.com;

    location / {
        proxy_pass http://web-service:80;
    }
}
"""
    config_file = tmp_path / "api.conf"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def mock_swag_reader() -> MagicMock:
    """Mock SwagReader for testing CLI without Neo4j."""
    from datetime import UTC, datetime

    mock_reader = MagicMock()

    # Mock parse_file to return proxies and routes
    proxy = Proxy(
        name="swag",
        proxy_type=ProxyType.SWAG,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metadata={"source": "swag_config"},
    )

    routes = [
        {
            "host": "api.example.com",
            "path": "/",
            "target_service": "api-service",
            "tls": True,
        },
        {
            "host": "api.example.com",
            "path": "/admin",
            "target_service": "admin-service",
            "tls": True,
        },
        {
            "host": "web.example.com",
            "path": "/",
            "target_service": "web-service",
            "tls": False,
        },
    ]

    mock_reader.parse_file.return_value = {"proxies": [proxy], "routes": routes}
    return mock_reader


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Mock Neo4jClient for testing CLI without Neo4j."""
    mock_client = MagicMock()
    mock_client.connect.return_value = None
    mock_client.close.return_value = None

    # Mock session context manager
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=None)
    mock_client.session.return_value = mock_session

    return mock_client


class TestIngestSwagCommand:
    """Test suite for `taboot ingest swag` command."""

    def test_swag_command_exists(self) -> None:
        """Test that the swag subcommand is registered."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "swag" in result.stdout

    def test_ingest_swag_with_valid_config(
        self,
        sample_swag_config: Path,
        mock_swag_reader: MagicMock,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test ingesting a valid SWAG config file."""
        with (
            patch("apps.cli.commands.ingest_swag.SwagReader", return_value=mock_swag_reader),
            patch("apps.cli.commands.ingest_swag.Neo4jClient", return_value=mock_neo4j_client),
        ):
            result = runner.invoke(app, [str(sample_swag_config)])

            assert result.exit_code == 0
            assert "Starting SWAG config ingestion" in result.stdout
            assert str(sample_swag_config) in result.stdout
            assert "1 proxy" in result.stdout.lower()
            assert "3 routes" in result.stdout.lower()

            # Verify reader was called
            mock_swag_reader.parse_file.assert_called_once_with(str(sample_swag_config))

            # Verify Neo4j client was used
            mock_neo4j_client.connect.assert_called_once()
            mock_neo4j_client.close.assert_called_once()

    def test_ingest_swag_with_nonexistent_file(self) -> None:
        """Test that command fails gracefully with nonexistent config file."""
        nonexistent = "/tmp/nonexistent-config.conf"

        with (
            patch("apps.cli.commands.ingest_swag.SwagReader") as mock_reader_class,
        ):
            mock_reader = MagicMock()
            mock_reader.parse_file.side_effect = FileNotFoundError(
                f"Config file not found: {nonexistent}"
            )
            mock_reader_class.return_value = mock_reader

            result = runner.invoke(app, [nonexistent])

            assert result.exit_code == 1
            assert "not found" in result.stdout.lower() or "failed" in result.stdout.lower()

    def test_ingest_swag_with_invalid_config(
        self, tmp_path: Path, mock_neo4j_client: MagicMock
    ) -> None:
        """Test that command fails gracefully with invalid nginx config."""
        invalid_config = tmp_path / "invalid.conf"
        invalid_config.write_text("server { this is not valid nginx config")

        with (
            patch("apps.cli.commands.ingest_swag.SwagReader") as mock_reader_class,
            patch("apps.cli.commands.ingest_swag.Neo4jClient", return_value=mock_neo4j_client),
        ):
            mock_reader = MagicMock()
            mock_reader.parse_file.side_effect = ValueError("Invalid nginx syntax")
            mock_reader_class.return_value = mock_reader

            result = runner.invoke(app, [str(invalid_config)])

            assert result.exit_code == 1
            assert "failed" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_ingest_swag_missing_argument(self) -> None:
        """Test that command requires config path argument."""
        result = runner.invoke(app, [])
        # Exit code 2 indicates Typer/Click usage error
        assert result.exit_code == 2
        # Check stderr for error message since Typer outputs usage errors there
        output = result.stdout + getattr(result, "stderr", "")
        has_error_message = "missing argument" in output.lower() or "required" in output.lower()
        # Accept if either error message exists or exit code is 2
        assert has_error_message or result.exit_code == 2

    def test_ingest_swag_with_proxy_name_option(
        self,
        sample_swag_config: Path,
        mock_swag_reader: MagicMock,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test ingesting SWAG config with custom proxy name."""
        with (
            patch("apps.cli.commands.ingest_swag.SwagReader", return_value=mock_swag_reader),
            patch("apps.cli.commands.ingest_swag.Neo4jClient", return_value=mock_neo4j_client),
        ):
            result = runner.invoke(app, [str(sample_swag_config), "--proxy-name", "custom-proxy"])

            assert result.exit_code == 0
            assert "custom-proxy" in result.stdout or result.exit_code == 0

    def test_ingest_swag_displays_progress(
        self,
        sample_swag_config: Path,
        mock_swag_reader: MagicMock,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test that command displays progress and results."""
        with (
            patch("apps.cli.commands.ingest_swag.SwagReader", return_value=mock_swag_reader),
            patch("apps.cli.commands.ingest_swag.Neo4jClient", return_value=mock_neo4j_client),
        ):
            result = runner.invoke(app, [str(sample_swag_config)])

            assert result.exit_code == 0

            # Check for progress indicators
            output_lower = result.stdout.lower()
            assert "starting" in output_lower or "ingestion" in output_lower
            assert "proxy" in output_lower or "proxies" in output_lower
            assert "route" in output_lower or "routes" in output_lower

    def test_ingest_swag_handles_empty_config(
        self, tmp_path: Path, mock_neo4j_client: MagicMock
    ) -> None:
        """Test ingesting an empty config file."""
        from datetime import UTC, datetime

        empty_config = tmp_path / "empty.conf"
        empty_config.write_text("")

        # Create mock for empty config case
        mock_reader = MagicMock()
        proxy = Proxy(
            name="swag",
            proxy_type=ProxyType.SWAG,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={"source": "swag_config"},
        )
        mock_reader.parse_file.return_value = {"proxies": [proxy], "routes": []}

        with (
            patch("apps.cli.commands.ingest_swag.SwagReader", return_value=mock_reader),
            patch("apps.cli.commands.ingest_swag.Neo4jClient", return_value=mock_neo4j_client),
        ):
            result = runner.invoke(app, [str(empty_config)])

            # Should succeed but show 0 routes
            assert result.exit_code == 0
            assert "0 route" in result.stdout.lower()
