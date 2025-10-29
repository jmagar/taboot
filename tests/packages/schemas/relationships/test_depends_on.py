"""Tests for DependsOnRelationship schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.relationships.depends_on import DependsOnRelationship


class TestDependsOnRelationship:
    """Test suite for DependsOnRelationship (Service → Service)."""

    def test_depends_on_relationship_minimal_valid(self) -> None:
        """Test DependsOnRelationship with only required fields."""
        now = datetime.now(UTC)

        rel = DependsOnRelationship(
            condition="service_started",
            created_at=now,
            source="docker_compose_reader",
            extractor_version="1.0.0",
        )

        assert rel.condition == "service_started"
        assert rel.created_at == now
        assert rel.source == "docker_compose_reader"
        assert rel.confidence == 1.0
        assert rel.extractor_version == "1.0.0"

    def test_depends_on_relationship_full_valid(self) -> None:
        """Test DependsOnRelationship with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        rel = DependsOnRelationship(
            condition="service_healthy",
            created_at=now,
            source_timestamp=source_time,
            source="docker_compose_reader",
            confidence=0.99,
            extractor_version="1.2.0",
        )

        assert rel.condition == "service_healthy"
        assert rel.source_timestamp == source_time
        assert rel.confidence == 0.99

    def test_depends_on_relationship_completed_condition(self) -> None:
        """Test DependsOnRelationship with service_completed_successfully condition."""
        now = datetime.now(UTC)

        rel = DependsOnRelationship(
            condition="service_completed_successfully",
            created_at=now,
            source="docker_compose_reader",
            extractor_version="1.0.0",
        )

        assert rel.condition == "service_completed_successfully"

    def test_depends_on_relationship_missing_required_condition(self) -> None:
        """Test DependsOnRelationship validation fails without condition."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            DependsOnRelationship(
                created_at=now,
                source="docker_compose_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("condition",) for e in errors)

    def test_depends_on_relationship_empty_condition(self) -> None:
        """Test DependsOnRelationship validation fails with empty condition."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            DependsOnRelationship(
                condition="",
                created_at=now,
                source="docker_compose_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("condition",) for e in errors)

    def test_depends_on_relationship_missing_required_created_at(self) -> None:
        """Test DependsOnRelationship validation fails without created_at."""
        with pytest.raises(ValidationError) as exc_info:
            DependsOnRelationship(
                condition="service_started",
                source="docker_compose_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("created_at",) for e in errors)

    def test_depends_on_relationship_missing_required_source(self) -> None:
        """Test DependsOnRelationship validation fails without source."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            DependsOnRelationship(
                condition="service_started",
                created_at=now,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source",) for e in errors)

    def test_depends_on_relationship_missing_required_extractor_version(self) -> None:
        """Test DependsOnRelationship validation fails without extractor_version."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            DependsOnRelationship(
                condition="service_started",
                created_at=now,
                source="docker_compose_reader",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extractor_version",) for e in errors)

    def test_depends_on_relationship_serialization(self) -> None:
        """Test DependsOnRelationship can be serialized to dict."""
        now = datetime.now(UTC)

        rel = DependsOnRelationship(
            condition="service_healthy",
            created_at=now,
            source="docker_compose_reader",
            extractor_version="1.0.0",
        )

        data = rel.model_dump()
        assert data["condition"] == "service_healthy"
        assert data["confidence"] == 1.0
        assert data["source"] == "docker_compose_reader"
