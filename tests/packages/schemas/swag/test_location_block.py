"""Tests for LocationBlock entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.swag.location_block import LocationBlock


class TestLocationBlockEntity:
    """Test suite for LocationBlock entity."""

    def test_location_block_minimal_valid(self) -> None:
        """Test LocationBlock with only required fields."""
        now = datetime.now(UTC)
        location = LocationBlock(
            path="/api",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert location.path == "/api"
        assert location.proxy_pass_url is None
        assert location.auth_enabled is False
        assert location.auth_type is None

    def test_location_block_full_valid(self) -> None:
        """Test LocationBlock with all fields populated."""
        now = datetime.now(UTC)
        location = LocationBlock(
            path="/admin",
            proxy_pass_url="http://100.74.16.82:3000",
            auth_enabled=True,
            auth_type="authelia",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert location.path == "/admin"
        assert location.proxy_pass_url == "http://100.74.16.82:3000"
        assert location.auth_enabled is True
        assert location.auth_type == "authelia"

    def test_location_block_missing_required_path(self) -> None:
        """Test LocationBlock validation fails without path."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            LocationBlock(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("path",) for e in errors)

    def test_location_block_serialization(self) -> None:
        """Test LocationBlock can be serialized to dict."""
        now = datetime.now(UTC)
        location = LocationBlock(
            path="/api",
            proxy_pass_url="http://backend:8080",
            auth_enabled=True,
            auth_type="basic",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = location.model_dump()
        assert data["path"] == "/api"
        assert data["proxy_pass_url"] == "http://backend:8080"
        assert data["auth_enabled"] is True
