"""Tests for UnifiSite entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.unifi.unifi_site import UnifiSite


class TestUnifiSiteEntity:
    """Test suite for UnifiSite entity."""

    def test_unifi_site_minimal_valid(self) -> None:
        """Test UnifiSite with only required fields."""
        now = datetime.now(UTC)
        site = UnifiSite(
            site_id="default",
            name="Default Site",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert site.site_id == "default"
        assert site.name == "Default Site"
        assert site.description is None
        assert site.wan_ip is None
        assert site.gateway_ip is None
        assert site.dns_servers is None

    def test_unifi_site_full_valid(self) -> None:
        """Test UnifiSite with all fields populated."""
        now = datetime.now(UTC)

        site = UnifiSite(
            site_id="default",
            name="Default Site",
            description="Main office location",
            wan_ip="203.0.113.10",
            gateway_ip="192.168.1.1",
            dns_servers=["8.8.8.8", "8.8.4.4"],
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert site.description == "Main office location"
        assert site.wan_ip == "203.0.113.10"
        assert site.gateway_ip == "192.168.1.1"
        assert site.dns_servers == ["8.8.8.8", "8.8.4.4"]
