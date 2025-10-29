"""Tests for LocatedInRelationship schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.relationships.located_in import LocatedInRelationship


class TestLocatedInRelationship:
    """Test suite for LocatedInRelationship (Entity → Place)."""

    def test_located_in_relationship_minimal_valid(self) -> None:
        """Test LocatedInRelationship with only required fields."""
        now = datetime.now(UTC)

        rel = LocatedInRelationship(
            created_at=now,
            updated_at=now,
            source="tailscale_reader",
            extractor_version="1.0.0",
        )

        assert rel.created_at == now
        assert rel.updated_at == now
        assert rel.source == "tailscale_reader"
        assert rel.confidence == 1.0
        assert rel.extractor_version == "1.0.0"

    def test_located_in_relationship_full_valid(self) -> None:
        """Test LocatedInRelationship with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        rel = LocatedInRelationship(
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            source="unifi_reader",
            confidence=0.97,
            extractor_version="1.2.0",
        )

        assert rel.source_timestamp == source_time
        assert rel.confidence == 0.97
        assert rel.source == "unifi_reader"

    def test_located_in_relationship_missing_required_created_at(self) -> None:
        """Test LocatedInRelationship validation fails without created_at."""
        with pytest.raises(ValidationError) as exc_info:
            LocatedInRelationship(
                updated_at=datetime.now(UTC),
                source="tailscale_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("created_at",) for e in errors)

    def test_located_in_relationship_missing_required_source(self) -> None:
        """Test LocatedInRelationship validation fails without source."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            LocatedInRelationship(
                created_at=now,
                updated_at=now,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source",) for e in errors)

    def test_located_in_relationship_missing_required_extractor_version(self) -> None:
        """Test LocatedInRelationship validation fails without extractor_version."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            LocatedInRelationship(
                created_at=now,
                updated_at=now,
                source="tailscale_reader",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extractor_version",) for e in errors)

    def test_located_in_relationship_serialization(self) -> None:
        """Test LocatedInRelationship can be serialized to dict."""
        now = datetime.now(UTC)

        rel = LocatedInRelationship(
            created_at=now,
            updated_at=now,
            source="tailscale_reader",
            extractor_version="1.0.0",
        )

        data = rel.model_dump()
        assert data["confidence"] == 1.0
        assert data["source"] == "tailscale_reader"
        assert data["extractor_version"] == "1.0.0"
