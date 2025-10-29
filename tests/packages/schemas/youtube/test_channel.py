"""Tests for Channel entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Subscriber count validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.youtube.channel import Channel


class TestChannelEntity:
    """Test suite for Channel entity."""

    def test_channel_minimal_valid(self) -> None:
        """Test Channel with only required fields."""
        now = datetime.now(UTC)

        channel = Channel(
            channel_id="UCxxxxxxxxxxxxx",
            channel_name="Tech Channel",
            channel_url="https://www.youtube.com/channel/UCxxxxxxxxxxxxx",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="youtube_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert channel.channel_id == "UCxxxxxxxxxxxxx"
        assert channel.channel_name == "Tech Channel"
        assert channel.channel_url == "https://www.youtube.com/channel/UCxxxxxxxxxxxxx"
        assert channel.verified is False  # default value
        assert channel.subscribers is None
        assert channel.created_at == now
        assert channel.updated_at == now
        assert channel.extraction_tier == "A"
        assert channel.extraction_method == "youtube_api"
        assert channel.confidence == 1.0
        assert channel.extractor_version == "1.0.0"
        assert channel.source_timestamp is None

    def test_channel_full_valid(self) -> None:
        """Test Channel with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        channel = Channel(
            channel_id="UCyyyyyyyyyyyyyy",
            channel_name="Python Tutorials",
            channel_url="https://www.youtube.com/@pythontutorials",
            subscribers=1000000,
            verified=True,
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="youtube_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert channel.channel_id == "UCyyyyyyyyyyyyyy"
        assert channel.channel_name == "Python Tutorials"
        assert channel.channel_url == "https://www.youtube.com/@pythontutorials"
        assert channel.subscribers == 1000000
        assert channel.verified is True
        assert channel.source_timestamp == source_time

    def test_channel_missing_required_channel_id(self) -> None:
        """Test Channel validation fails without channel_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Channel(
                channel_name="Test Channel",
                channel_url="https://www.youtube.com/channel/test",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("channel_id",) for e in errors)

    def test_channel_missing_required_channel_name(self) -> None:
        """Test Channel validation fails without channel_name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Channel(
                channel_id="UCtest123",
                channel_url="https://www.youtube.com/channel/UCtest123",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("channel_name",) for e in errors)

    def test_channel_missing_required_channel_url(self) -> None:
        """Test Channel validation fails without channel_url."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Channel(
                channel_id="UCtest123",
                channel_name="Test Channel",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("channel_url",) for e in errors)

    def test_channel_negative_subscribers(self) -> None:
        """Test Channel validation fails with negative subscribers."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Channel(
                channel_id="UCtest123",
                channel_name="Test Channel",
                channel_url="https://www.youtube.com/channel/UCtest123",
                subscribers=-100,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("subscribers",) for e in errors)

    def test_channel_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Channel(
                channel_id="UCtest123",
                channel_name="Test Channel",
                channel_url="https://www.youtube.com/channel/UCtest123",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_channel_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Channel(
                channel_id="UCtest123",
                channel_name="Test Channel",
                channel_url="https://www.youtube.com/channel/UCtest123",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.5,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_channel_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            channel = Channel(
                channel_id="UCtest123",
                channel_name="Test Channel",
                channel_url="https://www.youtube.com/channel/UCtest123",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert channel.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Channel(
                channel_id="UCtest123",
                channel_name="Test Channel",
                channel_url="https://www.youtube.com/channel/UCtest123",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_channel_serialization(self) -> None:
        """Test Channel can be serialized to dict."""
        now = datetime.now(UTC)

        channel = Channel(
            channel_id="UCtest123",
            channel_name="Test Channel",
            channel_url="https://www.youtube.com/channel/UCtest123",
            subscribers=50000,
            verified=True,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="youtube_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = channel.model_dump()
        assert data["channel_id"] == "UCtest123"
        assert data["channel_name"] == "Test Channel"
        assert data["channel_url"] == "https://www.youtube.com/channel/UCtest123"
        assert data["subscribers"] == 50000
        assert data["verified"] is True

    def test_channel_deserialization(self) -> None:
        """Test Channel can be deserialized from dict."""
        now = datetime.now(UTC)

        data = {
            "channel_id": "UCtest123",
            "channel_name": "Test Channel",
            "channel_url": "https://www.youtube.com/channel/UCtest123",
            "subscribers": 50000,
            "verified": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "youtube_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        channel = Channel.model_validate(data)
        assert channel.channel_id == "UCtest123"
        assert channel.channel_name == "Test Channel"
        assert channel.subscribers == 50000
        assert channel.verified is True
