"""Tests for File entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- URL and mime_type validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.core.file import File


class TestFileEntity:
    """Test suite for File entity."""

    def test_file_minimal_valid(self) -> None:
        """Test File with only required fields."""
        now = datetime.now(UTC)
        file = File(
            name="README.md",
            file_id="file_12345",
            source="github",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert file.name == "README.md"
        assert file.file_id == "file_12345"
        assert file.source == "github"
        assert file.created_at == now
        assert file.updated_at == now
        assert file.extraction_tier == "A"
        assert file.extraction_method == "github_api"
        assert file.confidence == 1.0
        assert file.extractor_version == "1.0.0"
        assert file.mime_type is None
        assert file.size_bytes is None
        assert file.url is None
        assert file.source_timestamp is None

    def test_file_full_valid(self) -> None:
        """Test File with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        file = File(
            name="document.pdf",
            file_id="file_67890",
            source="gmail",
            mime_type="application/pdf",
            size_bytes=1024000,
            url="https://example.com/document.pdf",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="B",
            extraction_method="gmail_api",
            confidence=0.95,
            extractor_version="1.2.0",
        )

        assert file.name == "document.pdf"
        assert file.file_id == "file_67890"
        assert file.source == "gmail"
        assert file.mime_type == "application/pdf"
        assert file.size_bytes == 1024000
        assert file.url == "https://example.com/document.pdf"
        assert file.source_timestamp == source_time
        assert file.extraction_tier == "B"
        assert file.confidence == 0.95

    def test_file_missing_required_name(self) -> None:
        """Test File validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            File(
                file_id="test",
                source="github",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_file_missing_required_file_id(self) -> None:
        """Test File validation fails without file_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            File(
                name="test.txt",
                source="github",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("file_id",) for e in errors)

    def test_file_missing_required_source(self) -> None:
        """Test File validation fails without source."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            File(
                name="test.txt",
                file_id="test",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source",) for e in errors)

    def test_file_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            File(
                name="test.txt",
                file_id="test",
                source="github",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_file_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            File(
                name="test.txt",
                file_id="test",
                source="github",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_file_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            file = File(
                name="test.txt",
                file_id="test",
                source="github",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert file.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            File(
                name="test.txt",
                file_id="test",
                source="github",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_file_size_bytes_validation(self) -> None:
        """Test size_bytes must be >= 0."""
        now = datetime.now(UTC)

        # Valid size
        file = File(
            name="test.txt",
            file_id="test",
            source="github",
            size_bytes=0,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="regex",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        assert file.size_bytes == 0

        # Invalid size
        with pytest.raises(ValidationError) as exc_info:
            File(
                name="test.txt",
                file_id="test",
                source="github",
                size_bytes=-1,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("size_bytes",) for e in errors)

    def test_file_serialization(self) -> None:
        """Test File can be serialized to dict."""
        now = datetime.now(UTC)
        file = File(
            name="test.txt",
            file_id="test",
            source="github",
            mime_type="text/plain",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="regex",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = file.model_dump()
        assert data["name"] == "test.txt"
        assert data["file_id"] == "test"
        assert data["source"] == "github"
        assert data["mime_type"] == "text/plain"
        assert data["confidence"] == 1.0

    def test_file_deserialization(self) -> None:
        """Test File can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "name": "test.txt",
            "file_id": "test",
            "source": "github",
            "mime_type": "text/plain",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "regex",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        file = File.model_validate(data)
        assert file.name == "test.txt"
        assert file.file_id == "test"
        assert file.source == "github"
        assert file.mime_type == "text/plain"
