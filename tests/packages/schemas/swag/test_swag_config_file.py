"""Tests for SwagConfigFile entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- File path validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.swag.swag_config_file import SwagConfigFile


class TestSwagConfigFileEntity:
    """Test suite for SwagConfigFile entity."""

    def test_swag_config_file_minimal_valid(self) -> None:
        """Test SwagConfigFile with only required fields."""
        now = datetime.now(UTC)
        config_file = SwagConfigFile(
            file_path="/config/nginx/site-confs/default",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert config_file.file_path == "/config/nginx/site-confs/default"
        assert config_file.created_at == now
        assert config_file.updated_at == now
        assert config_file.extraction_tier == "A"
        assert config_file.extraction_method == "nginx_parser"
        assert config_file.confidence == 1.0
        assert config_file.extractor_version == "1.0.0"
        assert config_file.version is None
        assert config_file.parsed_at is None
        assert config_file.source_timestamp is None

    def test_swag_config_file_full_valid(self) -> None:
        """Test SwagConfigFile with all fields populated."""
        now = datetime.now(UTC)
        parsed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        config_file = SwagConfigFile(
            file_path="/config/nginx/site-confs/myapp.conf",
            version="1.0",
            parsed_at=parsed_time,
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="2.0.0",
        )

        assert config_file.file_path == "/config/nginx/site-confs/myapp.conf"
        assert config_file.version == "1.0"
        assert config_file.parsed_at == parsed_time
        assert config_file.source_timestamp == source_time
        assert config_file.extraction_tier == "A"
        assert config_file.confidence == 1.0
        assert config_file.extractor_version == "2.0.0"

    def test_swag_config_file_missing_required_file_path(self) -> None:
        """Test SwagConfigFile validation fails without file_path."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            SwagConfigFile(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("file_path",) for e in errors)

    def test_swag_config_file_empty_file_path(self) -> None:
        """Test SwagConfigFile validation fails with empty file_path."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            SwagConfigFile(
                file_path="",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("file_path",) for e in errors)

    def test_swag_config_file_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            SwagConfigFile(
                file_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_swag_config_file_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            SwagConfigFile(
                file_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_swag_config_file_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            config_file = SwagConfigFile(
                file_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert config_file.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            SwagConfigFile(
                file_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_swag_config_file_serialization(self) -> None:
        """Test SwagConfigFile can be serialized to dict."""
        now = datetime.now(UTC)
        config_file = SwagConfigFile(
            file_path="/config/nginx/site-confs/myapp.conf",
            version="1.0",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = config_file.model_dump()
        assert data["file_path"] == "/config/nginx/site-confs/myapp.conf"
        assert data["version"] == "1.0"
        assert data["confidence"] == 1.0

    def test_swag_config_file_deserialization(self) -> None:
        """Test SwagConfigFile can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "file_path": "/config/nginx/site-confs/myapp.conf",
            "version": "1.0",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "nginx_parser",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        config_file = SwagConfigFile.model_validate(data)
        assert config_file.file_path == "/config/nginx/site-confs/myapp.conf"
        assert config_file.version == "1.0"
