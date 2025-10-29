"""Tests for ServiceDependency entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.service_dependency import ServiceDependency


class TestServiceDependencyEntity:
    """Test suite for ServiceDependency entity."""

    def test_service_dependency_minimal_valid(self) -> None:
        """Test ServiceDependency with only required fields."""
        now = datetime.now(UTC)
        dep = ServiceDependency(
            source_service="web",
            target_service="db",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert dep.source_service == "web"
        assert dep.target_service == "db"
        assert dep.condition is None

    def test_service_dependency_with_condition(self) -> None:
        """Test ServiceDependency with condition."""
        now = datetime.now(UTC)
        dep = ServiceDependency(
            source_service="api",
            target_service="postgres",
            condition="service_healthy",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert dep.condition == "service_healthy"

    def test_service_dependency_missing_required_source(self) -> None:
        """Test ServiceDependency validation fails without source_service."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ServiceDependency(
                target_service="db",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_service",) for e in errors)
