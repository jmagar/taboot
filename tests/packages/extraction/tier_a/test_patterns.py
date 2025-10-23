"""Tests for Tier A entity pattern matching using Aho-Corasick."""

import pytest
from packages.extraction.tier_a.patterns import EntityPatternMatcher


class TestEntityPatternMatcher:
    """Test Aho-Corasick automaton for known entities."""

    def test_match_service_names(self) -> None:
        """Test matching known service names."""
        matcher = EntityPatternMatcher()
        matcher.add_patterns("service", ["api-service", "postgres", "redis", "nginx"])

        text = "The api-service depends on postgres and redis for caching."
        matches = matcher.find_matches(text)

        assert len(matches) >= 3
        service_matches = [m for m in matches if m["entity_type"] == "service"]
        assert len(service_matches) == 3

        service_names = {m["text"] for m in service_matches}
        assert "api-service" in service_names
        assert "postgres" in service_names
        assert "redis" in service_names

    def test_match_ip_addresses(self) -> None:
        """Test matching IP addresses."""
        matcher = EntityPatternMatcher()
        matcher.add_patterns("ip", ["192.168.1.10", "10.0.0.5", "172.16.0.1"])

        text = "Server at 192.168.1.10 connects to 10.0.0.5"
        matches = matcher.find_matches(text)

        ip_matches = [m for m in matches if m["entity_type"] == "ip"]
        assert len(ip_matches) == 2

        ips = {m["text"] for m in ip_matches}
        assert "192.168.1.10" in ips
        assert "10.0.0.5" in ips

    def test_match_ports(self) -> None:
        """Test matching port numbers."""
        matcher = EntityPatternMatcher()
        matcher.add_patterns("port", ["8080", "5432", "6379", "80", "443"])

        text = "API listens on port 8080, postgres on 5432"
        matches = matcher.find_matches(text)

        port_matches = [m for m in matches if m["entity_type"] == "port"]
        assert len(port_matches) == 2

        ports = {m["text"] for m in port_matches}
        assert "8080" in ports
        assert "5432" in ports

    def test_no_matches_returns_empty(self) -> None:
        """Test text with no matches returns empty list."""
        matcher = EntityPatternMatcher()
        matcher.add_patterns("service", ["api", "db"])

        text = "Some text with no matching patterns"
        matches = matcher.find_matches(text)

        assert matches == []

    def test_case_insensitive_matching(self) -> None:
        """Test case-insensitive pattern matching."""
        matcher = EntityPatternMatcher()
        matcher.add_patterns("service", ["nginx", "postgres"])

        text = "NGINX proxy routes to PostgreS database"
        matches = matcher.find_matches(text)

        service_matches = [m for m in matches if m["entity_type"] == "service"]
        assert len(service_matches) == 2

        # Matches should return original case from text
        service_texts = {m["text"] for m in service_matches}
        assert "NGINX" in service_texts
        assert "PostgreS" in service_texts

    def test_overlapping_patterns(self) -> None:
        """Test handling overlapping patterns."""
        matcher = EntityPatternMatcher()
        matcher.add_patterns("service", ["api", "api-service"])

        text = "The api-service handles requests"
        matches = matcher.find_matches(text)

        # Should match longest pattern
        service_matches = [m for m in matches if m["entity_type"] == "service"]
        assert any(m["text"] == "api-service" for m in service_matches)

    def test_empty_text_returns_empty(self) -> None:
        """Test empty text returns empty list."""
        matcher = EntityPatternMatcher()
        matcher.add_patterns("service", ["api"])

        matches = matcher.find_matches("")
        assert matches == []

    def test_multiple_entity_types(self) -> None:
        """Test matching multiple entity types simultaneously."""
        matcher = EntityPatternMatcher()
        matcher.add_patterns("service", ["postgres"])
        matcher.add_patterns("port", ["5432"])
        matcher.add_patterns("ip", ["192.168.1.10"])

        text = "postgres at 192.168.1.10:5432"
        matches = matcher.find_matches(text)

        assert len(matches) == 3
        entity_types = {m["entity_type"] for m in matches}
        assert entity_types == {"service", "port", "ip"}
