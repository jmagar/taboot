"""Tests for Person entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Email validation
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.schemas.core.person import Person


class TestPersonEntity:
    """Test suite for Person entity."""

    def test_person_minimal_valid(self) -> None:
        """Test Person with only required fields."""
        now = datetime.now(UTC)
        person = Person(
            name="John Doe",
            email="john.doe@example.com",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert person.name == "John Doe"
        assert person.email == "john.doe@example.com"
        assert person.created_at == now
        assert person.updated_at == now
        assert person.extraction_tier == "A"
        assert person.extraction_method == "github_api"
        assert person.confidence == 1.0
        assert person.extractor_version == "1.0.0"
        assert person.role is None
        assert person.bio is None
        assert person.github_username is None
        assert person.reddit_username is None
        assert person.youtube_channel is None
        assert person.source_timestamp is None

    def test_person_full_valid(self) -> None:
        """Test Person with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        person = Person(
            name="Jane Smith",
            email="jane.smith@example.com",
            role="Senior Engineer",
            bio="Passionate about open source and Python",
            github_username="janesmith",
            reddit_username="jane_dev",
            youtube_channel="@janesmithdev",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="B",
            extraction_method="spacy_ner",
            confidence=0.85,
            extractor_version="1.2.0",
        )

        assert person.name == "Jane Smith"
        assert person.email == "jane.smith@example.com"
        assert person.role == "Senior Engineer"
        assert person.bio == "Passionate about open source and Python"
        assert person.github_username == "janesmith"
        assert person.reddit_username == "jane_dev"
        assert person.youtube_channel == "@janesmithdev"
        assert person.source_timestamp == source_time
        assert person.extraction_tier == "B"
        assert person.confidence == 0.85

    def test_person_missing_required_name(self) -> None:
        """Test Person validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Person(
                email="test@example.com",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_person_missing_required_email(self) -> None:
        """Test Person validation fails without email."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Person(
                name="Test User",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)

    def test_person_invalid_email_format(self) -> None:
        """Test Person validation fails with invalid email."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Person(
                name="Test User",
                email="not-an-email",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)

    def test_person_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Person(
                name="Test User",
                email="test@example.com",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_person_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Person(
                name="Test User",
                email="test@example.com",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_person_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            person = Person(
                name="Test User",
                email="test@example.com",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert person.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Person(
                name="Test User",
                email="test@example.com",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_person_serialization(self) -> None:
        """Test Person can be serialized to dict."""
        now = datetime.now(UTC)
        person = Person(
            name="Test User",
            email="test@example.com",
            role="Engineer",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="regex",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = person.model_dump()
        assert data["name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert data["role"] == "Engineer"
        assert data["confidence"] == 1.0

    def test_person_deserialization(self) -> None:
        """Test Person can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "name": "Test User",
            "email": "test@example.com",
            "role": "Engineer",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "regex",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        person = Person.model_validate(data)
        assert person.name == "Test User"
        assert person.email == "test@example.com"
        assert person.role == "Engineer"
