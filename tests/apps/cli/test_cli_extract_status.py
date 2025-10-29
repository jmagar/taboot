"""Tests for extract status CLI command (T131-T132).

Following TDD: Write failing tests first (RED), then implement to pass (GREEN).

The extract status command should:
1. Execute `taboot extract status` successfully
2. Display service health with colored indicators (green=healthy, red=unhealthy)
3. Display queue depths (ingestion, extraction)
4. Display metrics snapshot (documents, chunks, jobs, nodes)
5. Exit with code 0 on success, 1 on failure
6. Handle errors gracefully
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from apps.cli.main import app
from packages.core.use_cases.get_status import (
    MetricsSnapshot,
    QueueDepth,
    ServiceHealth,
    SystemStatus,
)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide Typer CLI test runner.

    Returns:
        CliRunner: Typer test runner instance.
    """
    return CliRunner()


@pytest.fixture
def mock_healthy_status() -> SystemStatus:
    """Provide a mock healthy system status for testing.

    Returns:
        SystemStatus: Complete healthy system status.
    """
    return SystemStatus(
        overall_healthy=True,
        services={
            "neo4j": ServiceHealth(name="neo4j", healthy=True),
            "qdrant": ServiceHealth(name="qdrant", healthy=True),
            "redis": ServiceHealth(name="redis", healthy=True),
            "tei": ServiceHealth(name="tei", healthy=True),
            "ollama": ServiceHealth(name="ollama", healthy=True),
            "firecrawl": ServiceHealth(name="firecrawl", healthy=True),
            "playwright": ServiceHealth(name="playwright", healthy=True),
        },
        queue_depth=QueueDepth(ingestion=5, extraction=12),
        metrics=MetricsSnapshot(
            documents_ingested=150,
            chunks_indexed=3420,
            extraction_jobs_completed=138,
            graph_nodes_created=892,
        ),
    )


@pytest.fixture
def mock_unhealthy_status() -> SystemStatus:
    """Provide a mock unhealthy system status for testing.

    Returns:
        SystemStatus: System status with failed services.
    """
    return SystemStatus(
        overall_healthy=False,
        services={
            "neo4j": ServiceHealth(name="neo4j", healthy=False, message="Connection timeout"),
            "qdrant": ServiceHealth(name="qdrant", healthy=True),
            "redis": ServiceHealth(name="redis", healthy=True),
            "tei": ServiceHealth(name="tei", healthy=False, message="Service unavailable"),
            "ollama": ServiceHealth(name="ollama", healthy=True),
            "firecrawl": ServiceHealth(name="firecrawl", healthy=True),
            "playwright": ServiceHealth(name="playwright", healthy=True),
        },
        queue_depth=QueueDepth(ingestion=23, extraction=45),
        metrics=MetricsSnapshot(
            documents_ingested=200,
            chunks_indexed=4500,
            extraction_jobs_completed=185,
            graph_nodes_created=1050,
        ),
    )


