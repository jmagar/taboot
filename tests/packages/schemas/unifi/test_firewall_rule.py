"""Tests for FirewallRule entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.unifi.firewall_rule import FirewallRule


class TestFirewallRuleEntity:
    """Test suite for FirewallRule entity."""

    def test_firewall_rule_minimal_valid(self) -> None:
        """Test FirewallRule with only required fields."""
        now = datetime.now(UTC)
        rule = FirewallRule(
            rule_id="5f9c1234abcd5678ef123456",
            name="Block External",
            enabled=True,
            action="DROP",
            protocol="all",
            ip_version="ipv4",
            index=1,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert rule.rule_id == "5f9c1234abcd5678ef123456"
        assert rule.name == "Block External"
        assert rule.action == "DROP"
        assert rule.protocol == "all"
        assert rule.ip_version == "ipv4"
        assert rule.index == 1

    def test_firewall_rule_full_valid(self) -> None:
        """Test FirewallRule with all fields populated."""
        now = datetime.now(UTC)

        rule = FirewallRule(
            rule_id="5f9c1234abcd5678ef123456",
            name="Block External",
            enabled=True,
            action="DROP",
            protocol="tcp",
            ip_version="ipv4",
            index=1,
            source_zone="WAN",
            dest_zone="LAN",
            logging=True,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert rule.source_zone == "WAN"
        assert rule.dest_zone == "LAN"
        assert rule.logging is True
