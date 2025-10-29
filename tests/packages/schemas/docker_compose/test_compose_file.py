"""Tests for ComposeFile entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.docker_compose.compose_file import ComposeFile


class TestComposeFileEntity:
    """Test suite for ComposeFile entity."""

    def test_compose_file_minimal_valid(self) -> None:
        """Test ComposeFile with only required fields."""
        now = datetime.now(UTC)
        compose_file = ComposeFile(
            file_path="/path/to/docker-compose.yml",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert compose_file.file_path == "/path/to/docker-compose.yml"
        assert compose_file.created_at == now
        assert compose_file.updated_at == now
        assert compose_file.extraction_tier == "A"
        assert compose_file.extraction_method == "yaml_parser"
        assert compose_file.confidence == 1.0
        assert compose_file.extractor_version == "1.0.0"
        assert compose_file.version is None
        assert compose_file.project_name is None
        assert compose_file.source_timestamp is None

    def test_compose_file_full_valid(self) -> None:
        """Test ComposeFile with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        compose_file = ComposeFile(
            file_path="/home/user/project/docker-compose.yml",
            version="3.8",
            project_name="my-project",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert compose_file.file_path == "/home/user/project/docker-compose.yml"
        assert compose_file.version == "3.8"
        assert compose_file.project_name == "my-project"
        assert compose_file.source_timestamp == source_time
        assert compose_file.extraction_tier == "A"
        assert compose_file.confidence == 1.0

    def test_compose_file_missing_required_file_path(self) -> None:
        """Test ComposeFile validation fails without file_path."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ComposeFile(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("file_path",) for e in errors)

    def test_compose_file_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ComposeFile(
                file_path="/path/to/docker-compose.yml",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_compose_file_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ComposeFile(
                file_path="/path/to/docker-compose.yml",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="yaml_parser",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_compose_file_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            compose_file = ComposeFile(
                file_path="/path/to/docker-compose.yml",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert compose_file.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            ComposeFile(
                file_path="/path/to/docker-compose.yml",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="yaml_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_compose_file_serialization(self) -> None:
        """Test ComposeFile can be serialized to dict."""
        now = datetime.now(UTC)
        compose_file = ComposeFile(
            file_path="/path/to/docker-compose.yml",
            version="3.8",
            project_name="test-project",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="yaml_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = compose_file.model_dump()
        assert data["file_path"] == "/path/to/docker-compose.yml"
        assert data["version"] == "3.8"
        assert data["project_name"] == "test-project"
        assert data["confidence"] == 1.0

    def test_compose_file_deserialization(self) -> None:
        """Test ComposeFile can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "file_path": "/path/to/docker-compose.yml",
            "version": "3.8",
            "project_name": "test-project",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "yaml_parser",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        compose_file = ComposeFile.model_validate(data)
        assert compose_file.file_path == "/path/to/docker-compose.yml"
        assert compose_file.version == "3.8"
        assert compose_file.project_name == "test-project"
