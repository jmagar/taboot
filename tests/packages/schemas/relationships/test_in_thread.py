"""Tests for InThreadRelationship schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.relationships.in_thread import InThreadRelationship


class TestInThreadRelationship:
    """Test suite for InThreadRelationship (Email → Thread)."""

    def test_in_thread_relationship_minimal_valid(self) -> None:
        """Test InThreadRelationship with only required fields."""
        now = datetime.now(UTC)

        rel = InThreadRelationship(
            created_at=now,
            source="gmail_reader",
            extractor_version="1.0.0",
        )

        assert rel.created_at == now
        assert rel.source == "gmail_reader"
        assert rel.confidence == 1.0
        assert rel.extractor_version == "1.0.0"

    def test_in_thread_relationship_full_valid(self) -> None:
        """Test InThreadRelationship with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        rel = InThreadRelationship(
            created_at=now,
            source_timestamp=source_time,
            source="gmail_reader",
            confidence=0.99,
            extractor_version="1.2.0",
        )

        assert rel.source_timestamp == source_time
        assert rel.confidence == 0.99

    def test_in_thread_relationship_missing_required_created_at(self) -> None:
        """Test InThreadRelationship validation fails without created_at."""
        with pytest.raises(ValidationError) as exc_info:
            InThreadRelationship(
                source="gmail_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("created_at",) for e in errors)

    def test_in_thread_relationship_missing_required_source(self) -> None:
        """Test InThreadRelationship validation fails without source."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            InThreadRelationship(
                created_at=now,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source",) for e in errors)

    def test_in_thread_relationship_missing_required_extractor_version(self) -> None:
        """Test InThreadRelationship validation fails without extractor_version."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            InThreadRelationship(
                created_at=now,
                source="gmail_reader",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extractor_version",) for e in errors)

    def test_in_thread_relationship_serialization(self) -> None:
        """Test InThreadRelationship can be serialized to dict."""
        now = datetime.now(UTC)

        rel = InThreadRelationship(
            created_at=now,
            source="gmail_reader",
            extractor_version="1.0.0",
        )

        data = rel.model_dump()
        assert data["confidence"] == 1.0
        assert data["source"] == "gmail_reader"
        assert data["extractor_version"] == "1.0.0"
