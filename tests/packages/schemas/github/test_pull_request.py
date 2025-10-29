"""Tests for PullRequest entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- State and merge validation
- Integer field validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.pull_request import PullRequest


class TestPullRequestEntity:
    """Test suite for PullRequest entity."""

    def test_pull_request_minimal_valid(self) -> None:
        """Test PullRequest with only required fields."""
        now = datetime.now(UTC)
        pr = PullRequest(
            number=123,
            title="Add new feature",
            state="open",
            base_branch="main",
            head_branch="feature/new-thing",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert pr.number == 123
        assert pr.title == "Add new feature"
        assert pr.state == "open"
        assert pr.base_branch == "main"
        assert pr.head_branch == "feature/new-thing"
        assert pr.merged is None
        assert pr.merged_at is None
        assert pr.commits is None
        assert pr.additions is None
        assert pr.deletions is None

    def test_pull_request_merged(self) -> None:
        """Test PullRequest with merge information."""
        now = datetime.now(UTC)
        merged_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        pr = PullRequest(
            number=123,
            title="Add new feature",
            state="closed",
            base_branch="main",
            head_branch="feature/new-thing",
            merged=True,
            merged_at=merged_time,
            commits=5,
            additions=250,
            deletions=50,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert pr.merged is True
        assert pr.merged_at == merged_time
        assert pr.commits == 5
        assert pr.additions == 250
        assert pr.deletions == 50

    def test_pull_request_missing_required_base_branch(self) -> None:
        """Test PullRequest validation fails without base_branch."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            PullRequest(
                number=123,
                title="Test PR",
                state="open",
                head_branch="feature/test",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("base_branch",) for e in errors)

    def test_pull_request_negative_commits(self) -> None:
        """Test PullRequest validation fails with negative commits."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            PullRequest(
                number=123,
                title="Test PR",
                state="open",
                base_branch="main",
                head_branch="feature/test",
                commits=-1,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("commits",) for e in errors)
