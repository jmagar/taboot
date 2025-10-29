"""Tests for Organization entity schema.

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

from packages.schemas.core.organization import Organization


class TestOrganizationEntity:
    """Test suite for Organization entity."""

    def test_organization_minimal_valid(self) -> None:
        """Test Organization with only required fields."""
        now = datetime.now(UTC)
        org = Organization(
            name="Acme Corp",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert org.name == "Acme Corp"
        assert org.created_at == now
        assert org.updated_at == now
        assert org.extraction_tier == "A"
        assert org.extraction_method == "github_api"
        assert org.confidence == 1.0
        assert org.extractor_version == "1.0.0"
        assert org.industry is None
        assert org.size is None
        assert org.website is None
        assert org.description is None
        assert org.source_timestamp is None

    def test_organization_full_valid(self) -> None:
        """Test Organization with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        org = Organization(
            name="Tech Corp",
            industry="Software Development",
            size="100-500",
            website="https://techcorp.example.com",
            description="Leading software company",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="B",
            extraction_method="spacy_ner",
            confidence=0.90,
            extractor_version="1.2.0",
        )

        assert org.name == "Tech Corp"
        assert org.industry == "Software Development"
        assert org.size == "100-500"
        assert org.website == "https://techcorp.example.com"
        assert org.description == "Leading software company"
        assert org.source_timestamp == source_time
        assert org.extraction_tier == "B"
        assert org.confidence == 0.90

    def test_organization_missing_required_name(self) -> None:
        """Test Organization validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Organization(
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_organization_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Organization(
                name="Test Org",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_organization_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Organization(
                name="Test Org",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="regex",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_organization_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            org = Organization(
                name="Test Org",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert org.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Organization(
                name="Test Org",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="regex",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_organization_serialization(self) -> None:
        """Test Organization can be serialized to dict."""
        now = datetime.now(UTC)
        org = Organization(
            name="Test Org",
            industry="Technology",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="regex",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = org.model_dump()
        assert data["name"] == "Test Org"
        assert data["industry"] == "Technology"
        assert data["confidence"] == 1.0

    def test_organization_deserialization(self) -> None:
        """Test Organization can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "name": "Test Org",
            "industry": "Technology",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "regex",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        org = Organization.model_validate(data)
        assert org.name == "Test Org"
        assert org.industry == "Technology"
