"""Tests for Email entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Email metadata validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.gmail.email import Email


class TestEmailEntity:
    """Test suite for Email entity."""

    def test_email_minimal_valid(self) -> None:
        """Test Email with only required fields."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        email = Email(
            message_id="msg_12345",
            thread_id="thread_67890",
            subject="Test Subject",
            snippet="This is a test email snippet...",
            sent_at=sent_at,
            size_estimate=1024,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert email.message_id == "msg_12345"
        assert email.thread_id == "thread_67890"
        assert email.subject == "Test Subject"
        assert email.snippet == "This is a test email snippet..."
        assert email.sent_at == sent_at
        assert email.size_estimate == 1024
        assert email.body is None
        assert email.labels == []
        assert email.has_attachments is False
        assert email.in_reply_to is None
        assert email.references == []

    def test_email_full_valid(self) -> None:
        """Test Email with all fields populated."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        email = Email(
            message_id="msg_12345",
            thread_id="thread_67890",
            subject="Re: Project Update",
            snippet="Thanks for the update...",
            body="Full email body content here",
            sent_at=sent_at,
            labels=["INBOX", "IMPORTANT", "CATEGORY_PERSONAL"],
            size_estimate=2048,
            has_attachments=True,
            in_reply_to="msg_11111",
            references=["msg_11111", "msg_11112"],
            created_at=now,
            updated_at=now,
            source_timestamp=sent_at,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert email.message_id == "msg_12345"
        assert email.thread_id == "thread_67890"
        assert email.subject == "Re: Project Update"
        assert email.snippet == "Thanks for the update..."
        assert email.body == "Full email body content here"
        assert email.sent_at == sent_at
        assert email.labels == ["INBOX", "IMPORTANT", "CATEGORY_PERSONAL"]
        assert email.size_estimate == 2048
        assert email.has_attachments is True
        assert email.in_reply_to == "msg_11111"
        assert email.references == ["msg_11111", "msg_11112"]
        assert email.source_timestamp == sent_at

    def test_email_missing_required_message_id(self) -> None:
        """Test Email validation fails without message_id."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Email(
                thread_id="thread_67890",
                subject="Test",
                snippet="Test snippet",
                sent_at=sent_at,
                size_estimate=1024,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("message_id",) for e in errors)

    def test_email_missing_required_thread_id(self) -> None:
        """Test Email validation fails without thread_id."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Email(
                message_id="msg_12345",
                subject="Test",
                snippet="Test snippet",
                sent_at=sent_at,
                size_estimate=1024,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("thread_id",) for e in errors)

    def test_email_missing_required_subject(self) -> None:
        """Test Email validation fails without subject."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Email(
                message_id="msg_12345",
                thread_id="thread_67890",
                snippet="Test snippet",
                sent_at=sent_at,
                size_estimate=1024,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("subject",) for e in errors)

    def test_email_missing_required_sent_at(self) -> None:
        """Test Email validation fails without sent_at."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Email(
                message_id="msg_12345",
                thread_id="thread_67890",
                subject="Test",
                snippet="Test snippet",
                size_estimate=1024,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("sent_at",) for e in errors)

    def test_email_negative_size_estimate(self) -> None:
        """Test Email validation fails with negative size_estimate."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Email(
                message_id="msg_12345",
                thread_id="thread_67890",
                subject="Test",
                snippet="Test snippet",
                sent_at=sent_at,
                size_estimate=-100,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("size_estimate",) for e in errors)

    def test_email_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Email(
                message_id="msg_12345",
                thread_id="thread_67890",
                subject="Test",
                snippet="Test snippet",
                sent_at=sent_at,
                size_estimate=1024,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_email_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Email(
                message_id="msg_12345",
                thread_id="thread_67890",
                subject="Test",
                snippet="Test snippet",
                sent_at=sent_at,
                size_estimate=1024,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.5,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_email_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            email = Email(
                message_id="msg_12345",
                thread_id="thread_67890",
                subject="Test",
                snippet="Test snippet",
                sent_at=sent_at,
                size_estimate=1024,
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert email.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Email(
                message_id="msg_12345",
                thread_id="thread_67890",
                subject="Test",
                snippet="Test snippet",
                sent_at=sent_at,
                size_estimate=1024,
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_email_serialization(self) -> None:
        """Test Email can be serialized to dict."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        email = Email(
            message_id="msg_12345",
            thread_id="thread_67890",
            subject="Test Subject",
            snippet="Test snippet",
            sent_at=sent_at,
            size_estimate=1024,
            labels=["INBOX"],
            has_attachments=True,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = email.model_dump()
        assert data["message_id"] == "msg_12345"
        assert data["thread_id"] == "thread_67890"
        assert data["subject"] == "Test Subject"
        assert data["labels"] == ["INBOX"]
        assert data["has_attachments"] is True

    def test_email_deserialization(self) -> None:
        """Test Email can be deserialized from dict."""
        now = datetime.now(UTC)
        sent_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        data = {
            "message_id": "msg_12345",
            "thread_id": "thread_67890",
            "subject": "Test Subject",
            "snippet": "Test snippet",
            "sent_at": sent_at.isoformat(),
            "size_estimate": 1024,
            "labels": ["INBOX", "IMPORTANT"],
            "has_attachments": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "gmail_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        email = Email.model_validate(data)
        assert email.message_id == "msg_12345"
        assert email.thread_id == "thread_67890"
        assert email.subject == "Test Subject"
        assert email.labels == ["INBOX", "IMPORTANT"]

    def test_email_validate_extraction_tier_direct(self) -> None:
        """Ensure the extraction_tier validator raises for unsupported values."""
        with pytest.raises(ValueError, match="extraction_tier"):
            Email.validate_extraction_tier("Z")
