"""Tests for extract pending CLI command (T084).

Following TDD: Write failing tests first (RED), then implement to pass (GREEN).

The extract pending command should:
1. Execute `taboot extract pending` successfully
2. Accept optional `--limit N` flag
3. Display summary output (processed, succeeded, failed)
4. Exit with code 0 on success, 1 on failure
5. Handle errors gracefully
"""

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
def mock_extraction_summary() -> dict[str, int]:
    """Provide a mock extraction summary for testing.

    Returns:
        dict[str, int]: Extraction summary with processed, succeeded, failed counts.
    """
    return {
        "processed": 42,
        "succeeded": 38,
        "failed": 4,
    }


@pytest.mark.unit
class TestExtractPendingCommand:
    """Test extract pending CLI command orchestration."""

    def test_extract_command_exists(self, cli_runner: CliRunner) -> None:
        """Test that extract command is registered in the CLI."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "extract" in result.stdout

    @patch("apps.cli.commands.extract_pending.ExtractPendingUseCase")
    @patch("apps.cli.commands.extract_pending.ExtractionOrchestrator")
    @patch("apps.cli.commands.extract_pending.get_config")
    @patch("apps.cli.commands.extract_pending.EntityPatternMatcher")
    @patch("apps.cli.commands.extract_pending.WindowSelector")
    @patch("apps.cli.commands.extract_pending.TierCLLMClient")
    @patch("apps.cli.commands.extract_pending.redis.asyncio.from_url")
    def test_extract_pending_command_success(
        self,
        mock_redis_from_url: MagicMock,
        mock_llm_client: MagicMock,
        mock_window_selector: MagicMock,
        mock_pattern_matcher: MagicMock,
        mock_get_config: MagicMock,
        mock_orchestrator: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
        mock_extraction_summary: dict[str, int],
    ) -> None:
        """Test that extract pending command executes successfully."""
        # Mock config
        mock_config = Mock()
        mock_config.redis_url = "redis://localhost:6379"
        mock_config.ollama_base_url = "http://localhost:11434"
        mock_config.ollama_model = "qwen3:4b"
        mock_get_config.return_value = mock_config

        # Mock Redis client (async)
        # from_url is an async function, so we need to make the mock awaitable
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()

        # Create an async function that returns the mock client
        async def mock_from_url_func(url: str) -> AsyncMock:
            return mock_redis_client

        mock_redis_from_url.side_effect = mock_from_url_func

        # Mock document store (will be created in command)
        mock_document_store = Mock()

        # Mock use case execution
        # ExtractPendingUseCase.execute() is async, so use AsyncMock
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute = AsyncMock(return_value=mock_extraction_summary)

        # Patch document store creation
        with patch("apps.cli.commands.extract_pending.InMemoryDocumentStore") as mock_store_cls:
            mock_store_cls.return_value = mock_document_store

            result = cli_runner.invoke(app, ["extract", "pending"])

            # Should succeed
            assert result.exit_code == 0

            # Should display summary
            assert "Processed:" in result.stdout
            assert "42" in result.stdout
            assert "38" in result.stdout
            assert "4" in result.stdout

    @patch("apps.cli.commands.extract_pending.ExtractPendingUseCase")
    @patch("apps.cli.commands.extract_pending.ExtractionOrchestrator")
    @patch("apps.cli.commands.extract_pending.get_config")
    @patch("apps.cli.commands.extract_pending.EntityPatternMatcher")
    @patch("apps.cli.commands.extract_pending.WindowSelector")
    @patch("apps.cli.commands.extract_pending.TierCLLMClient")
    @patch("apps.cli.commands.extract_pending.redis.asyncio.from_url")
    def test_extract_pending_accepts_limit_option(
        self,
        mock_redis_from_url: MagicMock,
        mock_llm_client: MagicMock,
        mock_window_selector: MagicMock,
        mock_pattern_matcher: MagicMock,
        mock_get_config: MagicMock,
        mock_orchestrator: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
        mock_extraction_summary: dict[str, int],
    ) -> None:
        """Test that extract pending command accepts optional --limit parameter."""
        # Mock config
        mock_config = Mock()
        mock_config.redis_url = "redis://localhost:6379"
        mock_config.ollama_base_url = "http://localhost:11434"
        mock_config.ollama_model = "qwen3:4b"
        mock_get_config.return_value = mock_config

        # Mock Redis client (async)
        # from_url is an async function, so we need to make the mock awaitable
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()

        # Create an async function that returns the mock client
        async def mock_from_url_func(url: str) -> AsyncMock:
            return mock_redis_client

        mock_redis_from_url.side_effect = mock_from_url_func

        # Mock document store
        mock_document_store = Mock()

        # Mock use case execution
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute = AsyncMock(return_value=mock_extraction_summary)

        # Patch document store creation
        with patch("apps.cli.commands.extract_pending.InMemoryDocumentStore") as mock_store_cls:
            mock_store_cls.return_value = mock_document_store

            result = cli_runner.invoke(app, ["extract", "pending", "--limit", "10"])

            # Should succeed
            assert result.exit_code == 0

            # Use case should be called with limit=10
            mock_use_case_instance.execute.assert_called_once()
            call_kwargs = mock_use_case_instance.execute.call_args.kwargs
            assert call_kwargs["limit"] == 10

    @patch("apps.cli.commands.extract_pending.ExtractPendingUseCase")
    @patch("apps.cli.commands.extract_pending.ExtractionOrchestrator")
    @patch("apps.cli.commands.extract_pending.get_config")
    @patch("apps.cli.commands.extract_pending.EntityPatternMatcher")
    @patch("apps.cli.commands.extract_pending.WindowSelector")
    @patch("apps.cli.commands.extract_pending.TierCLLMClient")
    @patch("apps.cli.commands.extract_pending.redis.asyncio.from_url")
    def test_extract_pending_displays_summary_output(
        self,
        mock_redis_from_url: MagicMock,
        mock_llm_client: MagicMock,
        mock_window_selector: MagicMock,
        mock_pattern_matcher: MagicMock,
        mock_get_config: MagicMock,
        mock_orchestrator: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
        mock_extraction_summary: dict[str, int],
    ) -> None:
        """Test that extract pending command displays formatted summary."""
        # Mock config
        mock_config = Mock()
        mock_config.redis_url = "redis://localhost:6379"
        mock_config.ollama_base_url = "http://localhost:11434"
        mock_config.ollama_model = "qwen3:4b"
        mock_get_config.return_value = mock_config

        # Mock Redis client (async)
        # from_url is an async function, so we need to make the mock awaitable
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()

        # Create an async function that returns the mock client
        async def mock_from_url_func(url: str) -> AsyncMock:
            return mock_redis_client

        mock_redis_from_url.side_effect = mock_from_url_func

        # Mock document store
        mock_document_store = Mock()

        # Mock use case execution
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute = AsyncMock(return_value=mock_extraction_summary)

        # Patch document store creation
        with patch("apps.cli.commands.extract_pending.InMemoryDocumentStore") as mock_store_cls:
            mock_store_cls.return_value = mock_document_store

            result = cli_runner.invoke(app, ["extract", "pending"])

            # Should display header
            assert "Extraction Pipeline" in result.stdout

            # Should display all summary fields
            assert "Processed:" in result.stdout
            assert "Succeeded:" in result.stdout
            assert "Failed:" in result.stdout

    @patch("apps.cli.commands.extract_pending.ExtractPendingUseCase")
    @patch("apps.cli.commands.extract_pending.ExtractionOrchestrator")
    @patch("apps.cli.commands.extract_pending.get_config")
    @patch("apps.cli.commands.extract_pending.EntityPatternMatcher")
    @patch("apps.cli.commands.extract_pending.WindowSelector")
    @patch("apps.cli.commands.extract_pending.TierCLLMClient")
    @patch("apps.cli.commands.extract_pending.redis.asyncio.from_url")
    def test_extract_pending_handles_exception(
        self,
        mock_redis_from_url: MagicMock,
        mock_llm_client: MagicMock,
        mock_window_selector: MagicMock,
        mock_pattern_matcher: MagicMock,
        mock_get_config: MagicMock,
        mock_orchestrator: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that extract pending command handles unexpected exceptions."""
        # Mock config
        mock_config = Mock()
        mock_config.redis_url = "redis://localhost:6379"
        mock_config.ollama_base_url = "http://localhost:11434"
        mock_config.ollama_model = "qwen3:4b"
        mock_get_config.return_value = mock_config

        # Mock Redis client (async)
        # from_url is an async function, so we need to make the mock awaitable
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()

        # Create an async function that returns the mock client
        async def mock_from_url_func(url: str) -> AsyncMock:
            return mock_redis_client

        mock_redis_from_url.side_effect = mock_from_url_func

        # Mock document store
        mock_document_store = Mock()

        # Mock use case to raise exception
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        # Patch document store creation
        with patch("apps.cli.commands.extract_pending.InMemoryDocumentStore") as mock_store_cls:
            mock_store_cls.return_value = mock_document_store

            result = cli_runner.invoke(app, ["extract", "pending"])

            # Should exit with error code
            assert result.exit_code != 0

            # Should display error message
            assert "error" in result.stdout.lower() or "failed" in result.stdout.lower()

    @patch("apps.cli.commands.extract_pending.ExtractPendingUseCase")
    @patch("apps.cli.commands.extract_pending.ExtractionOrchestrator")
    @patch("apps.cli.commands.extract_pending.get_config")
    @patch("apps.cli.commands.extract_pending.EntityPatternMatcher")
    @patch("apps.cli.commands.extract_pending.WindowSelector")
    @patch("apps.cli.commands.extract_pending.TierCLLMClient")
    @patch("apps.cli.commands.extract_pending.redis.asyncio.from_url")
    def test_extract_pending_no_pending_documents(
        self,
        mock_redis_from_url: MagicMock,
        mock_llm_client: MagicMock,
        mock_window_selector: MagicMock,
        mock_pattern_matcher: MagicMock,
        mock_get_config: MagicMock,
        mock_orchestrator: MagicMock,
        mock_use_case: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that extract pending command handles empty queue gracefully."""
        # Mock config
        mock_config = Mock()
        mock_config.redis_url = "redis://localhost:6379"
        mock_config.ollama_base_url = "http://localhost:11434"
        mock_config.ollama_model = "qwen3:4b"
        mock_get_config.return_value = mock_config

        # Mock Redis client (async)
        # from_url is an async function, so we need to make the mock awaitable
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()

        # Create an async function that returns the mock client
        async def mock_from_url_func(url: str) -> AsyncMock:
            return mock_redis_client

        mock_redis_from_url.side_effect = mock_from_url_func

        # Mock document store
        mock_document_store = Mock()

        # Mock use case execution returning empty results
        empty_summary = {"processed": 0, "succeeded": 0, "failed": 0}
        mock_use_case_instance = mock_use_case.return_value
        mock_use_case_instance.execute = AsyncMock(return_value=empty_summary)

        # Patch document store creation
        with patch("apps.cli.commands.extract_pending.InMemoryDocumentStore") as mock_store_cls:
            mock_store_cls.return_value = mock_document_store

            result = cli_runner.invoke(app, ["extract", "pending"])

            # Should succeed even with no documents
            assert result.exit_code == 0

            # Should display zeros
            assert "Processed: 0" in result.stdout
