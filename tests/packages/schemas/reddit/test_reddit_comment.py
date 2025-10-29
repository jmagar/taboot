"""Tests for RedditComment entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Comment ID validation
- Depth validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.reddit.reddit_comment import RedditComment


class TestRedditCommentEntity:
    """Test suite for RedditComment entity."""

    def test_reddit_comment_minimal_valid(self) -> None:
        """Test RedditComment with only required fields."""
        now = datetime.now(UTC)
        comment = RedditComment(
            comment_id="def456",
            body="Great question! I recommend starting with the official Python tutorial.",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert comment.comment_id == "def456"
        assert comment.body == "Great question! I recommend starting with the official Python tutorial."
        assert comment.created_at == now
        assert comment.updated_at == now
        assert comment.extraction_tier == "A"
        assert comment.extraction_method == "reddit_api"
        assert comment.confidence == 1.0
        assert comment.extractor_version == "1.0.0"
        assert comment.score is None
        assert comment.created_utc is None
        assert comment.permalink is None
        assert comment.parent_id is None
        assert comment.depth is None
        assert comment.gilded is None
        assert comment.edited is None
        assert comment.source_timestamp is None

    def test_reddit_comment_full_valid(self) -> None:
        """Test RedditComment with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        created_utc = datetime(2024, 1, 1, 11, 0, 0, tzinfo=UTC)

        comment = RedditComment(
            comment_id="def456",
            body="Great question! I recommend starting with the official Python tutorial.",
            score=25,
            created_utc=created_utc,
            permalink="/r/python/comments/abc123/how_to_learn_python/def456/",
            parent_id="abc123",
            depth=1,
            gilded=1,
            edited=False,
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert comment.comment_id == "def456"
        assert comment.body == "Great question! I recommend starting with the official Python tutorial."
        assert comment.score == 25
        assert comment.created_utc == created_utc
        assert comment.permalink == "/r/python/comments/abc123/how_to_learn_python/def456/"
        assert comment.parent_id == "abc123"
        assert comment.depth == 1
        assert comment.gilded == 1
        assert comment.edited is False
        assert comment.source_timestamp == source_time

    def test_reddit_comment_missing_required_comment_id(self) -> None:
        """Test RedditComment validation fails without comment_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditComment(
                body="Great question!",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("comment_id",) for e in errors)

    def test_reddit_comment_missing_required_body(self) -> None:
        """Test RedditComment validation fails without body."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditComment(
                comment_id="def456",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("body",) for e in errors)

    def test_reddit_comment_empty_comment_id(self) -> None:
        """Test RedditComment validation fails with empty comment_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditComment(
                comment_id="",
                body="Great question!",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("comment_id",) for e in errors)

    def test_reddit_comment_empty_body(self) -> None:
        """Test RedditComment validation fails with empty body."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditComment(
                comment_id="def456",
                body="",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("body",) for e in errors)

    def test_reddit_comment_negative_depth(self) -> None:
        """Test RedditComment validation fails with negative depth."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditComment(
                comment_id="def456",
                body="Great question!",
                depth=-1,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("depth",) for e in errors)

    def test_reddit_comment_negative_gilded(self) -> None:
        """Test RedditComment validation fails with negative gilded count."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditComment(
                comment_id="def456",
                body="Great question!",
                gilded=-1,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gilded",) for e in errors)

    def test_reddit_comment_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditComment(
                comment_id="def456",
                body="Great question!",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_reddit_comment_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditComment(
                comment_id="def456",
                body="Great question!",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_reddit_comment_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            comment = RedditComment(
                comment_id="def456",
                body="Great question!",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert comment.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            RedditComment(
                comment_id="def456",
                body="Great question!",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_reddit_comment_serialization(self) -> None:
        """Test RedditComment can be serialized to dict."""
        now = datetime.now(UTC)
        comment = RedditComment(
            comment_id="def456",
            body="Great question!",
            score=25,
            parent_id="abc123",
            depth=1,
            gilded=1,
            edited=False,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = comment.model_dump()
        assert data["comment_id"] == "def456"
        assert data["body"] == "Great question!"
        assert data["score"] == 25
        assert data["parent_id"] == "abc123"
        assert data["depth"] == 1
        assert data["gilded"] == 1
        assert data["edited"] is False
        assert data["confidence"] == 1.0

    def test_reddit_comment_deserialization(self) -> None:
        """Test RedditComment can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "comment_id": "def456",
            "body": "Great question!",
            "score": 25,
            "parent_id": "abc123",
            "depth": 1,
            "gilded": 1,
            "edited": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "reddit_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        comment = RedditComment.model_validate(data)
        assert comment.comment_id == "def456"
        assert comment.body == "Great question!"
        assert comment.score == 25
        assert comment.parent_id == "abc123"
        assert comment.depth == 1
        assert comment.gilded == 1
        assert comment.edited is False
