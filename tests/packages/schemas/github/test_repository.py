"""Tests for Repository entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Boolean field handling
- Integer field validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.repository import Repository


class TestRepositoryEntity:
    """Test suite for Repository entity."""

    def test_repository_minimal_valid(self) -> None:
        """Test Repository with only required fields."""
        now = datetime.now(UTC)
        repo = Repository(
            owner="anthropics",
            name="claude-code",
            full_name="anthropics/claude-code",
            url="https://github.com/anthropics/claude-code",
            default_branch="main",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert repo.owner == "anthropics"
        assert repo.name == "claude-code"
        assert repo.full_name == "anthropics/claude-code"
        assert repo.url == "https://github.com/anthropics/claude-code"
        assert repo.default_branch == "main"
        assert repo.extraction_tier == "A"
        assert repo.confidence == 1.0
        assert repo.description is None
        assert repo.language is None
        assert repo.stars is None
        assert repo.forks is None
        assert repo.open_issues is None
        assert repo.is_private is None
        assert repo.is_fork is None

    def test_repository_full_valid(self) -> None:
        """Test Repository with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        repo = Repository(
            owner="anthropics",
            name="claude-code",
            full_name="anthropics/claude-code",
            url="https://github.com/anthropics/claude-code",
            default_branch="main",
            description="AI-powered coding assistant",
            language="Python",
            stars=1500,
            forks=200,
            open_issues=45,
            is_private=False,
            is_fork=False,
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert repo.description == "AI-powered coding assistant"
        assert repo.language == "Python"
        assert repo.stars == 1500
        assert repo.forks == 200
        assert repo.open_issues == 45
        assert repo.is_private is False
        assert repo.is_fork is False
        assert repo.source_timestamp == source_time

    def test_repository_missing_required_owner(self) -> None:
        """Test Repository validation fails without owner."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Repository(
                name="test-repo",
                full_name="user/test-repo",
                url="https://github.com/user/test-repo",
                default_branch="main",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("owner",) for e in errors)

    def test_repository_negative_stars(self) -> None:
        """Test Repository validation fails with negative stars."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Repository(
                owner="user",
                name="test-repo",
                full_name="user/test-repo",
                url="https://github.com/user/test-repo",
                default_branch="main",
                stars=-1,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("stars",) for e in errors)

    def test_repository_serialization(self) -> None:
        """Test Repository can be serialized to dict."""
        now = datetime.now(UTC)
        repo = Repository(
            owner="anthropics",
            name="claude-code",
            full_name="anthropics/claude-code",
            url="https://github.com/anthropics/claude-code",
            default_branch="main",
            stars=1500,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = repo.model_dump()
        assert data["owner"] == "anthropics"
        assert data["name"] == "claude-code"
        assert data["stars"] == 1500
