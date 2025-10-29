"""Tests for ComposeService entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.compose_service import ComposeService


class TestComposeServiceEntity:
    """Test suite for ComposeService entity."""

    def test_compose_service_minimal_valid(self) -> None:
        """Test ComposeService with only required fields."""
        now = datetime.now(UTC)
        service = ComposeService(
            name="web",
            compose_file_path="/tmp/docker-compose.yml",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert service.name == "web"
        assert service.compose_file_path == "/tmp/docker-compose.yml"
        assert service.image is None
        assert service.command is None
        assert service.restart is None

    def test_compose_service_full_valid(self) -> None:
        """Test ComposeService with all fields populated."""
        now = datetime.now(UTC)
        service = ComposeService(
            name="api",
            compose_file_path="/tmp/docker-compose.yml",
            image="nginx:alpine",
            command="nginx -g 'daemon off;'",
            entrypoint="/docker-entrypoint.sh",
            restart="unless-stopped",
            cpus=2.0,
            memory="2048m",
            user="1000:1000",
            working_dir="/app",
            hostname="api.local",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert service.name == "api"
        assert service.compose_file_path == "/tmp/docker-compose.yml"
        assert service.image == "nginx:alpine"
        assert service.command == "nginx -g 'daemon off;'"
        assert service.cpus == 2.0
        assert service.memory == "2048m"

    def test_compose_service_missing_required_name(self) -> None:
        """Test ComposeService validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ComposeService(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)
        assert any(e["loc"] == ("compose_file_path",) for e in errors)

    def test_compose_service_serialization(self) -> None:
        """Test ComposeService can be serialized to dict."""
        now = datetime.now(UTC)
        service = ComposeService(
            name="db",
            compose_file_path="/tmp/docker-compose.yml",
            image="postgres:14",
            restart="always",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = service.model_dump()
        assert data["name"] == "db"
        assert data["image"] == "postgres:14"
        assert data["restart"] == "always"
        assert data["compose_file_path"] == "/tmp/docker-compose.yml"
