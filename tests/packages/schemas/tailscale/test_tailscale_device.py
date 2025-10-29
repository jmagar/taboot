"""Tests for TailscaleDevice entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- IPv4 and IPv6 address fields
- Boolean flags (is_exit_node, ssh_enabled)
- List fields (endpoints, subnet_routes)
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.tailscale.tailscale_device import TailscaleDevice


class TestTailscaleDeviceEntity:
    """Test suite for TailscaleDevice entity."""

    def test_tailscale_device_minimal_valid(self) -> None:
        """Test TailscaleDevice with only required fields."""
        now = datetime.now(UTC)
        device = TailscaleDevice(
            device_id="ts-device-123",
            hostname="server.example.com",
            os="linux",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert device.device_id == "ts-device-123"
        assert device.hostname == "server.example.com"
        assert device.os == "linux"
        assert device.created_at == now
        assert device.updated_at == now
        assert device.extraction_tier == "A"
        assert device.extraction_method == "tailscale_api"
        assert device.confidence == 1.0
        assert device.extractor_version == "1.0.0"
        assert device.ipv4_address is None
        assert device.ipv6_address is None
        assert device.endpoints is None
        assert device.key_expiry is None
        assert device.is_exit_node is None
        assert device.subnet_routes is None
        assert device.ssh_enabled is None
        assert device.tailnet_dns_name is None
        assert device.source_timestamp is None

    def test_tailscale_device_full_valid(self) -> None:
        """Test TailscaleDevice with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        key_expiry = datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC)

        device = TailscaleDevice(
            device_id="ts-device-456",
            hostname="gateway.example.com",
            os="linux",
            ipv4_address="100.64.1.5",
            ipv6_address="fd7a:115c:a1e0::1",
            endpoints=["192.168.1.100:41641", "203.0.113.50:41641"],
            key_expiry=key_expiry,
            is_exit_node=True,
            subnet_routes=["10.0.0.0/24", "10.1.0.0/24"],
            ssh_enabled=True,
            tailnet_dns_name="gateway.tailnet-abc.ts.net",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert device.device_id == "ts-device-456"
        assert device.hostname == "gateway.example.com"
        assert device.os == "linux"
        assert device.ipv4_address == "100.64.1.5"
        assert device.ipv6_address == "fd7a:115c:a1e0::1"
        assert device.endpoints == ["192.168.1.100:41641", "203.0.113.50:41641"]
        assert device.key_expiry == key_expiry
        assert device.is_exit_node is True
        assert device.subnet_routes == ["10.0.0.0/24", "10.1.0.0/24"]
        assert device.ssh_enabled is True
        assert device.tailnet_dns_name == "gateway.tailnet-abc.ts.net"
        assert device.source_timestamp == source_time
        assert device.extraction_tier == "A"
        assert device.confidence == 1.0

    def test_tailscale_device_missing_required_device_id(self) -> None:
        """Test TailscaleDevice validation fails without device_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleDevice(
                hostname="server.example.com",
                os="linux",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("device_id",) for e in errors)

    def test_tailscale_device_missing_required_hostname(self) -> None:
        """Test TailscaleDevice validation fails without hostname."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleDevice(
                device_id="ts-device-123",
                os="linux",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("hostname",) for e in errors)

    def test_tailscale_device_missing_required_os(self) -> None:
        """Test TailscaleDevice validation fails without os."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleDevice(
                device_id="ts-device-123",
                hostname="server.example.com",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("os",) for e in errors)

    def test_tailscale_device_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleDevice(
                device_id="ts-device-123",
                hostname="server.example.com",
                os="linux",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_tailscale_device_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleDevice(
                device_id="ts-device-123",
                hostname="server.example.com",
                os="linux",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_tailscale_device_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            device = TailscaleDevice(
                device_id="ts-device-123",
                hostname="server.example.com",
                os="linux",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert device.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            TailscaleDevice(
                device_id="ts-device-123",
                hostname="server.example.com",
                os="linux",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_tailscale_device_serialization(self) -> None:
        """Test TailscaleDevice can be serialized to dict."""
        now = datetime.now(UTC)
        device = TailscaleDevice(
            device_id="ts-device-123",
            hostname="server.example.com",
            os="linux",
            ipv4_address="100.64.1.5",
            is_exit_node=False,
            ssh_enabled=True,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = device.model_dump()
        assert data["device_id"] == "ts-device-123"
        assert data["hostname"] == "server.example.com"
        assert data["os"] == "linux"
        assert data["ipv4_address"] == "100.64.1.5"
        assert data["is_exit_node"] is False
        assert data["ssh_enabled"] is True
        assert data["confidence"] == 1.0

    def test_tailscale_device_deserialization(self) -> None:
        """Test TailscaleDevice can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "device_id": "ts-device-123",
            "hostname": "server.example.com",
            "os": "linux",
            "ipv4_address": "100.64.1.5",
            "is_exit_node": False,
            "ssh_enabled": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "tailscale_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        device = TailscaleDevice.model_validate(data)
        assert device.device_id == "ts-device-123"
        assert device.hostname == "server.example.com"
        assert device.os == "linux"
        assert device.ipv4_address == "100.64.1.5"
        assert device.is_exit_node is False
        assert device.ssh_enabled is True

    def test_tailscale_device_empty_lists(self) -> None:
        """Test TailscaleDevice handles empty list fields."""
        now = datetime.now(UTC)
        device = TailscaleDevice(
            device_id="ts-device-123",
            hostname="server.example.com",
            os="linux",
            endpoints=[],
            subnet_routes=[],
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert device.endpoints == []
        assert device.subnet_routes == []
