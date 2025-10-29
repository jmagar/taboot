"""Tests for Document entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Content hash validation
- Extraction state validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.web.document import Document


class TestDocumentEntity:
    """Test suite for Document entity."""

    def test_document_minimal_valid(self) -> None:
        """Test Document with only required fields."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        doc = Document(
            doc_id="doc_12345",
            source_url="https://example.com/page",
            source_type="web",
            content_hash="abc123def456",
            ingested_at=ingested_at,
            extraction_state="pending",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="firecrawl",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert doc.doc_id == "doc_12345"
        assert doc.source_url == "https://example.com/page"
        assert doc.source_type == "web"
        assert doc.content_hash == "abc123def456"
        assert doc.ingested_at == ingested_at
        assert doc.extraction_state == "pending"
        assert doc.extraction_tier == "A"
        assert doc.confidence == 1.0
        assert doc.source_timestamp is None

    def test_document_full_valid(self) -> None:
        """Test Document with all fields populated."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        doc = Document(
            doc_id="doc_12345",
            source_url="https://example.com/page",
            source_type="elasticsearch",
            content_hash="abc123def456789",
            ingested_at=ingested_at,
            extraction_state="completed",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="B",
            extraction_method="elasticsearch_api",
            confidence=0.95,
            extractor_version="1.2.0",
        )

        assert doc.doc_id == "doc_12345"
        assert doc.source_url == "https://example.com/page"
        assert doc.source_type == "elasticsearch"
        assert doc.content_hash == "abc123def456789"
        assert doc.ingested_at == ingested_at
        assert doc.extraction_state == "completed"
        assert doc.source_timestamp == source_time
        assert doc.extraction_tier == "B"
        assert doc.extraction_method == "elasticsearch_api"
        assert doc.confidence == 0.95
        assert doc.extractor_version == "1.2.0"

    def test_document_missing_required_doc_id(self) -> None:
        """Test Document validation fails without doc_id."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Document(
                source_url="https://example.com/page",
                source_type="web",
                content_hash="abc123",
                ingested_at=ingested_at,
                extraction_state="pending",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("doc_id",) for e in errors)

    def test_document_missing_required_source_url(self) -> None:
        """Test Document validation fails without source_url."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Document(
                doc_id="doc_12345",
                source_type="web",
                content_hash="abc123",
                ingested_at=ingested_at,
                extraction_state="pending",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_url",) for e in errors)

    def test_document_missing_required_source_type(self) -> None:
        """Test Document validation fails without source_type."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Document(
                doc_id="doc_12345",
                source_url="https://example.com/page",
                content_hash="abc123",
                ingested_at=ingested_at,
                extraction_state="pending",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_type",) for e in errors)

    def test_document_missing_required_content_hash(self) -> None:
        """Test Document validation fails without content_hash."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Document(
                doc_id="doc_12345",
                source_url="https://example.com/page",
                source_type="web",
                ingested_at=ingested_at,
                extraction_state="pending",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("content_hash",) for e in errors)

    def test_document_missing_required_ingested_at(self) -> None:
        """Test Document validation fails without ingested_at."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Document(
                doc_id="doc_12345",
                source_url="https://example.com/page",
                source_type="web",
                content_hash="abc123",
                extraction_state="pending",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("ingested_at",) for e in errors)

    def test_document_missing_required_extraction_state(self) -> None:
        """Test Document validation fails without extraction_state."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Document(
                doc_id="doc_12345",
                source_url="https://example.com/page",
                source_type="web",
                content_hash="abc123",
                ingested_at=ingested_at,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_state",) for e in errors)

    def test_document_extraction_state_validation(self) -> None:
        """Test extraction_state must be pending, processing, completed, or failed."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        # Valid extraction states
        for state in ["pending", "processing", "completed", "failed"]:
            doc = Document(
                doc_id="doc_12345",
                source_url="https://example.com/page",
                source_type="web",
                content_hash="abc123",
                ingested_at=ingested_at,
                extraction_state=state,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert doc.extraction_state == state

        # Invalid extraction state
        with pytest.raises(ValidationError) as exc_info:
            Document(
                doc_id="doc_12345",
                source_url="https://example.com/page",
                source_type="web",
                content_hash="abc123",
                ingested_at=ingested_at,
                extraction_state="invalid_state",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_state",) for e in errors)

    def test_document_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Document(
                doc_id="doc_12345",
                source_url="https://example.com/page",
                source_type="web",
                content_hash="abc123",
                ingested_at=ingested_at,
                extraction_state="pending",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_document_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            Document(
                doc_id="doc_12345",
                source_url="https://example.com/page",
                source_type="web",
                content_hash="abc123",
                ingested_at=ingested_at,
                extraction_state="pending",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=1.5,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_document_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            doc = Document(
                doc_id="doc_12345",
                source_url="https://example.com/page",
                source_type="web",
                content_hash="abc123",
                ingested_at=ingested_at,
                extraction_state="pending",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert doc.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Document(
                doc_id="doc_12345",
                source_url="https://example.com/page",
                source_type="web",
                content_hash="abc123",
                ingested_at=ingested_at,
                extraction_state="pending",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_document_serialization(self) -> None:
        """Test Document can be serialized to dict."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        doc = Document(
            doc_id="doc_12345",
            source_url="https://example.com/page",
            source_type="web",
            content_hash="abc123def456",
            ingested_at=ingested_at,
            extraction_state="completed",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="firecrawl",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = doc.model_dump()
        assert data["doc_id"] == "doc_12345"
        assert data["source_url"] == "https://example.com/page"
        assert data["source_type"] == "web"
        assert data["content_hash"] == "abc123def456"
        assert data["extraction_state"] == "completed"

    def test_document_deserialization(self) -> None:
        """Test Document can be deserialized from dict."""
        now = datetime.now(UTC)
        ingested_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        data = {
            "doc_id": "doc_12345",
            "source_url": "https://example.com/page",
            "source_type": "web",
            "content_hash": "abc123def456",
            "ingested_at": ingested_at.isoformat(),
            "extraction_state": "pending",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "firecrawl",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        doc = Document.model_validate(data)
        assert doc.doc_id == "doc_12345"
        assert doc.source_url == "https://example.com/page"
        assert doc.source_type == "web"
        assert doc.content_hash == "abc123def456"
        assert doc.extraction_state == "pending"

    def test_document_validate_extraction_state_direct(self) -> None:
        """Ensure the extraction_state validator raises for invalid input."""
        with pytest.raises(ValueError, match="extraction_state"):
            Document.validate_extraction_state("bogus")

    def test_document_validate_extraction_tier_direct(self) -> None:
        """Ensure the extraction_tier validator raises for invalid input."""
        with pytest.raises(ValueError, match="extraction_tier"):
            Document.validate_extraction_tier("Z")
