"""Tests for Thread entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Thread metadata validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.gmail.thread import Thread


class TestThreadEntity:
    """Test suite for Thread entity."""

    def test_thread_minimal_valid(self) -> None:
        """Test Thread with only required fields."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        thread = Thread(
            thread_id="thread_67890",
            subject="Project Discussion",
            message_count=3,
            participant_count=2,
            first_message_at=first_msg,
            last_message_at=last_msg,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert thread.thread_id == "thread_67890"
        assert thread.subject == "Project Discussion"
        assert thread.message_count == 3
        assert thread.participant_count == 2
        assert thread.first_message_at == first_msg
        assert thread.last_message_at == last_msg
        assert thread.labels == []

    def test_thread_full_valid(self) -> None:
        """Test Thread with all fields populated."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        thread = Thread(
            thread_id="thread_67890",
            subject="Re: Project Discussion",
            message_count=5,
            participant_count=3,
            first_message_at=first_msg,
            last_message_at=last_msg,
            labels=["INBOX", "IMPORTANT", "CATEGORY_WORK"],
            created_at=now,
            updated_at=now,
            source_timestamp=first_msg,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert thread.thread_id == "thread_67890"
        assert thread.subject == "Re: Project Discussion"
        assert thread.message_count == 5
        assert thread.participant_count == 3
        assert thread.first_message_at == first_msg
        assert thread.last_message_at == last_msg
        assert thread.labels == ["INBOX", "IMPORTANT", "CATEGORY_WORK"]
        assert thread.source_timestamp == first_msg

    def test_thread_missing_required_thread_id(self) -> None:
        """Test Thread validation fails without thread_id."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Thread(
                subject="Test",
                message_count=3,
                participant_count=2,
                first_message_at=first_msg,
                last_message_at=last_msg,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("thread_id",) for e in errors)

    def test_thread_missing_required_subject(self) -> None:
        """Test Thread validation fails without subject."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Thread(
                thread_id="thread_67890",
                message_count=3,
                participant_count=2,
                first_message_at=first_msg,
                last_message_at=last_msg,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("subject",) for e in errors)

    def test_thread_negative_message_count(self) -> None:
        """Test Thread validation fails with negative message_count."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Thread(
                thread_id="thread_67890",
                subject="Test",
                message_count=-1,
                participant_count=2,
                first_message_at=first_msg,
                last_message_at=last_msg,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("message_count",) for e in errors)

    def test_thread_zero_message_count(self) -> None:
        """Test Thread validation fails with zero message_count."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Thread(
                thread_id="thread_67890",
                subject="Test",
                message_count=0,
                participant_count=2,
                first_message_at=first_msg,
                last_message_at=last_msg,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("message_count",) for e in errors)

    def test_thread_negative_participant_count(self) -> None:
        """Test Thread validation fails with negative participant_count."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Thread(
                thread_id="thread_67890",
                subject="Test",
                message_count=3,
                participant_count=-1,
                first_message_at=first_msg,
                last_message_at=last_msg,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("participant_count",) for e in errors)

    def test_thread_zero_participant_count(self) -> None:
        """Test Thread validation fails with zero participant_count."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Thread(
                thread_id="thread_67890",
                subject="Test",
                message_count=3,
                participant_count=0,
                first_message_at=first_msg,
                last_message_at=last_msg,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("participant_count",) for e in errors)

    def test_thread_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Thread(
                thread_id="thread_67890",
                subject="Test",
                message_count=3,
                participant_count=2,
                first_message_at=first_msg,
                last_message_at=last_msg,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_thread_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Thread(
                thread_id="thread_67890",
                subject="Test",
                message_count=3,
                participant_count=2,
                first_message_at=first_msg,
                last_message_at=last_msg,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.5,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_thread_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            thread = Thread(
                thread_id="thread_67890",
                subject="Test",
                message_count=3,
                participant_count=2,
                first_message_at=first_msg,
                last_message_at=last_msg,
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert thread.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Thread(
                thread_id="thread_67890",
                subject="Test",
                message_count=3,
                participant_count=2,
                first_message_at=first_msg,
                last_message_at=last_msg,
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_thread_serialization(self) -> None:
        """Test Thread can be serialized to dict."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        thread = Thread(
            thread_id="thread_67890",
            subject="Project Discussion",
            message_count=3,
            participant_count=2,
            first_message_at=first_msg,
            last_message_at=last_msg,
            labels=["INBOX", "IMPORTANT"],
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = thread.model_dump()
        assert data["thread_id"] == "thread_67890"
        assert data["subject"] == "Project Discussion"
        assert data["message_count"] == 3
        assert data["participant_count"] == 2
        assert data["labels"] == ["INBOX", "IMPORTANT"]

    def test_thread_deserialization(self) -> None:
        """Test Thread can be deserialized from dict."""
        now = datetime.now(UTC)
        first_msg = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        last_msg = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        data = {
            "thread_id": "thread_67890",
            "subject": "Project Discussion",
            "message_count": 3,
            "participant_count": 2,
            "first_message_at": first_msg.isoformat(),
            "last_message_at": last_msg.isoformat(),
            "labels": ["INBOX"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "gmail_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        thread = Thread.model_validate(data)
        assert thread.thread_id == "thread_67890"
        assert thread.subject == "Project Discussion"
        assert thread.message_count == 3
        assert thread.labels == ["INBOX"]
