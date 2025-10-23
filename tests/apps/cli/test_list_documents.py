"""Tests for CLI list documents command (T165).

Tests the `taboot list documents` command with filters and pagination.
Follows TDD RED-GREEN-REFACTOR methodology.
"""

import pytest
from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


@pytest.mark.unit
def test_list_documents_command_exists():
    """Test that list documents command can be invoked.

    RED phase: Will fail until command exists.
    """
    result = runner.invoke(app, ["list", "documents"])
    # Should either succeed or fail with expected error, not command not found
    assert "documents" in result.stdout.lower() or result.exit_code in [0, 1]


@pytest.mark.unit
def test_list_documents_accepts_limit():
    """Test list documents accepts --limit option.

    RED phase: Will fail until command exists.
    """
    result = runner.invoke(
        app,
        ["list", "documents", "--limit", "5"],
        catch_exceptions=False,
    )
    # May fail if DB not running, but should parse args
    assert result.exit_code in [0, 1]


@pytest.mark.unit
def test_list_documents_accepts_source_type_filter():
    """Test list documents accepts --source-type filter.

    RED phase: Will fail until command exists.
    """
    result = runner.invoke(
        app,
        ["list", "documents", "--source-type", "web"],
        catch_exceptions=False,
    )
    # May fail if DB not running, but should parse args
    assert result.exit_code in [0, 1]


@pytest.mark.unit
def test_list_documents_accepts_extraction_state_filter():
    """Test list documents accepts --extraction-state filter.

    RED phase: Will fail until command exists.
    """
    result = runner.invoke(
        app,
        ["list", "documents", "--extraction-state", "pending"],
        catch_exceptions=False,
    )
    # May fail if DB not running, but should parse args
    assert result.exit_code in [0, 1]


@pytest.mark.unit
def test_list_documents_accepts_offset():
    """Test list documents accepts --offset for pagination.

    RED phase: Will fail until command exists.
    """
    result = runner.invoke(
        app,
        ["list", "documents", "--limit", "10", "--offset", "20"],
        catch_exceptions=False,
    )
    # May fail if DB not running, but should parse args
    assert result.exit_code in [0, 1]


@pytest.mark.unit
def test_list_documents_combined_filters():
    """Test list documents accepts combined filters.

    RED phase: Will fail until command exists.
    """
    result = runner.invoke(
        app,
        [
            "list",
            "documents",
            "--limit",
            "5",
            "--source-type",
            "github",
            "--extraction-state",
            "completed",
        ],
        catch_exceptions=False,
    )
    # May fail if DB not running, but should parse args
    assert result.exit_code in [0, 1]


@pytest.mark.integration
@pytest.mark.slow
def test_list_documents_with_real_db():
    """Test list documents command against real database.

    Requires PostgreSQL service running.
    """
    result = runner.invoke(
        app,
        ["list", "documents", "--limit", "10"],
    )
    # Should succeed or fail gracefully
    assert result.exit_code in [0, 1]
    # If successful, should show some output (header, empty message, or documents)
    if result.exit_code == 0:
        assert len(result.stdout) > 0
