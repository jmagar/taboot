"""Tests for Video entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Video ID validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.youtube.video import Video


class TestVideoEntity:
    """Test suite for Video entity."""

    def test_video_minimal_valid(self) -> None:
        """Test Video with only required fields."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        video = Video(
            video_id="dQw4w9WgXcQ",
            title="Test Video Title",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            duration=300,
            views=1000000,
            published_at=published,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="youtube_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert video.video_id == "dQw4w9WgXcQ"
        assert video.title == "Test Video Title"
        assert video.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert video.duration == 300
        assert video.views == 1000000
        assert video.published_at == published
        assert video.created_at == now
        assert video.updated_at == now
        assert video.extraction_tier == "A"
        assert video.extraction_method == "youtube_api"
        assert video.confidence == 1.0
        assert video.extractor_version == "1.0.0"
        assert video.description is None
        assert video.language is None
        assert video.source_timestamp is None

    def test_video_full_valid(self) -> None:
        """Test Video with all fields populated."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        source_time = datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)

        video = Video(
            video_id="dQw4w9WgXcQ",
            title="Complete Test Video",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            duration=300,
            views=1000000,
            published_at=published,
            description="This is a test video description with details",
            language="en",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="youtube_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert video.video_id == "dQw4w9WgXcQ"
        assert video.title == "Complete Test Video"
        assert video.description == "This is a test video description with details"
        assert video.language == "en"
        assert video.source_timestamp == source_time

    def test_video_missing_required_video_id(self) -> None:
        """Test Video validation fails without video_id."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Video(
                title="Test Video",
                url="https://www.youtube.com/watch?v=test",
                duration=300,
                views=1000,
                published_at=published,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("video_id",) for e in errors)

    def test_video_missing_required_title(self) -> None:
        """Test Video validation fails without title."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Video(
                video_id="test123",
                url="https://www.youtube.com/watch?v=test123",
                duration=300,
                views=1000,
                published_at=published,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_video_negative_duration(self) -> None:
        """Test Video validation fails with negative duration."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Video(
                video_id="test123",
                title="Test Video",
                url="https://www.youtube.com/watch?v=test123",
                duration=-100,
                views=1000,
                published_at=published,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("duration",) for e in errors)

    def test_video_negative_views(self) -> None:
        """Test Video validation fails with negative views."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Video(
                video_id="test123",
                title="Test Video",
                url="https://www.youtube.com/watch?v=test123",
                duration=300,
                views=-100,
                published_at=published,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("views",) for e in errors)

    def test_video_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Video(
                video_id="test123",
                title="Test Video",
                url="https://www.youtube.com/watch?v=test123",
                duration=300,
                views=1000,
                published_at=published,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_video_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Video(
                video_id="test123",
                title="Test Video",
                url="https://www.youtube.com/watch?v=test123",
                duration=300,
                views=1000,
                published_at=published,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.5,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_video_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            video = Video(
                video_id="test123",
                title="Test Video",
                url="https://www.youtube.com/watch?v=test123",
                duration=300,
                views=1000,
                published_at=published,
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert video.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Video(
                video_id="test123",
                title="Test Video",
                url="https://www.youtube.com/watch?v=test123",
                duration=300,
                views=1000,
                published_at=published,
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_video_serialization(self) -> None:
        """Test Video can be serialized to dict."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        video = Video(
            video_id="test123",
            title="Test Video",
            url="https://www.youtube.com/watch?v=test123",
            duration=300,
            views=1000,
            published_at=published,
            description="Test description",
            language="en",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="youtube_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = video.model_dump()
        assert data["video_id"] == "test123"
        assert data["title"] == "Test Video"
        assert data["duration"] == 300
        assert data["views"] == 1000
        assert data["description"] == "Test description"
        assert data["language"] == "en"

    def test_video_deserialization(self) -> None:
        """Test Video can be deserialized from dict."""
        now = datetime.now(UTC)
        published = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        data = {
            "video_id": "test123",
            "title": "Test Video",
            "url": "https://www.youtube.com/watch?v=test123",
            "duration": 300,
            "views": 1000,
            "published_at": published.isoformat(),
            "description": "Test description",
            "language": "en",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "youtube_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        video = Video.model_validate(data)
        assert video.video_id == "test123"
        assert video.title == "Test Video"
        assert video.duration == 300
        assert video.views == 1000
        assert video.description == "Test description"
        assert video.language == "en"
