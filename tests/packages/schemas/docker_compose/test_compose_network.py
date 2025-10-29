"""Tests for ComposeNetwork entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.compose_network import ComposeNetwork


class TestComposeNetworkEntity:
    """Test suite for ComposeNetwork entity."""

    def test_compose_network_minimal_valid(self) -> None:
        """Test ComposeNetwork with only required fields."""
        now = datetime.now(UTC)
        network = ComposeNetwork(
            name="backend",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert network.name == "backend"
        assert network.driver is None
        assert network.external is None

    def test_compose_network_full_valid(self) -> None:
        """Test ComposeNetwork with all fields populated."""
        now = datetime.now(UTC)
        network = ComposeNetwork(
            name="frontend",
            driver="bridge",
            external=False,
            enable_ipv6=True,
            ipam_driver="default",
            ipam_config={"subnet": "172.28.0.0/16"},
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert network.name == "frontend"
        assert network.driver == "bridge"
        assert network.enable_ipv6 is True

    def test_compose_network_missing_required_name(self) -> None:
        """Test ComposeNetwork validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ComposeNetwork(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)
