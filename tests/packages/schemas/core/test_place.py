"""Tests for Place entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Coordinates validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.core.place import Place


class TestPlaceEntity:
    """Test suite for Place entity."""

    def test_place_minimal_valid(self) -> None:
        """Test Place with only required fields."""
        now = datetime.now(UTC)
        place = Place(
            name="Office Building",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert place.name == "Office Building"
        assert place.created_at == now
        assert place.updated_at == now
        assert place.extraction_tier == "A"
        assert place.extraction_method == "tailscale_api"
        assert place.confidence == 1.0
        assert place.extractor_version == "1.0.0"
        assert place.address is None
        assert place.coordinates is None
        assert place.place_type is None
        assert place.source_timestamp is None

    def test_place_full_valid(self) -> None:
        """Test Place with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        place = Place(
            name="San Francisco Office",
            address="123 Market St, San Francisco, CA 94105",
            coordinates="37.7749,-122.4194",
            place_type="office",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="B",
            extraction_method="spacy_ner",
            confidence=0.85,
            extractor_version="1.2.0",
        )

        assert place.name == "San Francisco Office"
        assert place.address == "123 Market St, San Francisco, CA 94105"
        assert place.coordinates == "37.7749,-122.4194"
        assert place.place_type == "office"
        assert place.source_timestamp == source_time
        assert place.extraction_tier == "B"
        assert place.confidence == 0.85

    def test_place_missing_required_name(self) -> None:
        """Test Place validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Place(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_place_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Place(
                name="Test Place",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_place_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Place(
                name="Test Place",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_place_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            place = Place(
                name="Test Place",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert place.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Place(
                name="Test Place",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_place_serialization(self) -> None:
        """Test Place can be serialized to dict."""
        now = datetime.now(UTC)
        place = Place(
            name="Test Place",
            place_type="datacenter",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="regex",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = place.model_dump()
        assert data["name"] == "Test Place"
        assert data["place_type"] == "datacenter"
        assert data["confidence"] == 1.0

    def test_place_deserialization(self) -> None:
        """Test Place can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "name": "Test Place",
            "place_type": "datacenter",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "regex",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        place = Place.model_validate(data)
        assert place.name == "Test Place"
        assert place.place_type == "datacenter"
