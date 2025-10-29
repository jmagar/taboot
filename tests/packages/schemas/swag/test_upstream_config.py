"""Tests for UpstreamConfig entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.swag.upstream_config import UpstreamConfig


class TestUpstreamConfigEntity:
    """Test suite for UpstreamConfig entity."""

    def test_upstream_config_minimal_valid(self) -> None:
        """Test UpstreamConfig with only required fields."""
        now = datetime.now(UTC)
        config = UpstreamConfig(
            app="100.74.16.82",
            port=3000,
            proto="http",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert config.app == "100.74.16.82"
        assert config.port == 3000
        assert config.proto == "http"

    def test_upstream_config_full_valid(self) -> None:
        """Test UpstreamConfig with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        config = UpstreamConfig(
            app="backend-service",
            port=8080,
            proto="https",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="2.0.0",
        )

        assert config.app == "backend-service"
        assert config.port == 8080
        assert config.proto == "https"
        assert config.source_timestamp == source_time

    def test_upstream_config_port_validation(self) -> None:
        """Test port must be valid (1-65535)."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            UpstreamConfig(
                app="100.74.16.82",
                port=0,
                proto="http",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("port",) for e in errors)

    def test_upstream_config_serialization(self) -> None:
        """Test UpstreamConfig can be serialized to dict."""
        now = datetime.now(UTC)
        config = UpstreamConfig(
            app="100.74.16.82",
            port=3000,
            proto="http",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = config.model_dump()
        assert data["app"] == "100.74.16.82"
        assert data["port"] == 3000
        assert data["proto"] == "http"
