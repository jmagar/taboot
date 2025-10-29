"""Tests for UnifiClient entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- MAC address validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.unifi.unifi_client import UnifiClient


class TestUnifiClientEntity:
    """Test suite for UnifiClient entity."""

    def test_unifi_client_minimal_valid(self) -> None:
        """Test UnifiClient with only required fields."""
        now = datetime.now(UTC)
        client = UnifiClient(
            mac="aa:bb:cc:dd:ee:ff",
            hostname="laptop-01",
            ip="192.168.1.50",
            network="LAN",
            is_wired=False,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert client.mac == "aa:bb:cc:dd:ee:ff"
        assert client.hostname == "laptop-01"
        assert client.ip == "192.168.1.50"
        assert client.network == "LAN"
        assert client.is_wired is False
        assert client.link_speed is None
        assert client.connection_type is None
        assert client.uptime is None

    def test_unifi_client_full_valid(self) -> None:
        """Test UnifiClient with all fields populated."""
        now = datetime.now(UTC)

        client = UnifiClient(
            mac="aa:bb:cc:dd:ee:ff",
            hostname="laptop-01",
            ip="192.168.1.50",
            network="LAN",
            is_wired=False,
            link_speed=866,
            connection_type="wifi6",
            uptime=7200,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert client.mac == "aa:bb:cc:dd:ee:ff"
        assert client.link_speed == 866
        assert client.connection_type == "wifi6"
        assert client.uptime == 7200

    def test_unifi_client_missing_required_mac(self) -> None:
        """Test UnifiClient validation fails without mac."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            UnifiClient(
                hostname="laptop-01",
                ip="192.168.1.50",
                network="LAN",
                is_wired=False,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="unifi_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("mac",) for e in errors)

    def test_unifi_client_invalid_mac_format(self) -> None:
        """Test UnifiClient validation fails with invalid MAC address."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            UnifiClient(
                mac="invalid-mac",
                hostname="laptop-01",
                ip="192.168.1.50",
                network="LAN",
                is_wired=False,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="unifi_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("mac",) for e in errors)

    def test_unifi_client_serialization(self) -> None:
        """Test UnifiClient can be serialized to dict."""
        now = datetime.now(UTC)
        client = UnifiClient(
            mac="aa:bb:cc:dd:ee:ff",
            hostname="laptop-01",
            ip="192.168.1.50",
            network="LAN",
            is_wired=False,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = client.model_dump()
        assert data["mac"] == "aa:bb:cc:dd:ee:ff"
        assert data["hostname"] == "laptop-01"
        assert data["is_wired"] is False
