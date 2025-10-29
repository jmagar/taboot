"""Tests for UnifiNetwork entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.unifi.unifi_network import UnifiNetwork


class TestUnifiNetworkEntity:
    """Test suite for UnifiNetwork entity."""

    def test_unifi_network_minimal_valid(self) -> None:
        """Test UnifiNetwork with only required fields."""
        now = datetime.now(UTC)
        network = UnifiNetwork(
            network_id="5f9c1234abcd5678ef123456",
            name="LAN",
            vlan_id=1,
            subnet="192.168.1.0/24",
            gateway_ip="192.168.1.1",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert network.network_id == "5f9c1234abcd5678ef123456"
        assert network.name == "LAN"
        assert network.vlan_id == 1
        assert network.subnet == "192.168.1.0/24"
        assert network.gateway_ip == "192.168.1.1"
        assert network.dns_servers is None
        assert network.wifi_name is None

    def test_unifi_network_full_valid(self) -> None:
        """Test UnifiNetwork with all fields populated."""
        now = datetime.now(UTC)

        network = UnifiNetwork(
            network_id="5f9c1234abcd5678ef123456",
            name="LAN",
            vlan_id=1,
            subnet="192.168.1.0/24",
            gateway_ip="192.168.1.1",
            dns_servers=["8.8.8.8", "8.8.4.4"],
            wifi_name="MyWiFi",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert network.dns_servers == ["8.8.8.8", "8.8.4.4"]
        assert network.wifi_name == "MyWiFi"

    def test_unifi_network_missing_required_network_id(self) -> None:
        """Test UnifiNetwork validation fails without network_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            UnifiNetwork(
                name="LAN",
                vlan_id=1,
                subnet="192.168.1.0/24",
                gateway_ip="192.168.1.1",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="unifi_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("network_id",) for e in errors)
