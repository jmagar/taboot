"""Tests for ComposeProject entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.compose_project import ComposeProject


class TestComposeProjectEntity:
    """Test suite for ComposeProject entity."""

    def test_compose_project_minimal_valid(self) -> None:
        """Test ComposeProject with only required fields."""
        now = datetime.now(UTC)
        project = ComposeProject(
            name="my-project",
            file_path="/tmp/docker-compose.yml",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert project.name == "my-project"
        assert project.version is None
        assert project.file_path == "/tmp/docker-compose.yml"

    def test_compose_project_full_valid(self) -> None:
        """Test ComposeProject with all fields populated."""
        now = datetime.now(UTC)
        project = ComposeProject(
            name="production-stack",
            version="3.8",
            file_path="/opt/docker-compose.yml",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert project.name == "production-stack"
        assert project.version == "3.8"
        assert project.file_path == "/opt/docker-compose.yml"

    def test_compose_project_missing_required_name(self) -> None:
        """Test ComposeProject validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ComposeProject(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)
        assert any(e["loc"] == ("file_path",) for e in errors)

    def test_compose_project_serialization(self) -> None:
        """Test ComposeProject can be serialized to dict."""
        now = datetime.now(UTC)
        project = ComposeProject(
            name="test-project",
            version="3.8",
            file_path="/tmp/docker-compose.yml",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = project.model_dump()
        assert data["name"] == "test-project"
        assert data["version"] == "3.8"
        assert data["file_path"] == "/tmp/docker-compose.yml"
