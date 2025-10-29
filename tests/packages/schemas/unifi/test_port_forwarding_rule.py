"""Tests for PortForwardingRule entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.unifi.port_forwarding_rule import PortForwardingRule


class TestPortForwardingRuleEntity:
    """Test suite for PortForwardingRule entity."""

    def test_port_forwarding_rule_minimal_valid(self) -> None:
        """Test PortForwardingRule with only required fields."""
        now = datetime.now(UTC)
        rule = PortForwardingRule(
            rule_id="5f9c1234abcd5678ef123456",
            name="SSH Forward",
            enabled=True,
            proto="tcp",
            src="any",
            dst_port=22,
            fwd="192.168.1.100",
            fwd_port=22,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert rule.rule_id == "5f9c1234abcd5678ef123456"
        assert rule.name == "SSH Forward"
        assert rule.enabled is True
        assert rule.proto == "tcp"
        assert rule.src == "any"
        assert rule.dst_port == 22
        assert rule.fwd == "192.168.1.100"
        assert rule.fwd_port == 22
        assert rule.pfwd_interface is None

    def test_port_forwarding_rule_full_valid(self) -> None:
        """Test PortForwardingRule with all fields populated."""
        now = datetime.now(UTC)

        rule = PortForwardingRule(
            rule_id="5f9c1234abcd5678ef123456",
            name="SSH Forward",
            enabled=True,
            proto="tcp",
            src="any",
            dst_port=22,
            fwd="192.168.1.100",
            fwd_port=22,
            pfwd_interface="wan",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert rule.pfwd_interface == "wan"
