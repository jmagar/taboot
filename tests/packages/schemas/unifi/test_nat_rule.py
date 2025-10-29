"""Tests for NATRule entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.unifi.nat_rule import NATRule


class TestNATRuleEntity:
    """Test suite for NATRule entity."""

    def test_nat_rule_minimal_valid(self) -> None:
        """Test NATRule with only required fields."""
        now = datetime.now(UTC)
        rule = NATRule(
            rule_id="5f9c1234abcd5678ef123456",
            name="DNAT Rule",
            enabled=True,
            type="dnat",
            source="any",
            destination="192.168.1.100",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert rule.rule_id == "5f9c1234abcd5678ef123456"
        assert rule.name == "DNAT Rule"
        assert rule.type == "dnat"
        assert rule.source == "any"
        assert rule.destination == "192.168.1.100"

    def test_nat_rule_full_valid(self) -> None:
        """Test NATRule with all fields populated."""
        now = datetime.now(UTC)

        rule = NATRule(
            rule_id="5f9c1234abcd5678ef123456",
            name="DNAT Rule",
            enabled=True,
            type="dnat",
            source="192.168.0.0/16",
            destination="192.168.1.100",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert rule.source == "192.168.0.0/16"
