"""Tests for Event entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Time range validation (start_time <= end_time)
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.core.event import Event


class TestEventEntity:
    """Test suite for Event entity."""

    def test_event_minimal_valid(self) -> None:
        """Test Event with only required fields."""
        now = datetime.now(UTC)
        event = Event(
            name="Team Meeting",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert event.name == "Team Meeting"
        assert event.created_at == now
        assert event.updated_at == now
        assert event.extraction_tier == "A"
        assert event.extraction_method == "gmail_api"
        assert event.confidence == 1.0
        assert event.extractor_version == "1.0.0"
        assert event.start_time is None
        assert event.end_time is None
        assert event.location is None
        assert event.event_type is None
        assert event.source_timestamp is None

    def test_event_full_valid(self) -> None:
        """Test Event with all fields populated."""
        now = datetime.now(UTC)
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)

        event = Event(
            name="Product Launch",
            start_time=start,
            end_time=end,
            location="Conference Room A",
            event_type="meeting",
            created_at=now,
            updated_at=now,
            source_timestamp=start,
            extraction_tier="B",
            extraction_method="spacy_ner",
            confidence=0.90,
            extractor_version="1.2.0",
        )

        assert event.name == "Product Launch"
        assert event.start_time == start
        assert event.end_time == end
        assert event.location == "Conference Room A"
        assert event.event_type == "meeting"
        assert event.source_timestamp == start
        assert event.extraction_tier == "B"
        assert event.confidence == 0.90

    def test_event_missing_required_name(self) -> None:
        """Test Event validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Event(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_event_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Event(
                name="Test Event",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_event_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Event(
                name="Test Event",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_event_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            event = Event(
                name="Test Event",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert event.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Event(
                name="Test Event",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_event_time_range_valid(self) -> None:
        """Test Event with valid time range (start <= end)."""
        now = datetime.now(UTC)
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)

        event = Event(
            name="Test Event",
            start_time=start,
            end_time=end,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="regex",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert event.start_time == start
        assert event.end_time == end

    def test_event_time_range_invalid(self) -> None:
        """Test Event validation fails when end_time < start_time."""
        now = datetime.now(UTC)
        start = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Event(
                name="Test Event",
                start_time=start,
                end_time=end,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        # Validation error should mention time range
        assert len(errors) > 0

    def test_event_serialization(self) -> None:
        """Test Event can be serialized to dict."""
        now = datetime.now(UTC)
        event = Event(
            name="Test Event",
            event_type="release",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="regex",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = event.model_dump()
        assert data["name"] == "Test Event"
        assert data["event_type"] == "release"
        assert data["confidence"] == 1.0

    def test_event_deserialization(self) -> None:
        """Test Event can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "name": "Test Event",
            "event_type": "release",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "regex",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        event = Event.model_validate(data)
        assert event.name == "Test Event"
        assert event.event_type == "release"
