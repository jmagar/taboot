"""Tests for CreatedRelationship schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.relationships.created import CreatedRelationship


class TestCreatedRelationship:
    """Test suite for CreatedRelationship (Person → File)."""

    def test_created_relationship_minimal_valid(self) -> None:
        """Test CreatedRelationship with only required fields."""
        now = datetime.now(UTC)

        rel = CreatedRelationship(
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )

        assert rel.created_at == now
        assert rel.source == "github_reader"
        assert rel.confidence == 1.0
        assert rel.extractor_version == "1.0.0"

    def test_created_relationship_full_valid(self) -> None:
        """Test CreatedRelationship with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        rel = CreatedRelationship(
            created_at=now,
            source_timestamp=source_time,
            source="github_reader",
            confidence=0.95,
            extractor_version="1.2.0",
        )

        assert rel.source_timestamp == source_time
        assert rel.confidence == 0.95

    def test_created_relationship_missing_required_created_at(self) -> None:
        """Test CreatedRelationship validation fails without created_at."""
        with pytest.raises(ValidationError) as exc_info:
            CreatedRelationship(
                source="github_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("created_at",) for e in errors)

    def test_created_relationship_missing_required_source(self) -> None:
        """Test CreatedRelationship validation fails without source."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            CreatedRelationship(
                created_at=now,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source",) for e in errors)

    def test_created_relationship_missing_required_extractor_version(self) -> None:
        """Test CreatedRelationship validation fails without extractor_version."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            CreatedRelationship(
                created_at=now,
                source="github_reader",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extractor_version",) for e in errors)

    def test_created_relationship_serialization(self) -> None:
        """Test CreatedRelationship can be serialized to dict."""
        now = datetime.now(UTC)

        rel = CreatedRelationship(
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )

        data = rel.model_dump()
        assert data["confidence"] == 1.0
        assert data["source"] == "github_reader"
        assert data["extractor_version"] == "1.0.0"
