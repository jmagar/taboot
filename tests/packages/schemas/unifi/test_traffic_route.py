"""Tests for TrafficRoute entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.unifi.traffic_route import TrafficRoute


class TestTrafficRouteEntity:
    """Test suite for TrafficRoute entity."""

    def test_traffic_route_minimal_valid(self) -> None:
        """Test TrafficRoute with only required fields."""
        now = datetime.now(UTC)
        route = TrafficRoute(
            route_id="5f9c1234abcd5678ef123456",
            name="Route to VPN",
            enabled=True,
            next_hop="192.168.1.1",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert route.route_id == "5f9c1234abcd5678ef123456"
        assert route.name == "Route to VPN"
        assert route.next_hop == "192.168.1.1"

    def test_traffic_route_full_valid(self) -> None:
        """Test TrafficRoute with all fields populated."""
        now = datetime.now(UTC)

        route = TrafficRoute(
            route_id="5f9c1234abcd5678ef123456",
            name="Route to VPN",
            enabled=True,
            next_hop="192.168.1.1",
            matching_target="domain",
            network_id="5f9c1234abcd5678ef111111",
            ip_addresses=["10.0.0.0/24"],
            domains=["internal.company.com"],
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert route.matching_target == "domain"
        assert route.ip_addresses == ["10.0.0.0/24"]
