"""Tests for Tier C triple validation schemas."""

import pytest
from pydantic import ValidationError
from packages.extraction.tier_c.schema import Triple, ExtractionResult


class TestTriple:
    """Test triple validation schema."""

    def test_valid_triple(self):
        """Test valid triple."""
        triple = Triple(
            subject="api-service",
            predicate="DEPENDS_ON",
            object="postgres",
            confidence=0.95,
        )

        assert triple.subject == "api-service"
        assert triple.predicate == "DEPENDS_ON"
        assert triple.object == "postgres"
        assert triple.confidence == 0.95

    def test_subject_required(self):
        """Test subject is required."""
        with pytest.raises(ValidationError) as exc_info:
            Triple(predicate="DEPENDS_ON", object="postgres", confidence=0.9)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("subject",) for e in errors)

    def test_predicate_required(self):
        """Test predicate is required."""
        with pytest.raises(ValidationError) as exc_info:
            Triple(subject="api", object="db", confidence=0.9)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("predicate",) for e in errors)

    def test_object_required(self):
        """Test object is required."""
        with pytest.raises(ValidationError) as exc_info:
            Triple(subject="api", predicate="DEPENDS_ON", confidence=0.9)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("object",) for e in errors)

    def test_confidence_between_0_and_1(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            Triple(subject="api", predicate="DEPENDS_ON", object="db", confidence=1.5)

        with pytest.raises(ValidationError):
            Triple(subject="api", predicate="DEPENDS_ON", object="db", confidence=-0.1)


class TestExtractionResult:
    """Test extraction result schema."""

    def test_valid_extraction_result(self):
        """Test valid extraction result."""
        result = ExtractionResult(
            triples=[
                Triple(subject="api", predicate="DEPENDS_ON", object="db", confidence=0.9),
                Triple(subject="nginx", predicate="ROUTES_TO", object="api", confidence=0.85),
            ]
        )

        assert len(result.triples) == 2
        assert result.triples[0].subject == "api"

    def test_empty_triples_allowed(self):
        """Test empty triples list is allowed."""
        result = ExtractionResult(triples=[])
        assert result.triples == []

    def test_triples_is_list(self):
        """Test triples must be a list."""
        with pytest.raises(ValidationError):
            ExtractionResult(triples="not a list")
