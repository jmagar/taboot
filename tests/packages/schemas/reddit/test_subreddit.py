"""Tests for Subreddit entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Subreddit name validation
- Subscriber count validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.reddit.subreddit import Subreddit


class TestSubredditEntity:
    """Test suite for Subreddit entity."""

    def test_subreddit_minimal_valid(self) -> None:
        """Test Subreddit with only required fields."""
        now = datetime.now(UTC)
        subreddit = Subreddit(
            name="python",
            display_name="Python",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert subreddit.name == "python"
        assert subreddit.display_name == "Python"
        assert subreddit.created_at == now
        assert subreddit.updated_at == now
        assert subreddit.extraction_tier == "A"
        assert subreddit.extraction_method == "reddit_api"
        assert subreddit.confidence == 1.0
        assert subreddit.extractor_version == "1.0.0"
        assert subreddit.description is None
        assert subreddit.subscribers is None
        assert subreddit.created_utc is None
        assert subreddit.over_18 is None
        assert subreddit.source_timestamp is None

    def test_subreddit_full_valid(self) -> None:
        """Test Subreddit with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        created_utc = datetime(2008, 1, 25, 0, 0, 0, tzinfo=UTC)

        subreddit = Subreddit(
            name="python",
            display_name="Python",
            description="News about the dynamic, interpreted programming language Python.",
            subscribers=1500000,
            created_utc=created_utc,
            over_18=False,
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert subreddit.name == "python"
        assert subreddit.display_name == "Python"
        assert subreddit.description == "News about the dynamic, interpreted programming language Python."
        assert subreddit.subscribers == 1500000
        assert subreddit.created_utc == created_utc
        assert subreddit.over_18 is False
        assert subreddit.source_timestamp == source_time

    def test_subreddit_missing_required_name(self) -> None:
        """Test Subreddit validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Subreddit(
                display_name="Python",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_subreddit_missing_required_display_name(self) -> None:
        """Test Subreddit validation fails without display_name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Subreddit(
                name="python",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("display_name",) for e in errors)

    def test_subreddit_empty_name(self) -> None:
        """Test Subreddit validation fails with empty name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Subreddit(
                name="",
                display_name="Python",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_subreddit_negative_subscribers(self) -> None:
        """Test Subreddit validation fails with negative subscribers."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Subreddit(
                name="python",
                display_name="Python",
                subscribers=-100,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("subscribers",) for e in errors)

    def test_subreddit_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Subreddit(
                name="python",
                display_name="Python",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_subreddit_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Subreddit(
                name="python",
                display_name="Python",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_subreddit_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            subreddit = Subreddit(
                name="python",
                display_name="Python",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert subreddit.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Subreddit(
                name="python",
                display_name="Python",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_subreddit_serialization(self) -> None:
        """Test Subreddit can be serialized to dict."""
        now = datetime.now(UTC)
        subreddit = Subreddit(
            name="python",
            display_name="Python",
            description="Python programming",
            subscribers=1500000,
            over_18=False,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = subreddit.model_dump()
        assert data["name"] == "python"
        assert data["display_name"] == "Python"
        assert data["description"] == "Python programming"
        assert data["subscribers"] == 1500000
        assert data["over_18"] is False
        assert data["confidence"] == 1.0

    def test_subreddit_deserialization(self) -> None:
        """Test Subreddit can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "name": "python",
            "display_name": "Python",
            "description": "Python programming",
            "subscribers": 1500000,
            "over_18": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "reddit_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        subreddit = Subreddit.model_validate(data)
        assert subreddit.name == "python"
        assert subreddit.display_name == "Python"
        assert subreddit.description == "Python programming"
        assert subreddit.subscribers == 1500000
        assert subreddit.over_18 is False
