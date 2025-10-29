"""Tests for GmailLabel entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Label type validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.gmail.gmail_label import GmailLabel


class TestGmailLabelEntity:
    """Test suite for GmailLabel entity."""

    def test_gmail_label_minimal_valid(self) -> None:
        """Test GmailLabel with only required fields."""
        now = datetime.now(UTC)

        label = GmailLabel(
            label_id="Label_1",
            name="Work",
            type="user",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert label.label_id == "Label_1"
        assert label.name == "Work"
        assert label.type == "user"
        assert label.color is None
        assert label.message_count is None

    def test_gmail_label_full_valid(self) -> None:
        """Test GmailLabel with all fields populated."""
        now = datetime.now(UTC)

        label = GmailLabel(
            label_id="Label_1",
            name="Important Work",
            type="user",
            color="#ff0000",
            message_count=42,
            created_at=now,
            updated_at=now,
            source_timestamp=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert label.label_id == "Label_1"
        assert label.name == "Important Work"
        assert label.type == "user"
        assert label.color == "#ff0000"
        assert label.message_count == 42
        assert label.source_timestamp == now

    def test_gmail_label_system_type(self) -> None:
        """Test GmailLabel with system type."""
        now = datetime.now(UTC)

        label = GmailLabel(
            label_id="INBOX",
            name="INBOX",
            type="system",
            message_count=150,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert label.label_id == "INBOX"
        assert label.name == "INBOX"
        assert label.type == "system"
        assert label.message_count == 150

    def test_gmail_label_missing_required_label_id(self) -> None:
        """Test GmailLabel validation fails without label_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            GmailLabel(
                name="Work",
                type="user",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("label_id",) for e in errors)

    def test_gmail_label_missing_required_name(self) -> None:
        """Test GmailLabel validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            GmailLabel(
                label_id="Label_1",
                type="user",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_gmail_label_missing_required_type(self) -> None:
        """Test GmailLabel validation fails without type."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            GmailLabel(
                label_id="Label_1",
                name="Work",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("type",) for e in errors)

    def test_gmail_label_invalid_type(self) -> None:
        """Test GmailLabel validation fails with invalid type."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            GmailLabel(
                label_id="Label_1",
                name="Work",
                type="invalid",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("type",) for e in errors)

    def test_gmail_label_negative_message_count(self) -> None:
        """Test GmailLabel validation fails with negative message_count."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            GmailLabel(
                label_id="Label_1",
                name="Work",
                type="user",
                message_count=-1,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("message_count",) for e in errors)

    def test_gmail_label_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            GmailLabel(
                label_id="Label_1",
                name="Work",
                type="user",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_gmail_label_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            GmailLabel(
                label_id="Label_1",
                name="Work",
                type="user",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.5,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_gmail_label_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            label = GmailLabel(
                label_id="Label_1",
                name="Work",
                type="user",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert label.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            GmailLabel(
                label_id="Label_1",
                name="Work",
                type="user",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_gmail_label_serialization(self) -> None:
        """Test GmailLabel can be serialized to dict."""
        now = datetime.now(UTC)

        label = GmailLabel(
            label_id="Label_1",
            name="Work",
            type="user",
            color="#ff0000",
            message_count=42,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = label.model_dump()
        assert data["label_id"] == "Label_1"
        assert data["name"] == "Work"
        assert data["type"] == "user"
        assert data["color"] == "#ff0000"
        assert data["message_count"] == 42

    def test_gmail_label_deserialization(self) -> None:
        """Test GmailLabel can be deserialized from dict."""
        now = datetime.now(UTC)

        data = {
            "label_id": "Label_1",
            "name": "Work",
            "type": "user",
            "color": "#ff0000",
            "message_count": 42,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "gmail_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        label = GmailLabel.model_validate(data)
        assert label.label_id == "Label_1"
        assert label.name == "Work"
        assert label.type == "user"
        assert label.color == "#ff0000"
        assert label.message_count == 42

    def test_gmail_label_validate_type_direct(self) -> None:
        """Ensure the type validator raises for unsupported values."""
        with pytest.raises(ValueError, match="type must be"):
            GmailLabel.validate_type("invalid")

    def test_gmail_label_validate_extraction_tier_direct(self) -> None:
        """Ensure the extraction_tier validator raises for unsupported values."""
        with pytest.raises(ValueError, match="extraction_tier"):
            GmailLabel.validate_extraction_tier("Z")
