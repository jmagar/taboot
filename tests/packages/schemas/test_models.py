"""Tests for Pydantic data models.

Tests all entity models defined in packages/schemas/models.py following TDD methodology.
Validates field types, constraints, and validation rules per data-model.md.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.schemas.models import (
    Chunk,
    Document,
    ExtractionState,
    IngestionJob,
    JobState,
    SourceType,
)


class TestDocumentModel:
    """Tests for the Document Pydantic model."""

    def test_document_creation_with_valid_data(self) -> None:
        """Test creating a Document with valid data."""
        doc_id = uuid4()
        now = datetime.now(UTC)

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
                ingested_at=datetime.now(UTC),
                extraction_state=ExtractionState.PENDING,
                updated_at=datetime.now(UTC),
            )

    def test_document_requires_source_url(self) -> None:
        """Test that source_url is required and non-empty."""
        with pytest.raises(ValidationError, match="source_url"):
            Document(
                doc_id=uuid4(),
                source_url="",
                source_type=SourceType.WEB,
                content_hash="a" * 64,
                ingested_at=datetime.now(UTC),
                extraction_state=ExtractionState.PENDING,
                updated_at=datetime.now(UTC),
            )

    def test_document_validates_content_hash_length(self) -> None:
        """Test that content_hash must be exactly 64 characters (SHA-256)."""
        with pytest.raises(ValidationError, match="content_hash"):
            Document(
                doc_id=uuid4(),
                source_url="https://example.com",
                source_type=SourceType.WEB,
                content_hash="too_short",  # Not 64 chars
                ingested_at=datetime.now(UTC),
                extraction_state=ExtractionState.PENDING,
                updated_at=datetime.now(UTC),
            )

    def test_document_validates_source_type_enum(self) -> None:
        """Test that source_type must be a valid SourceType enum."""
        with pytest.raises(ValidationError, match="source_type"):
            Document(
                doc_id=uuid4(),
                source_url="https://example.com",
                source_type="invalid_type",  # Not a valid enum
                content_hash="a" * 64,
                ingested_at=datetime.now(UTC),
                extraction_state=ExtractionState.PENDING,
                updated_at=datetime.now(UTC),
            )

    def test_document_validates_extraction_state_enum(self) -> None:
        """Test that extraction_state must be a valid ExtractionState enum."""
        with pytest.raises(ValidationError, match="extraction_state"):
            Document(
                doc_id=uuid4(),
                source_url="https://example.com",
                source_type=SourceType.WEB,
                content_hash="a" * 64,
                ingested_at=datetime.now(UTC),
                extraction_state="invalid_state",  # Not a valid enum
                updated_at=datetime.now(UTC),
            )

    def test_document_with_optional_fields(self) -> None:
        """Test Document with optional fields (extraction_version, metadata)."""
        doc = Document(
            doc_id=uuid4(),
            source_url="https://example.com",
            source_type=SourceType.WEB,
            content_hash="a" * 64,
            ingested_at=datetime.now(UTC),
            extraction_state=ExtractionState.COMPLETED,
            extraction_version="v1.2.0",
            updated_at=datetime.now(UTC),
            metadata={"page_count": 42, "author": "Test Author"},
        )

        assert doc.extraction_version == "v1.2.0"
        assert doc.metadata == {"page_count": 42, "author": "Test Author"}


class TestChunkModel:
    """Tests for the Chunk Pydantic model."""

    def test_chunk_creation_with_valid_data(self) -> None:
        """Test creating a Chunk with valid data."""
        chunk_id = uuid4()
        doc_id = uuid4()
        now_ts = int(datetime.now(UTC).timestamp())

        chunk = Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            content="This is test chunk content.",
            section="Introduction > Overview",
            position=0,
            token_count=256,
            source_url="https://example.com/docs",
            source_type=SourceType.WEB,
            ingested_at=now_ts,
        )

        assert chunk.chunk_id == chunk_id
        assert chunk.doc_id == doc_id
        assert chunk.content == "This is test chunk content."
        assert chunk.section == "Introduction > Overview"
        assert chunk.position == 0
        assert chunk.token_count == 256
        assert chunk.source_url == "https://example.com/docs"
        assert chunk.source_type == SourceType.WEB
        assert chunk.ingested_at == now_ts
        assert chunk.tags is None

    def test_chunk_requires_chunk_id(self) -> None:
        """Test that chunk_id is required."""
        with pytest.raises(ValidationError, match="chunk_id"):
            Chunk(
                doc_id=uuid4(),
                content="Test content",
                position=0,
                token_count=100,
                source_url="https://example.com",
                source_type=SourceType.WEB,
                ingested_at=int(datetime.now(UTC).timestamp()),
            )

    def test_chunk_validates_content_length(self) -> None:
        """Test that content must be 1-4096 chars."""
        # Test empty content
        with pytest.raises(ValidationError, match="content"):
            Chunk(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                content="",
                position=0,
                token_count=1,
                source_url="https://example.com",
                source_type=SourceType.WEB,
                ingested_at=int(datetime.now(UTC).timestamp()),
            )

        # Test content too long
        with pytest.raises(ValidationError, match="content"):
            Chunk(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                content="x" * 4097,  # Exceeds 4096 chars
                position=0,
                token_count=1,
                source_url="https://example.com",
                source_type=SourceType.WEB,
                ingested_at=int(datetime.now(UTC).timestamp()),
            )

    def test_chunk_validates_token_count_range(self) -> None:
        """Test that token_count must be 1-512."""
        # Test token_count < 1
        with pytest.raises(ValidationError, match="token_count"):
            Chunk(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                content="Test",
                position=0,
                token_count=0,
                source_url="https://example.com",
                source_type=SourceType.WEB,
                ingested_at=int(datetime.now(UTC).timestamp()),
            )

        # Test token_count > 512
        with pytest.raises(ValidationError, match="token_count"):
            Chunk(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                content="Test",
                position=0,
                token_count=513,
                source_url="https://example.com",
                source_type=SourceType.WEB,
                ingested_at=int(datetime.now(UTC).timestamp()),
            )

    def test_chunk_with_optional_tags(self) -> None:
        """Test Chunk with optional tags field."""
        chunk = Chunk(
            chunk_id=uuid4(),
            doc_id=uuid4(),
            content="Test content",
            position=0,
            token_count=50,
            source_url="https://example.com",
            source_type=SourceType.WEB,
            ingested_at=int(datetime.now(UTC).timestamp()),
            tags=["kubernetes", "networking"],
        )

        assert chunk.tags == ["kubernetes", "networking"]


class TestIngestionJobModel:
    """Tests for the IngestionJob Pydantic model."""

    def test_ingestion_job_creation_with_valid_data(self) -> None:
        """Test creating an IngestionJob with valid data."""
        job_id = uuid4()
        now = datetime.now(UTC)

        job = IngestionJob(
            job_id=job_id,
            source_type=SourceType.WEB,
            source_target="https://example.com/docs",
            state=JobState.PENDING,
            created_at=now,
            pages_processed=0,
            chunks_created=0,
        )

        assert job.job_id == job_id
        assert job.source_type == SourceType.WEB
        assert job.source_target == "https://example.com/docs"
        assert job.state == JobState.PENDING
        assert job.created_at == now
        assert job.started_at is None
        assert job.completed_at is None
        assert job.pages_processed == 0
        assert job.chunks_created == 0
        assert job.errors is None

    def test_ingestion_job_requires_job_id(self) -> None:
        """Test that job_id is required."""
        with pytest.raises(ValidationError, match="job_id"):
            IngestionJob(
                source_type=SourceType.WEB,
                source_target="https://example.com",
                state=JobState.PENDING,
                created_at=datetime.now(UTC),
                pages_processed=0,
                chunks_created=0,
            )

    def test_ingestion_job_validates_source_target_length(self) -> None:
        """Test that source_target must be non-empty and ≤2048 chars."""
        # Test empty source_target
        with pytest.raises(ValidationError, match="source_target"):
            IngestionJob(
                job_id=uuid4(),
                source_type=SourceType.WEB,
                source_target="",
                state=JobState.PENDING,
                created_at=datetime.now(UTC),
                pages_processed=0,
                chunks_created=0,
            )

        # Test source_target too long
        with pytest.raises(ValidationError, match="source_target"):
            IngestionJob(
                job_id=uuid4(),
                source_type=SourceType.WEB,
                source_target="x" * 2049,
                state=JobState.PENDING,
                created_at=datetime.now(UTC),
                pages_processed=0,
                chunks_created=0,
            )

    def test_ingestion_job_validates_counts_non_negative(self) -> None:
        """Test that pages_processed and chunks_created must be ≥0."""
        with pytest.raises(ValidationError, match="pages_processed"):
            IngestionJob(
                job_id=uuid4(),
                source_type=SourceType.WEB,
                source_target="https://example.com",
                state=JobState.PENDING,
                created_at=datetime.now(UTC),
                pages_processed=-1,
                chunks_created=0,
            )

        with pytest.raises(ValidationError, match="chunks_created"):
            IngestionJob(
                job_id=uuid4(),
                source_type=SourceType.WEB,
                source_target="https://example.com",
                state=JobState.PENDING,
                created_at=datetime.now(UTC),
                pages_processed=0,
                chunks_created=-1,
            )

    def test_ingestion_job_with_timestamps_and_errors(self) -> None:
        """Test IngestionJob with optional timestamps and errors."""
        now = datetime.now(UTC)
        started = now
        completed = now

        job = IngestionJob(
            job_id=uuid4(),
            source_type=SourceType.WEB,
            source_target="https://example.com",
            state=JobState.COMPLETED,
            created_at=now,
            started_at=started,
            completed_at=completed,
            pages_processed=10,
            chunks_created=50,
            errors=[{"error": "timeout", "url": "https://example.com/page1"}],
        )

        assert job.started_at == started
        assert job.completed_at == completed
        assert job.errors == [{"error": "timeout", "url": "https://example.com/page1"}]
