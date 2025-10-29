"""Tests for PortBinding entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.port_binding import PortBinding


class TestPortBindingEntity:
    """Test suite for PortBinding entity."""

    def test_port_binding_minimal_valid(self) -> None:
        """Test PortBinding with only required fields."""
        now = datetime.now(UTC)
        port = PortBinding(
            compose_file_path="/tmp/docker-compose.yml",
            service_name="web",
            container_port=80,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert port.container_port == 80
        assert port.compose_file_path == "/tmp/docker-compose.yml"
        assert port.service_name == "web"
        assert port.host_ip is None
        assert port.host_port is None
        assert port.protocol is None

    def test_port_binding_full_valid(self) -> None:
        """Test PortBinding with all fields populated."""
        now = datetime.now(UTC)
        port = PortBinding(
            compose_file_path="/tmp/docker-compose.yml",
            service_name="web",
            host_ip="0.0.0.0",
            host_port=8080,
            container_port=80,
            protocol="tcp",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert port.host_ip == "0.0.0.0"
        assert port.host_port == 8080
        assert port.container_port == 80
        assert port.protocol == "tcp"
        assert port.compose_file_path == "/tmp/docker-compose.yml"
        assert port.service_name == "web"

    def test_port_binding_missing_required_container_port(self) -> None:
        """Test PortBinding validation fails without container_port."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            PortBinding(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("container_port",) for e in errors)
        assert any(e["loc"] == ("compose_file_path",) for e in errors)
        assert any(e["loc"] == ("service_name",) for e in errors)
