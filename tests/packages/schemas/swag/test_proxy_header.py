"""Tests for ProxyHeader entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.swag.proxy_header import ProxyHeader


class TestProxyHeaderEntity:
    """Test suite for ProxyHeader entity."""

    def test_proxy_header_minimal_valid(self) -> None:
        """Test ProxyHeader with only required fields."""
        now = datetime.now(UTC)
        header = ProxyHeader(
            header_name="X-Frame-Options",
            header_value="SAMEORIGIN",
            header_type="add_header",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert header.header_name == "X-Frame-Options"
        assert header.header_value == "SAMEORIGIN"
        assert header.header_type == "add_header"

    def test_proxy_header_full_valid(self) -> None:
        """Test ProxyHeader with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        header = ProxyHeader(
            header_name="Host",
            header_value="$host",
            header_type="proxy_set_header",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="2.0.0",
        )

        assert header.header_name == "Host"
        assert header.header_value == "$host"
        assert header.header_type == "proxy_set_header"
        assert header.source_timestamp == source_time

    def test_proxy_header_missing_required_fields(self) -> None:
        """Test ProxyHeader validation fails without required fields."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ProxyHeader(
                header_value="SAMEORIGIN",
                header_type="add_header",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("header_name",) for e in errors)

    def test_proxy_header_serialization(self) -> None:
        """Test ProxyHeader can be serialized to dict."""
        now = datetime.now(UTC)
        header = ProxyHeader(
            header_name="X-Custom-Header",
            header_value="CustomValue",
            header_type="add_header",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = header.model_dump()
        assert data["header_name"] == "X-Custom-Header"
        assert data["header_value"] == "CustomValue"
        assert data["header_type"] == "add_header"
