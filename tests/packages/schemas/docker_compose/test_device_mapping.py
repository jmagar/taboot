"""Tests for DeviceMapping entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.device_mapping import DeviceMapping


class TestDeviceMappingEntity:
    """Test suite for DeviceMapping entity."""

    def test_device_mapping_minimal_valid(self) -> None:
        """Test DeviceMapping with only required fields."""
        now = datetime.now(UTC)
        device = DeviceMapping(
            host_device="/dev/sda",
            container_device="/dev/xvda",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert device.host_device == "/dev/sda"
        assert device.container_device == "/dev/xvda"
        assert device.permissions is None

    def test_device_mapping_with_permissions(self) -> None:
        """Test DeviceMapping with permissions."""
        now = datetime.now(UTC)
        device = DeviceMapping(
            host_device="/dev/video0",
            container_device="/dev/video0",
            permissions="rwm",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert device.permissions == "rwm"

    def test_device_mapping_missing_required_host_device(self) -> None:
        """Test DeviceMapping validation fails without host_device."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            DeviceMapping(
                container_device="/dev/xvda",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("host_device",) for e in errors)
