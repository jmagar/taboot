"""Tests for Attachment entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Attachment metadata validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.gmail.attachment import Attachment


class TestAttachmentEntity:
    """Test suite for Attachment entity."""

    def test_attachment_minimal_valid(self) -> None:
        """Test Attachment with only required fields."""
        now = datetime.now(UTC)

        attachment = Attachment(
            attachment_id="attach_12345",
            filename="document.pdf",
            mime_type="application/pdf",
            size=1024000,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert attachment.attachment_id == "attach_12345"
        assert attachment.filename == "document.pdf"
        assert attachment.mime_type == "application/pdf"
        assert attachment.size == 1024000
        assert attachment.content_hash is None
        assert attachment.is_inline is False

    def test_attachment_full_valid(self) -> None:
        """Test Attachment with all fields populated."""
        now = datetime.now(UTC)

        attachment = Attachment(
            attachment_id="attach_12345",
            filename="report.pdf",
            mime_type="application/pdf",
            size=2048000,
            content_hash="sha256:abc123def456",
            is_inline=True,
            created_at=now,
            updated_at=now,
            source_timestamp=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert attachment.attachment_id == "attach_12345"
        assert attachment.filename == "report.pdf"
        assert attachment.mime_type == "application/pdf"
        assert attachment.size == 2048000
        assert attachment.content_hash == "sha256:abc123def456"
        assert attachment.is_inline is True
        assert attachment.source_timestamp == now

    def test_attachment_image_inline(self) -> None:
        """Test Attachment for inline image."""
        now = datetime.now(UTC)

        attachment = Attachment(
            attachment_id="attach_img_001",
            filename="logo.png",
            mime_type="image/png",
            size=50000,
            is_inline=True,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert attachment.attachment_id == "attach_img_001"
        assert attachment.filename == "logo.png"
        assert attachment.mime_type == "image/png"
        assert attachment.size == 50000
        assert attachment.is_inline is True

    def test_attachment_missing_required_attachment_id(self) -> None:
        """Test Attachment validation fails without attachment_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Attachment(
                filename="document.pdf",
                mime_type="application/pdf",
                size=1024000,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("attachment_id",) for e in errors)

    def test_attachment_missing_required_filename(self) -> None:
        """Test Attachment validation fails without filename."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Attachment(
                attachment_id="attach_12345",
                mime_type="application/pdf",
                size=1024000,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("filename",) for e in errors)

    def test_attachment_missing_required_mime_type(self) -> None:
        """Test Attachment validation fails without mime_type."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Attachment(
                attachment_id="attach_12345",
                filename="document.pdf",
                size=1024000,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("mime_type",) for e in errors)

    def test_attachment_missing_required_size(self) -> None:
        """Test Attachment validation fails without size."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Attachment(
                attachment_id="attach_12345",
                filename="document.pdf",
                mime_type="application/pdf",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("size",) for e in errors)

    def test_attachment_negative_size(self) -> None:
        """Test Attachment validation fails with negative size."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Attachment(
                attachment_id="attach_12345",
                filename="document.pdf",
                mime_type="application/pdf",
                size=-1024,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("size",) for e in errors)

    def test_attachment_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Attachment(
                attachment_id="attach_12345",
                filename="document.pdf",
                mime_type="application/pdf",
                size=1024000,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_attachment_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Attachment(
                attachment_id="attach_12345",
                filename="document.pdf",
                mime_type="application/pdf",
                size=1024000,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.5,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_attachment_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            attachment = Attachment(
                attachment_id="attach_12345",
                filename="document.pdf",
                mime_type="application/pdf",
                size=1024000,
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert attachment.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Attachment(
                attachment_id="attach_12345",
                filename="document.pdf",
                mime_type="application/pdf",
                size=1024000,
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_attachment_serialization(self) -> None:
        """Test Attachment can be serialized to dict."""
        now = datetime.now(UTC)

        attachment = Attachment(
            attachment_id="attach_12345",
            filename="report.pdf",
            mime_type="application/pdf",
            size=2048000,
            content_hash="sha256:abc123",
            is_inline=False,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = attachment.model_dump()
        assert data["attachment_id"] == "attach_12345"
        assert data["filename"] == "report.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["size"] == 2048000
        assert data["content_hash"] == "sha256:abc123"
        assert data["is_inline"] is False

    def test_attachment_deserialization(self) -> None:
        """Test Attachment can be deserialized from dict."""
        now = datetime.now(UTC)

        data = {
            "attachment_id": "attach_12345",
            "filename": "report.pdf",
            "mime_type": "application/pdf",
            "size": 2048000,
            "content_hash": "sha256:abc123",
            "is_inline": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "gmail_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        attachment = Attachment.model_validate(data)
        assert attachment.attachment_id == "attach_12345"
        assert attachment.filename == "report.pdf"
        assert attachment.mime_type == "application/pdf"
        assert attachment.size == 2048000
        assert attachment.content_hash == "sha256:abc123"
        assert attachment.is_inline is True

    def test_attachment_validate_extraction_tier_direct(self) -> None:
        """Ensure the extraction_tier validator raises for unsupported values."""
        with pytest.raises(ValueError, match="extraction_tier"):
            Attachment.validate_extraction_tier("Z")
