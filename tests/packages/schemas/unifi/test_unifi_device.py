"""Tests for UnifiDevice entity schema.

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

from packages.schemas.unifi.unifi_device import UnifiDevice


class TestUnifiDeviceEntity:
    """Test suite for UnifiDevice entity."""

    def test_unifi_device_minimal_valid(self) -> None:
        """Test UnifiDevice with only required fields."""
        now = datetime.now(UTC)
        device = UnifiDevice(
            mac="00:11:22:33:44:55",
            hostname="unifi-switch-01",
            type="usw",
            model="US-24-250W",
            adopted=True,
            state="connected",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert device.mac == "00:11:22:33:44:55"
        assert device.hostname == "unifi-switch-01"
        assert device.type == "usw"
        assert device.model == "US-24-250W"
        assert device.adopted is True
        assert device.state == "connected"
        assert device.created_at == now
        assert device.updated_at == now
        assert device.extraction_tier == "A"
        assert device.extraction_method == "unifi_api"
        assert device.confidence == 1.0
        assert device.extractor_version == "1.0.0"
        assert device.ip is None
        assert device.firmware_version is None
        assert device.link_speed is None
        assert device.connection_type is None
        assert device.uptime is None
        assert device.source_timestamp is None

    def test_unifi_device_full_valid(self) -> None:
        """Test UnifiDevice with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        device = UnifiDevice(
            mac="00:11:22:33:44:55",
            hostname="unifi-switch-01",
            type="usw",
            model="US-24-250W",
            adopted=True,
            state="connected",
            ip="192.168.1.100",
            firmware_version="6.5.55",
            link_speed=1000,
            connection_type="wired",
            uptime=86400,
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert device.mac == "00:11:22:33:44:55"
        assert device.hostname == "unifi-switch-01"
        assert device.type == "usw"
        assert device.model == "US-24-250W"
        assert device.adopted is True
        assert device.state == "connected"
        assert device.ip == "192.168.1.100"
        assert device.firmware_version == "6.5.55"
        assert device.link_speed == 1000
        assert device.connection_type == "wired"
        assert device.uptime == 86400
        assert device.source_timestamp == source_time

    def test_unifi_device_missing_required_mac(self) -> None:
        """Test UnifiDevice validation fails without mac."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            UnifiDevice(
                hostname="unifi-switch-01",
                type="usw",
                model="US-24-250W",
                adopted=True,
                state="connected",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="unifi_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("mac",) for e in errors)

    def test_unifi_device_missing_required_hostname(self) -> None:
        """Test UnifiDevice validation fails without hostname."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            UnifiDevice(
                mac="00:11:22:33:44:55",
                type="usw",
                model="US-24-250W",
                adopted=True,
                state="connected",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="unifi_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("hostname",) for e in errors)

    def test_unifi_device_invalid_mac_format(self) -> None:
        """Test UnifiDevice validation fails with invalid MAC address."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            UnifiDevice(
                mac="not-a-mac",
                hostname="unifi-switch-01",
                type="usw",
                model="US-24-250W",
                adopted=True,
                state="connected",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="unifi_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("mac",) for e in errors)

    def test_unifi_device_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            UnifiDevice(
                mac="00:11:22:33:44:55",
                hostname="unifi-switch-01",
                type="usw",
                model="US-24-250W",
                adopted=True,
                state="connected",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="unifi_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_unifi_device_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            UnifiDevice(
                mac="00:11:22:33:44:55",
                hostname="unifi-switch-01",
                type="usw",
                model="US-24-250W",
                adopted=True,
                state="connected",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="unifi_api",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_unifi_device_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            device = UnifiDevice(
                mac="00:11:22:33:44:55",
                hostname="unifi-switch-01",
                type="usw",
                model="US-24-250W",
                adopted=True,
                state="connected",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="unifi_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert device.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            UnifiDevice(
                mac="00:11:22:33:44:55",
                hostname="unifi-switch-01",
                type="usw",
                model="US-24-250W",
                adopted=True,
                state="connected",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="unifi_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_unifi_device_serialization(self) -> None:
        """Test UnifiDevice can be serialized to dict."""
        now = datetime.now(UTC)
        device = UnifiDevice(
            mac="00:11:22:33:44:55",
            hostname="unifi-switch-01",
            type="usw",
            model="US-24-250W",
            adopted=True,
            state="connected",
            ip="192.168.1.100",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = device.model_dump()
        assert data["mac"] == "00:11:22:33:44:55"
        assert data["hostname"] == "unifi-switch-01"
        assert data["type"] == "usw"
        assert data["model"] == "US-24-250W"
        assert data["adopted"] is True
        assert data["state"] == "connected"
        assert data["ip"] == "192.168.1.100"
        assert data["confidence"] == 1.0

    def test_unifi_device_deserialization(self) -> None:
        """Test UnifiDevice can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "mac": "00:11:22:33:44:55",
            "hostname": "unifi-switch-01",
            "type": "usw",
            "model": "US-24-250W",
            "adopted": True,
            "state": "connected",
            "ip": "192.168.1.100",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "unifi_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        device = UnifiDevice.model_validate(data)
        assert device.mac == "00:11:22:33:44:55"
        assert device.hostname == "unifi-switch-01"
        assert device.type == "usw"
        assert device.model == "US-24-250W"
        assert device.adopted is True
        assert device.state == "connected"
        assert device.ip == "192.168.1.100"

    def test_unifi_device_uptime_validation(self) -> None:
        """Test uptime must be non-negative."""
        now = datetime.now(UTC)

        # Valid uptime
        device = UnifiDevice(
            mac="00:11:22:33:44:55",
            hostname="unifi-switch-01",
            type="usw",
            model="US-24-250W",
            adopted=True,
            state="connected",
            uptime=0,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        assert device.uptime == 0

        # Invalid uptime (negative)
        with pytest.raises(ValidationError) as exc_info:
            UnifiDevice(
                mac="00:11:22:33:44:55",
                hostname="unifi-switch-01",
                type="usw",
                model="US-24-250W",
                adopted=True,
                state="connected",
                uptime=-100,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="unifi_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("uptime",) for e in errors)
