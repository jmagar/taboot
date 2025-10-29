"""Tests for ImageDetails entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.image_details import ImageDetails


class TestImageDetailsEntity:
    """Test suite for ImageDetails entity."""

    def test_image_details_minimal_valid(self) -> None:
        """Test ImageDetails with only required fields."""
        now = datetime.now(UTC)
        image = ImageDetails(
            compose_file_path="/tmp/docker-compose.yml",
            service_name="web",
            image_name="nginx",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert image.image_name == "nginx"
        assert image.compose_file_path == "/tmp/docker-compose.yml"
        assert image.service_name == "web"
        assert image.tag is None
        assert image.registry is None

    def test_image_details_full_valid(self) -> None:
        """Test ImageDetails with all fields populated."""
        now = datetime.now(UTC)
        image = ImageDetails(
            compose_file_path="/tmp/docker-compose.yml",
            service_name="api",
            image_name="myapp",
            tag="1.2.3",
            registry="gcr.io/myproject",
            digest="sha256:abcdef123456",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert image.image_name == "myapp"
        assert image.tag == "1.2.3"
        assert image.registry == "gcr.io/myproject"
        assert image.digest == "sha256:abcdef123456"
        assert image.compose_file_path == "/tmp/docker-compose.yml"
        assert image.service_name == "api"

    def test_image_details_missing_required_name(self) -> None:
        """Test ImageDetails validation fails without image_name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ImageDetails(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("image_name",) for e in errors)
        assert any(e["loc"] == ("compose_file_path",) for e in errors)
        assert any(e["loc"] == ("service_name",) for e in errors)
