"""Tests for Comment entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- ID validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.comment import Comment


class TestCommentEntity:
    """Test suite for Comment entity."""

    def test_comment_minimal_valid(self) -> None:
        """Test Comment with only required fields."""
        now = datetime.now(UTC)
        comment = Comment(
            id=12345,
            author_login="johndoe",
            body="This looks good!",
            comment_created_at=now,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert comment.id == 12345
        assert comment.author_login == "johndoe"
        assert comment.body == "This looks good!"
        assert comment.comment_created_at == now
        assert comment.comment_updated_at is None

    def test_comment_with_update(self) -> None:
        """Test Comment with updated timestamp."""
        now = datetime.now(UTC)
        created_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        updated_time = datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)

        comment = Comment(
            id=12345,
            author_login="johndoe",
            body="This looks good! (edited)",
            comment_created_at=created_time,
            comment_updated_at=updated_time,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert comment.comment_updated_at == updated_time

    def test_comment_missing_required_id(self) -> None:
        """Test Comment validation fails without id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Comment(
                author_login="user",
                body="Test comment",
                comment_created_at=now,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("id",) for e in errors)
