"""Tests for Tier B spaCy entity ruler."""

import pytest

from packages.extraction.tier_b.entity_ruler import SpacyEntityRuler


class TestSpacyEntityRuler:
    """Test spaCy entity patterns for Service, Host, IP, Port."""

    @pytest.fixture
    def entity_ruler(self):
        """Create entity ruler instance."""
        return SpacyEntityRuler(model="en_core_web_sm")

    def test_extract_service_entities(self, entity_ruler):
        """Test extracting service entities."""
        text = "The api-service connects to postgres database and redis cache."

        entities = entity_ruler.extract_entities(text)

        services = [e for e in entities if e["label"] == "SERVICE"]
        assert len(services) >= 2
        service_texts = {e["text"].lower() for e in services}
        assert "postgres" in service_texts or "database" in service_texts

    def test_extract_host_entities(self, entity_ruler):
        """Test extracting host entities."""
        text = "Deploy to server01.example.com and backup-host in datacenter."

        entities = entity_ruler.extract_entities(text)

        hosts = [e for e in entities if e["label"] == "HOST"]
        assert len(hosts) >= 1

    def test_extract_ip_entities(self, entity_ruler):
        """Test extracting IP address entities."""
        text = "Server at 192.168.1.10 connects to 10.0.0.5 on port 8080."

        entities = entity_ruler.extract_entities(text)

        ips = [e for e in entities if e["label"] == "IP"]
        assert len(ips) >= 2
        ip_texts = {e["text"] for e in ips}
        assert "192.168.1.10" in ip_texts
        assert "10.0.0.5" in ip_texts

    def test_extract_port_entities(self, entity_ruler):
        """Test extracting port number entities."""
        text = "API listens on port 8080, database on 5432."

        entities = entity_ruler.extract_entities(text)

        ports = [e for e in entities if e["label"] == "PORT"]
        assert len(ports) >= 2
        port_texts = {e["text"] for e in ports}
        assert "8080" in port_texts
        assert "5432" in port_texts

    def test_extract_mixed_entities(self, entity_ruler):
        """Test extracting multiple entity types together."""
        text = "The nginx service at 192.168.1.10:80 routes to api-service at server01:8080."

        entities = entity_ruler.extract_entities(text)

        # Should extract services, IPs, hosts, and ports
        labels = {e["label"] for e in entities}
        assert "SERVICE" in labels or len([e for e in entities if "service" in e["text"].lower()]) > 0
        assert "IP" in labels
        assert "PORT" in labels

    def test_empty_text_returns_empty_list(self, entity_ruler):
        """Test that empty text returns empty list."""
        entities = entity_ruler.extract_entities("")
        assert entities == []

    def test_text_without_entities(self, entity_ruler):
        """Test text without recognizable entities."""
        text = "This is just plain text with no technical entities."
        entities = entity_ruler.extract_entities(text)
        # Should return empty or only generic entities
        assert isinstance(entities, list)
