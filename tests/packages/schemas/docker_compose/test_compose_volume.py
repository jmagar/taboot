"""Tests for ComposeVolume entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.compose_volume import ComposeVolume


class TestComposeVolumeEntity:
    """Test suite for ComposeVolume entity."""

    def test_compose_volume_minimal_valid(self) -> None:
        """Test ComposeVolume with only required fields."""
        now = datetime.now(UTC)
        volume = ComposeVolume(
            name="data",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert volume.name == "data"
        assert volume.driver is None
        assert volume.external is None

    def test_compose_volume_full_valid(self) -> None:
        """Test ComposeVolume with all fields populated."""
        now = datetime.now(UTC)
        volume = ComposeVolume(
            name="postgres-data",
            driver="local",
            external=False,
            driver_opts={"type": "nfs", "device": ":/mnt/data"},
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert volume.name == "postgres-data"
        assert volume.driver == "local"
        assert volume.driver_opts == {"type": "nfs", "device": ":/mnt/data"}

    def test_compose_volume_missing_required_name(self) -> None:
        """Test ComposeVolume validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ComposeVolume(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)
