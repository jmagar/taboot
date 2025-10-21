"""Tests for Pydantic data models.

Tests all entity models defined in packages/schemas/models.py following TDD methodology.
Validates field types, constraints, and validation rules per data-model.md.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from packages.schemas.models import (
    Document,
    SourceType,
    ExtractionState,
)


class TestDocumentModel:
    """Tests for the Document Pydantic model."""

    def test_document_creation_with_valid_data(self) -> None:
        """Test creating a Document with valid data."""
        doc_id = uuid4()
        now = datetime.now(timezone.utc)

        doc = Document(
            doc_id=doc_id,
            source_url="https://example.com/docs",
            source_type=SourceType.WEB,
            content_hash="a" * 64,  # SHA-256 hex digest
            ingested_at=now,
            extraction_state=ExtractionState.PENDING,
            updated_at=now,
        )

        assert doc.doc_id == doc_id
        assert doc.source_url == "https://example.com/docs"
        assert doc.source_type == SourceType.WEB
        assert doc.content_hash == "a" * 64
        assert doc.ingested_at == now
        assert doc.extraction_state == ExtractionState.PENDING
        assert doc.updated_at == now
        assert doc.extraction_version is None
        assert doc.metadata is None

    def test_document_requires_doc_id(self) -> None:
        """Test that doc_id is required."""
        with pytest.raises(ValidationError, match="doc_id"):
            Document(
                source_url="https://example.com",
                source_type=SourceType.WEB,
                content_hash="a" * 64,
                ingested_at=datetime.now(timezone.utc),
                extraction_state=ExtractionState.PENDING,
                updated_at=datetime.now(timezone.utc),
            )

    def test_document_requires_source_url(self) -> None:
        """Test that source_url is required and non-empty."""
        with pytest.raises(ValidationError, match="source_url"):
            Document(
                doc_id=uuid4(),
                source_url="",
                source_type=SourceType.WEB,
                content_hash="a" * 64,
                ingested_at=datetime.now(timezone.utc),
                extraction_state=ExtractionState.PENDING,
                updated_at=datetime.now(timezone.utc),
            )

    def test_document_validates_content_hash_length(self) -> None:
        """Test that content_hash must be exactly 64 characters (SHA-256)."""
        with pytest.raises(ValidationError, match="content_hash"):
            Document(
                doc_id=uuid4(),
                source_url="https://example.com",
                source_type=SourceType.WEB,
                content_hash="too_short",  # Not 64 chars
                ingested_at=datetime.now(timezone.utc),
                extraction_state=ExtractionState.PENDING,
                updated_at=datetime.now(timezone.utc),
            )

    def test_document_validates_source_type_enum(self) -> None:
        """Test that source_type must be a valid SourceType enum."""
        with pytest.raises(ValidationError, match="source_type"):
            Document(
                doc_id=uuid4(),
                source_url="https://example.com",
                source_type="invalid_type",  # Not a valid enum
                content_hash="a" * 64,
                ingested_at=datetime.now(timezone.utc),
                extraction_state=ExtractionState.PENDING,
                updated_at=datetime.now(timezone.utc),
            )

    def test_document_validates_extraction_state_enum(self) -> None:
        """Test that extraction_state must be a valid ExtractionState enum."""
        with pytest.raises(ValidationError, match="extraction_state"):
            Document(
                doc_id=uuid4(),
                source_url="https://example.com",
                source_type=SourceType.WEB,
                content_hash="a" * 64,
                ingested_at=datetime.now(timezone.utc),
                extraction_state="invalid_state",  # Not a valid enum
                updated_at=datetime.now(timezone.utc),
            )

    def test_document_with_optional_fields(self) -> None:
        """Test Document with optional fields (extraction_version, metadata)."""
        doc = Document(
            doc_id=uuid4(),
            source_url="https://example.com",
            source_type=SourceType.WEB,
            content_hash="a" * 64,
            ingested_at=datetime.now(timezone.utc),
            extraction_state=ExtractionState.COMPLETED,
            extraction_version="v1.2.0",
            updated_at=datetime.now(timezone.utc),
            metadata={"page_count": 42, "author": "Test Author"},
        )

        assert doc.extraction_version == "v1.2.0"
        assert doc.metadata == {"page_count": 42, "author": "Test Author"}
