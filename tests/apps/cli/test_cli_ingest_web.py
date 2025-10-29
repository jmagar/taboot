"""Tests for ingest web CLI command (T051-T052).

Following TDD: Write failing tests first (RED), then implement to pass (GREEN).

The ingest web command should:
1. Accept URL and optional --limit argument
2. Create and configure IngestWebUseCase with all dependencies
3. Execute the use case and display progress
4. Handle errors gracefully with proper exit codes
5. Report results (pages crawled, chunks created, duration)
"""

from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from apps.cli.main import app
from packages.schemas.models import IngestionJob, JobState, SourceType


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide Typer CLI test runner.

    Returns:
        CliRunner: Typer test runner instance.
    """
    return CliRunner()


@pytest.fixture
def mock_job() -> IngestionJob:
    """Provide a mock IngestionJob for testing.

    Returns:
        IngestionJob: Completed ingestion job with sample data.
    """
    from datetime import UTC, datetime

    job_id = uuid4()
    return IngestionJob(
        job_id=job_id,
        source_type=SourceType.WEB,
        source_target="https://example.com",
        state=JobState.COMPLETED,
        created_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        pages_processed=18,
        chunks_created=342,
        errors=None,
    )


@pytest.mark.unit
class TestIngestWebCommand:
    """Test ingest web CLI command orchestration."""

    def test_ingest_command_exists(self, cli_runner: CliRunner) -> None:
        """Test that ingest command is registered in the CLI."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ingest" in result.stdout

    def test_ingest_web_subcommand_exists(self, cli_runner: CliRunner) -> None:
        """Test that ingest web subcommand is registered."""
        result = cli_runner.invoke(app, ["ingest", "--help"])
        # Should show help without error (even if not implemented yet)
        assert result.exit_code == 0 or "not yet implemented" in result.stdout.lower()

    @patch("apps.cli.commands.ingest_web.IngestWebUseCase")
    @patch("apps.cli.commands.ingest_web.WebReader")
    @patch("apps.cli.commands.ingest_web.Normalizer")
    @patch("apps.cli.commands.ingest_web.Chunker")
    @patch("apps.cli.commands.ingest_web.Embedder")
    @patch("apps.cli.commands.ingest_web.QdrantWriter")
    @patch("apps.cli.commands.ingest_web.get_config")
    def test_ingest_web_accepts_url_argument(
        self,
        mock_get_config: MagicMock,
        mock_qdrant_writer: MagicMock,
        mock_embedder: MagicMock,
        mock_chunker: MagicMock,
        mock_normalizer: MagicMock,
        mock_web_reader: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
        mock_job: IngestionJob,
    ) -> None:
        """Test that ingest web command accepts URL as positional argument."""
        # Mock config
        mock_config = Mock()
        mock_config.collection_name = "documents"
        mock_config.firecrawl_api_url = "http://localhost:4200"
        mock_config.qdrant_url = "http://localhost:6333"
        mock_config.tei_embedding_url = "http://localhost:80"
        mock_get_config.return_value = mock_config

        # Mock use case execution
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute.return_value = mock_job

        result = cli_runner.invoke(app, ["ingest", "web", "https://example.com"])

        # Should succeed
        assert result.exit_code == 0

        # Use case should be executed with correct URL
        mock_use_case_instance.execute.assert_called_once()
        call_args = mock_use_case_instance.execute.call_args
        # Check keyword arguments (execute is called with url=... keyword)
        assert call_args.kwargs["url"] == "https://example.com"

    @patch("apps.cli.commands.ingest_web.IngestWebUseCase")
    @patch("apps.cli.commands.ingest_web.WebReader")
    @patch("apps.cli.commands.ingest_web.Normalizer")
    @patch("apps.cli.commands.ingest_web.Chunker")
    @patch("apps.cli.commands.ingest_web.Embedder")
    @patch("apps.cli.commands.ingest_web.QdrantWriter")
    @patch("apps.cli.commands.ingest_web.get_config")
    def test_ingest_web_accepts_limit_option(
        self,
        mock_get_config: MagicMock,
        mock_qdrant_writer: MagicMock,
        mock_embedder: MagicMock,
        mock_chunker: MagicMock,
        mock_normalizer: MagicMock,
        mock_web_reader: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
        mock_job: IngestionJob,
    ) -> None:
        """Test that ingest web command accepts optional --limit parameter."""
        # Mock config
        mock_config = Mock()
        mock_config.collection_name = "documents"
        mock_config.firecrawl_api_url = "http://localhost:4200"
        mock_config.qdrant_url = "http://localhost:6333"
        mock_config.tei_embedding_url = "http://localhost:80"
        mock_get_config.return_value = mock_config

        # Mock use case execution
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute.return_value = mock_job

        result = cli_runner.invoke(app, ["ingest", "web", "https://example.com", "--limit", "20"])

        # Should succeed
        assert result.exit_code == 0

        # Use case should be executed with correct limit
        mock_use_case_instance.execute.assert_called_once()
        call_args = mock_use_case_instance.execute.call_args
        assert call_args[1]["limit"] == 20  # limit keyword argument

    @patch("apps.cli.commands.ingest_web.IngestWebUseCase")
    @patch("apps.cli.commands.ingest_web.WebReader")
    @patch("apps.cli.commands.ingest_web.Normalizer")
    @patch("apps.cli.commands.ingest_web.Chunker")
    @patch("apps.cli.commands.ingest_web.Embedder")
    @patch("apps.cli.commands.ingest_web.QdrantWriter")
    @patch("apps.cli.commands.ingest_web.get_config")
    def test_ingest_web_creates_use_case_with_dependencies(
        self,
        mock_get_config: MagicMock,
        mock_qdrant_writer_class: MagicMock,
        mock_embedder_class: MagicMock,
        mock_chunker_class: MagicMock,
        mock_normalizer_class: MagicMock,
        mock_web_reader_class: MagicMock,
        mock_use_case_class: MagicMock,
        cli_runner: CliRunner,
        mock_job: IngestionJob,
    ) -> None:
        """Test that ingest web command creates IngestWebUseCase with all dependencies."""
        # Mock config
        mock_config = Mock()
        mock_config.collection_name = "documents"
        mock_config.firecrawl_api_url = "http://localhost:4200"
        mock_config.qdrant_url = "http://localhost:6333"
        mock_config.tei_embedding_url = "http://localhost:80"
        mock_get_config.return_value = mock_config

        # Mock adapter instances
        mock_web_reader = Mock()
        mock_normalizer = Mock()
        mock_chunker = Mock()
        mock_embedder = Mock()
        mock_qdrant_writer = Mock()

        mock_web_reader_class.return_value = mock_web_reader
        mock_normalizer_class.return_value = mock_normalizer
        mock_chunker_class.return_value = mock_chunker
        mock_embedder_class.return_value = mock_embedder
        mock_qdrant_writer_class.return_value = mock_qdrant_writer

        # Mock use case
        mock_use_case_instance = Mock()
        mock_use_case_instance.execute.return_value = mock_job
        mock_use_case_class.return_value = mock_use_case_instance

        result = cli_runner.invoke(app, ["ingest", "web", "https://example.com"])

        # Should succeed
        assert result.exit_code == 0

        # IngestWebUseCase should be created with all dependencies
        mock_use_case_class.assert_called_once_with(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="documents",
        )

    @patch("apps.cli.commands.ingest_web.IngestWebUseCase")
    @patch("apps.cli.commands.ingest_web.WebReader")
    @patch("apps.cli.commands.ingest_web.Normalizer")
    @patch("apps.cli.commands.ingest_web.Chunker")
    @patch("apps.cli.commands.ingest_web.Embedder")
    @patch("apps.cli.commands.ingest_web.QdrantWriter")
    @patch("apps.cli.commands.ingest_web.get_config")
    def test_ingest_web_displays_job_id(
        self,
        mock_get_config: MagicMock,
        mock_qdrant_writer: MagicMock,
        mock_embedder: MagicMock,
        mock_chunker: MagicMock,
        mock_normalizer: MagicMock,
        mock_web_reader: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
        mock_job: IngestionJob,
    ) -> None:
        """Test that ingest web command displays job ID in output."""
        # Mock config
        mock_config = Mock()
        mock_config.collection_name = "documents"
        mock_config.firecrawl_api_url = "http://localhost:4200"
        mock_config.qdrant_url = "http://localhost:6333"
        mock_config.tei_embedding_url = "http://localhost:80"
        mock_get_config.return_value = mock_config

        # Mock use case execution
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute.return_value = mock_job

        result = cli_runner.invoke(app, ["ingest", "web", "https://example.com"])

        # Should display job ID
        assert str(mock_job.job_id) in result.stdout

    @patch("apps.cli.commands.ingest_web.IngestWebUseCase")
    @patch("apps.cli.commands.ingest_web.WebReader")
    @patch("apps.cli.commands.ingest_web.Normalizer")
    @patch("apps.cli.commands.ingest_web.Chunker")
    @patch("apps.cli.commands.ingest_web.Embedder")
    @patch("apps.cli.commands.ingest_web.QdrantWriter")
    @patch("apps.cli.commands.ingest_web.get_config")
    def test_ingest_web_displays_results(
        self,
        mock_get_config: MagicMock,
        mock_qdrant_writer: MagicMock,
        mock_embedder: MagicMock,
        mock_chunker: MagicMock,
        mock_normalizer: MagicMock,
        mock_web_reader: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
        mock_job: IngestionJob,
    ) -> None:
        """Test that ingest web command displays pages and chunks counts."""
        # Mock config
        mock_config = Mock()
        mock_config.collection_name = "documents"
        mock_config.firecrawl_api_url = "http://localhost:4200"
        mock_config.qdrant_url = "http://localhost:6333"
        mock_config.tei_embedding_url = "http://localhost:80"
        mock_get_config.return_value = mock_config

        # Mock use case execution
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute.return_value = mock_job

        result = cli_runner.invoke(app, ["ingest", "web", "https://example.com"])

        # Should display results
        assert "18" in result.stdout  # pages_processed
        assert "342" in result.stdout  # chunks_created

    @patch("apps.cli.commands.ingest_web.IngestWebUseCase")
    @patch("apps.cli.commands.ingest_web.WebReader")
    @patch("apps.cli.commands.ingest_web.Normalizer")
    @patch("apps.cli.commands.ingest_web.Chunker")
    @patch("apps.cli.commands.ingest_web.Embedder")
    @patch("apps.cli.commands.ingest_web.QdrantWriter")
    @patch("apps.cli.commands.ingest_web.get_config")
    def test_ingest_web_handles_failed_job(
        self,
        mock_get_config: MagicMock,
        mock_qdrant_writer: MagicMock,
        mock_embedder: MagicMock,
        mock_chunker: MagicMock,
        mock_normalizer: MagicMock,
        mock_web_reader: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that ingest web command handles failed jobs gracefully."""
        from datetime import UTC, datetime

        # Mock config
        mock_config = Mock()
        mock_config.collection_name = "documents"
        mock_config.firecrawl_api_url = "http://localhost:4200"
        mock_config.qdrant_url = "http://localhost:6333"
        mock_config.tei_embedding_url = "http://localhost:80"
        mock_get_config.return_value = mock_config

        # Create failed job
        failed_job = IngestionJob(
            job_id=uuid4(),
            source_type=SourceType.WEB,
            source_target="https://example.com",
            state=JobState.FAILED,
            created_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            pages_processed=0,
            chunks_created=0,
            errors=[{"error": "Connection timeout", "timestamp": datetime.now(UTC).isoformat()}],
        )

        # Mock use case to return failed job
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute.return_value = failed_job

        result = cli_runner.invoke(app, ["ingest", "web", "https://example.com"])

        # Should exit with error code
        assert result.exit_code != 0

        # Should display error message
        assert "failed" in result.stdout.lower() or "error" in result.stdout.lower()

    @patch("apps.cli.commands.ingest_web.IngestWebUseCase")
    @patch("apps.cli.commands.ingest_web.WebReader")
    @patch("apps.cli.commands.ingest_web.Normalizer")
    @patch("apps.cli.commands.ingest_web.Chunker")
    @patch("apps.cli.commands.ingest_web.Embedder")
    @patch("apps.cli.commands.ingest_web.QdrantWriter")
    @patch("apps.cli.commands.ingest_web.get_config")
    def test_ingest_web_handles_exception(
        self,
        mock_get_config: MagicMock,
        mock_qdrant_writer: MagicMock,
        mock_embedder: MagicMock,
        mock_chunker: MagicMock,
        mock_normalizer: MagicMock,
        mock_web_reader: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that ingest web command handles unexpected exceptions."""
        # Mock config
        mock_config = Mock()
        mock_config.collection_name = "documents"
        mock_config.firecrawl_api_url = "http://localhost:4200"
        mock_config.qdrant_url = "http://localhost:6333"
        mock_config.tei_embedding_url = "http://localhost:80"
        mock_get_config.return_value = mock_config

        # Mock use case to raise exception
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute.side_effect = Exception("Unexpected error")

        result = cli_runner.invoke(app, ["ingest", "web", "https://example.com"])

        # Should exit with error code
        assert result.exit_code != 0

        # Should display error message
        assert "error" in result.stdout.lower() or "failed" in result.stdout.lower()

    def test_ingest_web_requires_url_argument(self, cli_runner: CliRunner) -> None:
        """Test that ingest web command requires URL argument."""
        result = cli_runner.invoke(app, ["ingest", "web"])

        # Should fail due to missing URL
        assert result.exit_code != 0
        # Typer will complain about missing argument (may be in stdout or stderr)
        output_combined = (result.stdout + result.stderr).lower()
        assert "missing" in output_combined or "required" in output_combined
