"""Tests for HealthCheck entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.health_check import HealthCheck


class TestHealthCheckEntity:
    """Test suite for HealthCheck entity."""

    def test_health_check_minimal_valid(self) -> None:
        """Test HealthCheck with only required fields."""
        now = datetime.now(UTC)
        health = HealthCheck(
            compose_file_path="/tmp/docker-compose.yml",
            service_name="web",
            test="CMD-SHELL curl -f http://localhost/ || exit 1",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert health.test == "CMD-SHELL curl -f http://localhost/ || exit 1"
        assert health.compose_file_path == "/tmp/docker-compose.yml"
        assert health.service_name == "web"
        assert health.interval is None
        assert health.timeout is None

    def test_health_check_full_valid(self) -> None:
        """Test HealthCheck with all fields populated."""
        now = datetime.now(UTC)
        health = HealthCheck(
            compose_file_path="/tmp/docker-compose.yml",
            service_name="db",
            test="CMD pg_isready -U postgres",
            interval="30s",
            timeout="10s",
            retries=3,
            start_period="60s",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert health.test == "CMD pg_isready -U postgres"
        assert health.interval == "30s"
        assert health.timeout == "10s"
        assert health.retries == 3
        assert health.start_period == "60s"
        assert health.compose_file_path == "/tmp/docker-compose.yml"
        assert health.service_name == "db"

    def test_health_check_missing_required_test(self) -> None:
        """Test HealthCheck validation fails without test."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            HealthCheck(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("test",) for e in errors)
        assert any(e["loc"] == ("compose_file_path",) for e in errors)
        assert any(e["loc"] == ("service_name",) for e in errors)
