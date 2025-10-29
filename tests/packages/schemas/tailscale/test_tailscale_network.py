"""Tests for TailscaleNetwork entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- List fields (global_nameservers, search_domains)
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.tailscale.tailscale_network import TailscaleNetwork


class TestTailscaleNetworkEntity:
    """Test suite for TailscaleNetwork entity."""

    def test_tailscale_network_minimal_valid(self) -> None:
        """Test TailscaleNetwork with only required fields."""
        now = datetime.now(UTC)
        network = TailscaleNetwork(
            network_id="net-123",
            name="main-network",
            cidr="100.64.0.0/10",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert network.network_id == "net-123"
        assert network.name == "main-network"
        assert network.cidr == "100.64.0.0/10"
        assert network.created_at == now
        assert network.updated_at == now
        assert network.extraction_tier == "A"
        assert network.extraction_method == "tailscale_api"
        assert network.confidence == 1.0
        assert network.extractor_version == "1.0.0"
        assert network.global_nameservers is None
        assert network.search_domains is None
        assert network.source_timestamp is None

    def test_tailscale_network_full_valid(self) -> None:
        """Test TailscaleNetwork with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        network = TailscaleNetwork(
            network_id="net-456",
            name="production-network",
            cidr="100.64.0.0/10",
            global_nameservers=["8.8.8.8", "1.1.1.1", "8.8.4.4"],
            search_domains=["example.com", "internal.local", "dev.local"],
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert network.network_id == "net-456"
        assert network.name == "production-network"
        assert network.cidr == "100.64.0.0/10"
        assert network.global_nameservers == ["8.8.8.8", "1.1.1.1", "8.8.4.4"]
        assert network.search_domains == ["example.com", "internal.local", "dev.local"]
        assert network.source_timestamp == source_time
        assert network.extraction_tier == "A"
        assert network.confidence == 1.0

    def test_tailscale_network_missing_required_network_id(self) -> None:
        """Test TailscaleNetwork validation fails without network_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleNetwork(
                name="main-network",
                cidr="100.64.0.0/10",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("network_id",) for e in errors)

    def test_tailscale_network_missing_required_name(self) -> None:
        """Test TailscaleNetwork validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleNetwork(
                network_id="net-123",
                cidr="100.64.0.0/10",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_tailscale_network_missing_required_cidr(self) -> None:
        """Test TailscaleNetwork validation fails without cidr."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleNetwork(
                network_id="net-123",
                name="main-network",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("cidr",) for e in errors)

    def test_tailscale_network_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleNetwork(
                network_id="net-123",
                name="main-network",
                cidr="100.64.0.0/10",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_tailscale_network_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleNetwork(
                network_id="net-123",
                name="main-network",
                cidr="100.64.0.0/10",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_tailscale_network_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            network = TailscaleNetwork(
                network_id="net-123",
                name="main-network",
                cidr="100.64.0.0/10",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert network.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            TailscaleNetwork(
                network_id="net-123",
                name="main-network",
                cidr="100.64.0.0/10",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_tailscale_network_serialization(self) -> None:
        """Test TailscaleNetwork can be serialized to dict."""
        now = datetime.now(UTC)
        network = TailscaleNetwork(
            network_id="net-123",
            name="main-network",
            cidr="100.64.0.0/10",
            global_nameservers=["8.8.8.8"],
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = network.model_dump()
        assert data["network_id"] == "net-123"
        assert data["name"] == "main-network"
        assert data["cidr"] == "100.64.0.0/10"
        assert data["global_nameservers"] == ["8.8.8.8"]
        assert data["confidence"] == 1.0

    def test_tailscale_network_deserialization(self) -> None:
        """Test TailscaleNetwork can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "network_id": "net-123",
            "name": "main-network",
            "cidr": "100.64.0.0/10",
            "global_nameservers": ["8.8.8.8"],
            "search_domains": ["example.com"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "tailscale_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        network = TailscaleNetwork.model_validate(data)
        assert network.network_id == "net-123"
        assert network.name == "main-network"
        assert network.cidr == "100.64.0.0/10"
        assert network.global_nameservers == ["8.8.8.8"]
        assert network.search_domains == ["example.com"]

    def test_tailscale_network_empty_lists(self) -> None:
        """Test TailscaleNetwork handles empty list fields."""
        now = datetime.now(UTC)
        network = TailscaleNetwork(
            network_id="net-123",
            name="main-network",
            cidr="100.64.0.0/10",
            global_nameservers=[],
            search_domains=[],
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert network.global_nameservers == []
        assert network.search_domains == []
