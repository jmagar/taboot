"""Tests for GitHubLabel entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Color format validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.github_label import GitHubLabel


class TestGitHubLabelEntity:
    """Test suite for GitHubLabel entity."""

    def test_label_minimal_valid(self) -> None:
        """Test GitHubLabel with only required fields."""
        now = datetime.now(UTC)
        label = GitHubLabel(
            name="bug",
            color="ff0000",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert label.name == "bug"
        assert label.color == "ff0000"
        assert label.description is None

    def test_label_with_description(self) -> None:
        """Test GitHubLabel with description."""
        now = datetime.now(UTC)
        label = GitHubLabel(
            name="bug",
            color="ff0000",
            description="Something isn't working",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert label.description == "Something isn't working"

    def test_label_missing_required_name(self) -> None:
        """Test GitHubLabel validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            GitHubLabel(
                color="ff0000",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)
