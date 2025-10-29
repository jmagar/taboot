"""Tests for SentRelationship schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.relationships.sent import SentRelationship


class TestSentRelationship:
    """Test suite for SentRelationship (Person → Email)."""

    def test_sent_relationship_minimal_valid(self) -> None:
        """Test SentRelationship with only required fields."""
        now = datetime.now(UTC)
        sent_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        rel = SentRelationship(
            sent_at=sent_time,
            created_at=now,
            source="gmail_reader",
            extractor_version="1.0.0",
        )

        assert rel.sent_at == sent_time
        assert rel.created_at == now
        assert rel.source == "gmail_reader"
        assert rel.confidence == 1.0
        assert rel.extractor_version == "1.0.0"

    def test_sent_relationship_full_valid(self) -> None:
        """Test SentRelationship with all fields populated."""
        now = datetime.now(UTC)
        sent_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        source_time = datetime(2024, 1, 15, 10, 5, 0, tzinfo=UTC)

        rel = SentRelationship(
            sent_at=sent_time,
            created_at=now,
            source_timestamp=source_time,
            source="gmail_reader",
            confidence=0.99,
            extractor_version="1.2.0",
        )

        assert rel.sent_at == sent_time
        assert rel.source_timestamp == source_time
        assert rel.confidence == 0.99

    def test_sent_relationship_with_timezone(self) -> None:
        """Test SentRelationship with different timezone."""
        now = datetime.now(UTC)
        sent_time = datetime(2024, 6, 1, 14, 30, 0, tzinfo=UTC)

        rel = SentRelationship(
            sent_at=sent_time,
            created_at=now,
            source="gmail_reader",
            extractor_version="1.0.0",
        )

        assert rel.sent_at.year == 2024
        assert rel.sent_at.month == 6
        assert rel.sent_at.day == 1
        assert rel.sent_at.hour == 14

    def test_sent_relationship_missing_required_sent_at(self) -> None:
        """Test SentRelationship validation fails without sent_at."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            SentRelationship(
                created_at=now,
                source="gmail_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("sent_at",) for e in errors)

    def test_sent_relationship_missing_required_created_at(self) -> None:
        """Test SentRelationship validation fails without created_at."""
        sent_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            SentRelationship(
                sent_at=sent_time,
                source="gmail_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("created_at",) for e in errors)

    def test_sent_relationship_missing_required_source(self) -> None:
        """Test SentRelationship validation fails without source."""
        now = datetime.now(UTC)
        sent_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            SentRelationship(
                sent_at=sent_time,
                created_at=now,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source",) for e in errors)

    def test_sent_relationship_missing_required_extractor_version(self) -> None:
        """Test SentRelationship validation fails without extractor_version."""
        now = datetime.now(UTC)
        sent_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            SentRelationship(
                sent_at=sent_time,
                created_at=now,
                source="gmail_reader",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extractor_version",) for e in errors)

    def test_sent_relationship_serialization(self) -> None:
        """Test SentRelationship can be serialized to dict."""
        now = datetime.now(UTC)
        sent_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        rel = SentRelationship(
            sent_at=sent_time,
            created_at=now,
            source="gmail_reader",
            extractor_version="1.0.0",
        )

        data = rel.model_dump()
        assert data["sent_at"] == sent_time
        assert data["confidence"] == 1.0
        assert data["source"] == "gmail_reader"
