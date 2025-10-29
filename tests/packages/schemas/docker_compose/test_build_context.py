"""Tests for BuildContext entity schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.build_context import BuildContext


class TestBuildContextEntity:
    """Test suite for BuildContext entity."""

    def test_build_context_minimal_valid(self) -> None:
        """Test BuildContext with only required fields."""
        now = datetime.now(UTC)
        build = BuildContext(
            context_path=".",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert build.context_path == "."
        assert build.dockerfile is None
        assert build.target is None

    def test_build_context_full_valid(self) -> None:
        """Test BuildContext with all fields populated."""
        now = datetime.now(UTC)
        build = BuildContext(
            context_path="./api",
            dockerfile="Dockerfile.prod",
            target="production",
            args={"NODE_ENV": "production", "VERSION": "1.2.3"},
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert build.context_path == "./api"
        assert build.dockerfile == "Dockerfile.prod"
        assert build.target == "production"
        assert build.args == {"NODE_ENV": "production", "VERSION": "1.2.3"}

    def test_build_context_missing_required_context_path(self) -> None:
        """Test BuildContext validation fails without context_path."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BuildContext(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("context_path",) for e in errors)
