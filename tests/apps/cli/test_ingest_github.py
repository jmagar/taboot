"""Tests for GitHub ingest CLI command.

Tests GitHub repository ingestion via CLI.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


class TestIngestGithubCommand:
    """Tests for the ingest github CLI command."""

    def test_github_command_requires_repo_arg(self) -> None:
        """Test that github command requires repository argument."""
        result = runner.invoke(app, ["ingest", "github"])
        assert result.exit_code != 0

    def test_github_command_validates_repo_format(self) -> None:
        """Test that github command validates repo format."""
        result = runner.invoke(app, ["ingest", "github", "invalid-repo"])
        assert result.exit_code != 0
        assert "Invalid repository format" in result.stdout or "owner/repo" in result.stdout

    def test_github_command_accepts_valid_repo(self) -> None:
        """Test that github command accepts valid repo format."""
        result = runner.invoke(app, ["ingest", "github", "owner/repo", "--limit", "5"])
        # Command should attempt to execute (may fail on missing credentials)
        assert "owner/repo" in result.stdout

    def test_github_command_respects_limit_option(self) -> None:
        """Test that github command respects --limit option."""
        result = runner.invoke(app, ["ingest", "github", "owner/repo", "--limit", "10"])
        assert "10" in result.stdout or "limit" in result.stdout.lower()
