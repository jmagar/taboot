"""Tests for Tag entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.tag import Tag


class TestTagEntity:
    """Test suite for Tag entity."""

    def test_tag_minimal_valid(self) -> None:
        """Test Tag with only required fields."""
        now = datetime.now(UTC)
        tag = Tag(
            name="v1.0.0",
            sha="abc123def456",
            ref="refs/tags/v1.0.0",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert tag.name == "v1.0.0"
        assert tag.sha == "abc123def456"
        assert tag.ref == "refs/tags/v1.0.0"
        assert tag.message is None
        assert tag.tagger is None

    def test_tag_with_message(self) -> None:
        """Test Tag with message and tagger."""
        now = datetime.now(UTC)
        tag = Tag(
            name="v1.0.0",
            sha="abc123def456",
            ref="refs/tags/v1.0.0",
            message="Release version 1.0.0",
            tagger="johndoe",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert tag.message == "Release version 1.0.0"
        assert tag.tagger == "johndoe"

    def test_tag_missing_required_name(self) -> None:
        """Test Tag validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Tag(
                sha="abc123",
                ref="refs/tags/test",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)
