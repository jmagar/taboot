"""Tests for WorksAtRelationship schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.relationships.works_at import WorksAtRelationship


class TestWorksAtRelationship:
    """Test suite for WorksAtRelationship (Person → Organization)."""

    def test_works_at_relationship_minimal_valid(self) -> None:
        """Test WorksAtRelationship with only required fields from base."""
        now = datetime.now(UTC)

        rel = WorksAtRelationship(
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )

        assert rel.created_at == now
        assert rel.source == "github_reader"
        assert rel.confidence == 1.0
        assert rel.extractor_version == "1.0.0"
        assert rel.role is None
        assert rel.start_date is None
        assert rel.end_date is None

    def test_works_at_relationship_with_role(self) -> None:
        """Test WorksAtRelationship with role specified."""
        now = datetime.now(UTC)

        rel = WorksAtRelationship(
            role="Senior Engineer",
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )

        assert rel.role == "Senior Engineer"
        assert rel.start_date is None
        assert rel.end_date is None

    def test_works_at_relationship_full_valid(self) -> None:
        """Test WorksAtRelationship with all fields populated."""
        now = datetime.now(UTC)
        start = datetime(2020, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)

        rel = WorksAtRelationship(
            role="Product Manager",
            start_date=start,
            end_date=end,
            created_at=now,
            source_timestamp=start,
            source="linkedin_reader",
            confidence=0.95,
            extractor_version="1.2.0",
        )

        assert rel.role == "Product Manager"
        assert rel.start_date == start
        assert rel.end_date == end
        assert rel.source_timestamp == start
        assert rel.confidence == 0.95

    def test_works_at_relationship_current_employment(self) -> None:
        """Test WorksAtRelationship for current employment (no end_date)."""
        now = datetime.now(UTC)
        start = datetime(2023, 6, 1, tzinfo=UTC)

        rel = WorksAtRelationship(
            role="CTO",
            start_date=start,
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )

        assert rel.role == "CTO"
        assert rel.start_date == start
        assert rel.end_date is None

    def test_works_at_relationship_missing_required_created_at(self) -> None:
        """Test WorksAtRelationship validation fails without created_at."""
        with pytest.raises(ValidationError) as exc_info:
            WorksAtRelationship(
                role="Engineer",
                source="github_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("created_at",) for e in errors)

    def test_works_at_relationship_missing_required_source(self) -> None:
        """Test WorksAtRelationship validation fails without source."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            WorksAtRelationship(
                role="Engineer",
                created_at=now,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source",) for e in errors)

    def test_works_at_relationship_missing_required_extractor_version(self) -> None:
        """Test WorksAtRelationship validation fails without extractor_version."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            WorksAtRelationship(
                role="Engineer",
                created_at=now,
                source="github_reader",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extractor_version",) for e in errors)

    def test_works_at_relationship_serialization(self) -> None:
        """Test WorksAtRelationship can be serialized to dict."""
        now = datetime.now(UTC)
        start = datetime(2020, 1, 1, tzinfo=UTC)

        rel = WorksAtRelationship(
            role="Senior Engineer",
            start_date=start,
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )

        data = rel.model_dump()
        assert data["role"] == "Senior Engineer"
        assert data["start_date"] == start
        assert data["end_date"] is None
        assert data["confidence"] == 1.0
