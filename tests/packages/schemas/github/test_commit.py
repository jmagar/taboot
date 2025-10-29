"""Tests for Commit entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- SHA validation
- List field handling
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.commit import Commit


class TestCommitEntity:
    """Test suite for Commit entity."""

    def test_commit_minimal_valid(self) -> None:
        """Test Commit with only required fields."""
        now = datetime.now(UTC)
        commit_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        commit = Commit(
            sha="abc123def456",
            message="Fix bug in parser",
            author_name="John Doe",
            author_email="john@example.com",
            timestamp=commit_time,
            tree_sha="tree123abc",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert commit.sha == "abc123def456"
        assert commit.message == "Fix bug in parser"
        assert commit.author_name == "John Doe"
        assert commit.author_email == "john@example.com"
        assert commit.timestamp == commit_time
        assert commit.tree_sha == "tree123abc"
        assert commit.author_login is None
        assert commit.parent_shas is None
        assert commit.additions is None
        assert commit.deletions is None

    def test_commit_full_valid(self) -> None:
        """Test Commit with all fields populated."""
        now = datetime.now(UTC)
        commit_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        commit = Commit(
            sha="abc123def456",
            message="Fix bug in parser",
            author_login="johndoe",
            author_name="John Doe",
            author_email="john@example.com",
            timestamp=commit_time,
            tree_sha="tree123abc",
            parent_shas=["parent1abc", "parent2def"],
            additions=150,
            deletions=50,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert commit.author_login == "johndoe"
        assert commit.parent_shas == ["parent1abc", "parent2def"]
        assert commit.additions == 150
        assert commit.deletions == 50

    def test_commit_missing_required_sha(self) -> None:
        """Test Commit validation fails without sha."""
        now = datetime.now(UTC)
        commit_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Commit(
                message="Test commit",
                author_name="Test User",
                author_email="test@example.com",
                timestamp=commit_time,
                tree_sha="tree123",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("sha",) for e in errors)

    def test_commit_negative_additions(self) -> None:
        """Test Commit validation fails with negative additions."""
        now = datetime.now(UTC)
        commit_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Commit(
                sha="abc123",
                message="Test",
                author_name="Test",
                author_email="test@example.com",
                timestamp=commit_time,
                tree_sha="tree123",
                additions=-1,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("additions",) for e in errors)
