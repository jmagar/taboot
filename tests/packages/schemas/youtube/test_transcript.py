"""Tests for Transcript entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Language code validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.youtube.transcript import Transcript


class TestTranscriptEntity:
    """Test suite for Transcript entity."""

    def test_transcript_minimal_valid(self) -> None:
        """Test Transcript with only required fields."""
        now = datetime.now(UTC)

        transcript = Transcript(
            transcript_id="dQw4w9WgXcQ_en",
            video_id="dQw4w9WgXcQ",
            language="en",
            content="Never gonna give you up, never gonna let you down...",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="youtube_transcript_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert transcript.transcript_id == "dQw4w9WgXcQ_en"
        assert transcript.video_id == "dQw4w9WgXcQ"
        assert transcript.language == "en"
        assert transcript.content == "Never gonna give you up, never gonna let you down..."
        assert transcript.auto_generated is False  # default value
        assert transcript.created_at == now
        assert transcript.updated_at == now
        assert transcript.extraction_tier == "A"
        assert transcript.extraction_method == "youtube_transcript_api"
        assert transcript.confidence == 1.0
        assert transcript.extractor_version == "1.0.0"
        assert transcript.source_timestamp is None

    def test_transcript_full_valid(self) -> None:
        """Test Transcript with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        transcript = Transcript(
            transcript_id="test123_es",
            video_id="test123",
            language="es",
            auto_generated=True,
            content="Hola, esto es un video de prueba...",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="youtube_transcript_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert transcript.transcript_id == "test123_es"
        assert transcript.video_id == "test123"
        assert transcript.language == "es"
        assert transcript.auto_generated is True
        assert transcript.content == "Hola, esto es un video de prueba..."
        assert transcript.source_timestamp == source_time

    def test_transcript_missing_required_transcript_id(self) -> None:
        """Test Transcript validation fails without transcript_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Transcript(
                video_id="test123",
                language="en",
                content="Test content",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_transcript_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("transcript_id",) for e in errors)

    def test_transcript_missing_required_video_id(self) -> None:
        """Test Transcript validation fails without video_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Transcript(
                transcript_id="test123_en",
                language="en",
                content="Test content",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_transcript_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("video_id",) for e in errors)

    def test_transcript_missing_required_language(self) -> None:
        """Test Transcript validation fails without language."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Transcript(
                transcript_id="test123_en",
                video_id="test123",
                content="Test content",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_transcript_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("language",) for e in errors)

    def test_transcript_missing_required_content(self) -> None:
        """Test Transcript validation fails without content."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Transcript(
                transcript_id="test123_en",
                video_id="test123",
                language="en",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_transcript_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("content",) for e in errors)

    def test_transcript_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Transcript(
                transcript_id="test123_en",
                video_id="test123",
                language="en",
                content="Test content",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_transcript_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_transcript_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Transcript(
                transcript_id="test123_en",
                video_id="test123",
                language="en",
                content="Test content",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="youtube_transcript_api",
                confidence=1.5,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_transcript_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            transcript = Transcript(
                transcript_id="test123_en",
                video_id="test123",
                language="en",
                content="Test content",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="youtube_transcript_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert transcript.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Transcript(
                transcript_id="test123_en",
                video_id="test123",
                language="en",
                content="Test content",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="youtube_transcript_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_transcript_serialization(self) -> None:
        """Test Transcript can be serialized to dict."""
        now = datetime.now(UTC)

        transcript = Transcript(
            transcript_id="test123_en",
            video_id="test123",
            language="en",
            auto_generated=True,
            content="Test transcript content",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="youtube_transcript_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = transcript.model_dump()
        assert data["transcript_id"] == "test123_en"
        assert data["video_id"] == "test123"
        assert data["language"] == "en"
        assert data["auto_generated"] is True
        assert data["content"] == "Test transcript content"

    def test_transcript_deserialization(self) -> None:
        """Test Transcript can be deserialized from dict."""
        now = datetime.now(UTC)

        data = {
            "transcript_id": "test123_en",
            "video_id": "test123",
            "language": "en",
            "auto_generated": True,
            "content": "Test transcript content",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "youtube_transcript_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        transcript = Transcript.model_validate(data)
        assert transcript.transcript_id == "test123_en"
        assert transcript.video_id == "test123"
        assert transcript.language == "en"
        assert transcript.auto_generated is True
        assert transcript.content == "Test transcript content"
