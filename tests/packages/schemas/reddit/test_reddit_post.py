"""Tests for RedditPost entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Post ID validation
- Score validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.reddit.reddit_post import RedditPost


class TestRedditPostEntity:
    """Test suite for RedditPost entity."""

    def test_reddit_post_minimal_valid(self) -> None:
        """Test RedditPost with only required fields."""
        now = datetime.now(UTC)
        post = RedditPost(
            post_id="abc123",
            title="How to learn Python?",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert post.post_id == "abc123"
        assert post.title == "How to learn Python?"
        assert post.created_at == now
        assert post.updated_at == now
        assert post.extraction_tier == "A"
        assert post.extraction_method == "reddit_api"
        assert post.confidence == 1.0
        assert post.extractor_version == "1.0.0"
        assert post.selftext is None
        assert post.score is None
        assert post.num_comments is None
        assert post.created_utc is None
        assert post.url is None
        assert post.permalink is None
        assert post.is_self is None
        assert post.over_18 is None
        assert post.gilded is None
        assert post.source_timestamp is None

    def test_reddit_post_full_valid(self) -> None:
        """Test RedditPost with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        created_utc = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)

        post = RedditPost(
            post_id="abc123",
            title="How to learn Python?",
            selftext="I'm new to programming and want to learn Python. Any suggestions?",
            score=150,
            num_comments=42,
            created_utc=created_utc,
            url="https://reddit.com/r/python/comments/abc123/how_to_learn_python/",
            permalink="/r/python/comments/abc123/how_to_learn_python/",
            is_self=True,
            over_18=False,
            gilded=2,
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert post.post_id == "abc123"
        assert post.title == "How to learn Python?"
        assert post.selftext == "I'm new to programming and want to learn Python. Any suggestions?"
        assert post.score == 150
        assert post.num_comments == 42
        assert post.created_utc == created_utc
        assert post.url == "https://reddit.com/r/python/comments/abc123/how_to_learn_python/"
        assert post.permalink == "/r/python/comments/abc123/how_to_learn_python/"
        assert post.is_self is True
        assert post.over_18 is False
        assert post.gilded == 2
        assert post.source_timestamp == source_time

    def test_reddit_post_missing_required_post_id(self) -> None:
        """Test RedditPost validation fails without post_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditPost(
                title="How to learn Python?",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("post_id",) for e in errors)

    def test_reddit_post_missing_required_title(self) -> None:
        """Test RedditPost validation fails without title."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditPost(
                post_id="abc123",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_reddit_post_empty_post_id(self) -> None:
        """Test RedditPost validation fails with empty post_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditPost(
                post_id="",
                title="How to learn Python?",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("post_id",) for e in errors)

    def test_reddit_post_empty_title(self) -> None:
        """Test RedditPost validation fails with empty title."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditPost(
                post_id="abc123",
                title="",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_reddit_post_negative_num_comments(self) -> None:
        """Test RedditPost validation fails with negative num_comments."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditPost(
                post_id="abc123",
                title="How to learn Python?",
                num_comments=-5,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("num_comments",) for e in errors)

    def test_reddit_post_negative_gilded(self) -> None:
        """Test RedditPost validation fails with negative gilded count."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditPost(
                post_id="abc123",
                title="How to learn Python?",
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

    def test_reddit_post_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditPost(
                post_id="abc123",
                title="How to learn Python?",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_reddit_post_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RedditPost(
                post_id="abc123",
                title="How to learn Python?",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_reddit_post_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            post = RedditPost(
                post_id="abc123",
                title="How to learn Python?",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert post.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            RedditPost(
                post_id="abc123",
                title="How to learn Python?",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_reddit_post_serialization(self) -> None:
        """Test RedditPost can be serialized to dict."""
        now = datetime.now(UTC)
        post = RedditPost(
            post_id="abc123",
            title="How to learn Python?",
            selftext="I'm new to programming",
            score=150,
            num_comments=42,
            is_self=True,
            over_18=False,
            gilded=2,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = post.model_dump()
        assert data["post_id"] == "abc123"
        assert data["title"] == "How to learn Python?"
        assert data["selftext"] == "I'm new to programming"
        assert data["score"] == 150
        assert data["num_comments"] == 42
        assert data["is_self"] is True
        assert data["over_18"] is False
        assert data["gilded"] == 2
        assert data["confidence"] == 1.0

    def test_reddit_post_deserialization(self) -> None:
        """Test RedditPost can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "post_id": "abc123",
            "title": "How to learn Python?",
            "selftext": "I'm new to programming",
            "score": 150,
            "num_comments": 42,
            "is_self": True,
            "over_18": False,
            "gilded": 2,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "reddit_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        post = RedditPost.model_validate(data)
        assert post.post_id == "abc123"
        assert post.title == "How to learn Python?"
        assert post.selftext == "I'm new to programming"
        assert post.score == 150
        assert post.num_comments == 42
        assert post.is_self is True
        assert post.over_18 is False
        assert post.gilded == 2
