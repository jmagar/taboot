"""Tests for Issue entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- State validation
- Integer field validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.issue import Issue


class TestIssueEntity:
    """Test suite for Issue entity."""

    def test_issue_minimal_valid(self) -> None:
        """Test Issue with only required fields."""
        now = datetime.now(UTC)
        issue = Issue(
            repository_full_name="anthropics/claude-code",
            number=42,
            title="Fix bug in parser",
            state="open",
            author_login="johndoe",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert issue.number == 42
        assert issue.title == "Fix bug in parser"
        assert issue.state == "open"
        assert issue.author_login == "johndoe"
        assert issue.body is None
        assert issue.closed_at is None
        assert issue.comments_count is None

    def test_issue_full_valid(self) -> None:
        """Test Issue with all fields populated."""
        now = datetime.now(UTC)
        closed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        issue = Issue(
            repository_full_name="anthropics/claude-code",
            number=42,
            title="Fix bug in parser",
            state="closed",
            body="The parser fails on edge case X",
            author_login="johndoe",
            closed_at=closed_time,
            comments_count=5,
            created_at=now,
            updated_at=now,
            source_timestamp=closed_time,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert issue.body == "The parser fails on edge case X"
        assert issue.closed_at == closed_time
        assert issue.comments_count == 5
        assert issue.state == "closed"

    def test_issue_missing_required_number(self) -> None:
        """Test Issue validation fails without number."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Issue(
                repository_full_name="anthropics/claude-code",
                title="Test Issue",
                state="open",
                author_login="user",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("number",) for e in errors)

    def test_issue_negative_number(self) -> None:
        """Test Issue validation fails with negative number."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Issue(
                repository_full_name="anthropics/claude-code",
                number=-1,
                title="Test Issue",
                state="open",
                author_login="user",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("number",) for e in errors)

    def test_issue_missing_repository_full_name(self) -> None:
        """Test Issue validation fails without repository_full_name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Issue(
                number=1,
                title="Test Issue",
                state="open",
                author_login="user",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("repository_full_name",) for e in errors)
