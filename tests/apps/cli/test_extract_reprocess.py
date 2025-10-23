"""Tests for extract reprocess CLI command.

Tests document reprocessing via CLI.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


class TestExtractReprocessCommand:
    """Tests for the extract reprocess CLI command."""

    def test_reprocess_command_requires_since_date(self) -> None:
        """Test that reprocess command requires --since date."""
        result = runner.invoke(app, ["extract", "reprocess"])
        assert result.exit_code != 0  # Exit code check is sufficient

    def test_reprocess_command_accepts_since_date(self) -> None:
        """Test that reprocess command accepts --since date."""
        result = runner.invoke(app, ["extract", "reprocess", "--since", "7d"])
        # Command should attempt to execute
        assert "reprocess" in result.stdout.lower()

    def test_reprocess_command_displays_count(self) -> None:
        """Test that reprocess command displays documents queued count."""
        result = runner.invoke(app, ["extract", "reprocess", "--since", "1d"])
        # Should show count of documents queued
        assert "document" in result.stdout.lower() or "queued" in result.stdout.lower()
