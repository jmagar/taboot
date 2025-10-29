"""Tests for BaseRelationship schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking
- Confidence validation (0.0-1.0 range)
- Serialization and deserialization
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.relationships.base import BaseRelationship


class TestBaseRelationship:
    """Test suite for BaseRelationship."""

    def test_base_relationship_minimal_valid(self) -> None:
        """Test BaseRelationship with only required fields."""
        now = datetime.now(UTC)
        rel = BaseRelationship(
            created_at=now,
            source="job_12345",
            extractor_version="1.0.0",
        )

        assert rel.created_at == now
        assert rel.source_timestamp is None
        assert rel.source == "job_12345"
        assert rel.confidence == 1.0  # Default value
        assert rel.extractor_version == "1.0.0"

    def test_base_relationship_full_valid(self) -> None:
        """Test BaseRelationship with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        rel = BaseRelationship(
            created_at=now,
            source_timestamp=source_time,
            source="github_reader",
            confidence=0.85,
            extractor_version="1.2.0",
        )

        assert rel.created_at == now
        assert rel.source_timestamp == source_time
        assert rel.source == "github_reader"
        assert rel.confidence == 0.85
        assert rel.extractor_version == "1.2.0"

    def test_base_relationship_missing_required_created_at(self) -> None:
        """Test BaseRelationship validation fails without created_at."""
        with pytest.raises(ValidationError) as exc_info:
            BaseRelationship(
                source="job_12345",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("created_at",) for e in errors)

    def test_base_relationship_missing_required_source(self) -> None:
        """Test BaseRelationship validation fails without source."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BaseRelationship(
                created_at=now,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source",) for e in errors)

    def test_base_relationship_missing_required_extractor_version(self) -> None:
        """Test BaseRelationship validation fails without extractor_version."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BaseRelationship(
                created_at=now,
                source="job_12345",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extractor_version",) for e in errors)

    def test_base_relationship_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BaseRelationship(
                created_at=now,
                source="job_12345",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_base_relationship_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BaseRelationship(
                created_at=now,
                source="job_12345",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_base_relationship_confidence_default(self) -> None:
        """Test confidence defaults to 1.0."""
        now = datetime.now(UTC)
        rel = BaseRelationship(
            created_at=now,
            source="job_12345",
            extractor_version="1.0.0",
        )

        assert rel.confidence == 1.0

    def test_base_relationship_serialization(self) -> None:
        """Test BaseRelationship can be serialized to dict."""
        now = datetime.now(UTC)
        rel = BaseRelationship(
            created_at=now,
            source="job_12345",
            confidence=0.90,
            extractor_version="1.0.0",
        )

        data = rel.model_dump()
        assert data["source"] == "job_12345"
        assert data["confidence"] == 0.90
        assert data["extractor_version"] == "1.0.0"

    def test_base_relationship_deserialization(self) -> None:
        """Test BaseRelationship can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "created_at": now.isoformat(),
            "source": "job_12345",
            "confidence": 0.90,
            "extractor_version": "1.0.0",
        }

        rel = BaseRelationship.model_validate(data)
        assert rel.source == "job_12345"
        assert rel.confidence == 0.90
        assert rel.extractor_version == "1.0.0"
