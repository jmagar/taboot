"""Tests for TrafficRule entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.unifi.traffic_rule import TrafficRule


class TestTrafficRuleEntity:
    """Test suite for TrafficRule entity."""

    def test_traffic_rule_minimal_valid(self) -> None:
        """Test TrafficRule with only required fields."""
        now = datetime.now(UTC)
        rule = TrafficRule(
            rule_id="5f9c1234abcd5678ef123456",
            name="Limit Gaming",
            enabled=True,
            action="limit",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert rule.rule_id == "5f9c1234abcd5678ef123456"
        assert rule.name == "Limit Gaming"
        assert rule.action == "limit"

    def test_traffic_rule_full_valid(self) -> None:
        """Test TrafficRule with all fields populated."""
        now = datetime.now(UTC)

        rule = TrafficRule(
            rule_id="5f9c1234abcd5678ef123456",
            name="Limit Gaming",
            enabled=True,
            action="limit",
            bandwidth_limit={"download_kbps": 10000, "upload_kbps": 5000},
            matching_target="ip",
            ip_addresses=["192.168.1.100"],
            domains=["game-server.com"],
            schedule="weekdays",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert rule.bandwidth_limit == {"download_kbps": 10000, "upload_kbps": 5000}
        assert rule.matching_target == "ip"
        assert rule.ip_addresses == ["192.168.1.100"]