@pytest.mark.unit
class TestExtractStatusCommand:
    """Test extract status CLI command orchestration."""

    def test_status_command_exists(self, cli_runner: CliRunner) -> None:
        """Test that extract status command is registered in the CLI."""
        result = cli_runner.invoke(app, ["extract", "--help"])
        assert result.exit_code == 0
        assert "status" in result.stdout

    @patch("apps.cli.commands.extract_status.GetStatusUseCase")
    @patch("apps.cli.commands.extract_status.get_config")
    @patch("apps.cli.commands.extract_status.redis.asyncio.from_url")
    @patch("apps.cli.commands.extract_status.check_system_health")
    def test_extract_status_command_success_healthy(
        self,
        mock_health_checker: MagicMock,
        mock_redis_from_url: MagicMock,
        mock_get_config: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
        mock_healthy_status: SystemStatus,
    ) -> None:
        """Test that extract status command displays healthy system status."""
        # Mock config
        mock_config = MagicMock()
        mock_config.redis_url = "redis://localhost:4202"
        mock_get_config.return_value = mock_config

        # Mock Redis client (async)
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()

        async def mock_from_url_func(url: str) -> AsyncMock:
            return mock_redis_client

        mock_redis_from_url.side_effect = mock_from_url_func

        # Mock use case execution
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute = AsyncMock(return_value=mock_healthy_status)

        result = cli_runner.invoke(app, ["extract", "status"])

        # Should succeed
        assert result.exit_code == 0

        # Should display header
        assert "System Status" in result.stdout

        # Should display all services with healthy status
        assert "neo4j" in result.stdout.lower()
        assert "qdrant" in result.stdout.lower()
        assert "redis" in result.stdout.lower()
        assert "tei" in result.stdout.lower()
        assert "ollama" in result.stdout.lower()
        assert "firecrawl" in result.stdout.lower()
        assert "playwright" in result.stdout.lower()

        # Should display queue depths
        assert "5" in result.stdout  # ingestion queue
        assert "12" in result.stdout  # extraction queue

        # Should display metrics (formatted with thousands separators)
        assert "150" in result.stdout  # documents ingested
        assert "3,420" in result.stdout  # chunks indexed (formatted)
        assert "138" in result.stdout  # extraction jobs
        assert "892" in result.stdout  # graph nodes

    @patch("apps.cli.commands.extract_status.GetStatusUseCase")
    @patch("apps.cli.commands.extract_status.get_config")
    @patch("apps.cli.commands.extract_status.redis.asyncio.from_url")
    @patch("apps.cli.commands.extract_status.check_system_health")
    def test_extract_status_command_shows_unhealthy_services(
        self,
        mock_health_checker: MagicMock,
        mock_redis_from_url: MagicMock,
        mock_get_config: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
        mock_unhealthy_status: SystemStatus,
    ) -> None:
        """Test that extract status command displays unhealthy services with errors."""
        # Mock config
        mock_config = MagicMock()
        mock_config.redis_url = "redis://localhost:4202"
        mock_get_config.return_value = mock_config

        # Mock Redis client (async)
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()

        async def mock_from_url_func(url: str) -> AsyncMock:
            return mock_redis_client

        mock_redis_from_url.side_effect = mock_from_url_func

        # Mock use case execution
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute = AsyncMock(return_value=mock_unhealthy_status)

        result = cli_runner.invoke(app, ["extract", "status"])

        # Should succeed (even with unhealthy services)
        assert result.exit_code == 0

        # Should display error messages
        assert "Connection timeout" in result.stdout or "timeout" in result.stdout.lower()
        assert "Service unavailable" in result.stdout or "unavailable" in result.stdout.lower()

        # Should display queue depths
        assert "23" in result.stdout  # ingestion queue
        assert "45" in result.stdout  # extraction queue

    @patch("apps.cli.commands.extract_status.GetStatusUseCase")
    @patch("apps.cli.commands.extract_status.get_config")
    @patch("apps.cli.commands.extract_status.redis.asyncio.from_url")
    @patch("apps.cli.commands.extract_status.check_system_health")
    def test_extract_status_command_handles_exception(
        self,
        mock_health_checker: MagicMock,
        mock_redis_from_url: MagicMock,
        mock_get_config: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that extract status command handles unexpected exceptions."""
        # Mock config
        mock_config = MagicMock()
        mock_config.redis_url = "redis://localhost:4202"
        mock_get_config.return_value = mock_config

        # Mock Redis client (async)
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()

        async def mock_from_url_func(url: str) -> AsyncMock:
            return mock_redis_client

        mock_redis_from_url.side_effect = mock_from_url_func

        # Mock use case to raise exception
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute = AsyncMock(
            side_effect=Exception("Failed to fetch system status")
        )

        result = cli_runner.invoke(app, ["extract", "status"])

        # Should exit with error code
        assert result.exit_code != 0

        # Should display error message
        assert "error" in result.stdout.lower() or "failed" in result.stdout.lower()

    @patch("apps.cli.commands.extract_status.GetStatusUseCase")
    @patch("apps.cli.commands.extract_status.get_config")
    @patch("apps.cli.commands.extract_status.redis.asyncio.from_url")
    @patch("apps.cli.commands.extract_status.check_system_health")
    def test_extract_status_displays_formatted_output(
        self,
        mock_health_checker: MagicMock,
        mock_redis_from_url: MagicMock,
        mock_get_config: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
        mock_healthy_status: SystemStatus,
    ) -> None:
        """Test that extract status command displays well-formatted output."""
        # Mock config
        mock_config = MagicMock()
        mock_config.redis_url = "redis://localhost:4202"
        mock_get_config.return_value = mock_config

        # Mock Redis client (async)
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()

        async def mock_from_url_func(url: str) -> AsyncMock:
            return mock_redis_client

        mock_redis_from_url.side_effect = mock_from_url_func

        # Mock use case execution
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute = AsyncMock(return_value=mock_healthy_status)

        result = cli_runner.invoke(app, ["extract", "status"])

        # Should display formatted sections
        assert "System Status" in result.stdout
        assert "Service Health" in result.stdout or "Services" in result.stdout
        assert "Queue Depth" in result.stdout or "Queues" in result.stdout
        assert "Metrics" in result.stdout

    @patch("apps.cli.commands.extract_status.GetStatusUseCase")
    @patch("apps.cli.commands.extract_status.get_config")
    @patch("apps.cli.commands.extract_status.redis.asyncio.from_url")
    @patch("apps.cli.commands.extract_status.check_system_health")
    def test_extract_status_zero_queue_depths(
        self,
        mock_health_checker: MagicMock,
        mock_redis_from_url: MagicMock,
        mock_get_config: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that extract status command handles zero queue depths."""
        # Mock config
        mock_config = MagicMock()
        mock_config.redis_url = "redis://localhost:4202"
        mock_get_config.return_value = mock_config

        # Mock Redis client (async)
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()

        async def mock_from_url_func(url: str) -> AsyncMock:
            return mock_redis_client

        mock_redis_from_url.side_effect = mock_from_url_func

        # Create status with zero queues
        empty_status = SystemStatus(
            overall_healthy=True,
            services={
                "neo4j": ServiceHealth(name="neo4j", healthy=True),
                "qdrant": ServiceHealth(name="qdrant", healthy=True),
                "redis": ServiceHealth(name="redis", healthy=True),
                "tei": ServiceHealth(name="tei", healthy=True),
                "ollama": ServiceHealth(name="ollama", healthy=True),
                "firecrawl": ServiceHealth(name="firecrawl", healthy=True),
                "playwright": ServiceHealth(name="playwright", healthy=True),
            },
            queue_depth=QueueDepth(ingestion=0, extraction=0),
            metrics=MetricsSnapshot(
                documents_ingested=0,
                chunks_indexed=0,
                extraction_jobs_completed=0,
                graph_nodes_created=0,
            ),
        )

        # Mock use case execution
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute = AsyncMock(return_value=empty_status)

        result = cli_runner.invoke(app, ["extract", "status"])

        # Should succeed
        assert result.exit_code == 0

        # Should display zeros (queue depths appear in output)
        assert "Queue" in result.stdout
