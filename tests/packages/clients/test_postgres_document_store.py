"""Tests for PostgresDocumentStore implementation."""

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.common.db_schema import get_postgres_client
from packages.schemas.models import Document, ExtractionState, SourceType


@pytest.fixture
def db_connection() -> None:
    """Fixture providing clean database connection."""
    conn = get_postgres_client()
    yield conn

    # Cleanup
    with conn.cursor() as cur:
        cur.execute("DELETE FROM rag.document_content")
        cur.execute("DELETE FROM rag.documents")
    conn.commit()
    conn.close()


@pytest.fixture
def document_store(db_connection) -> None:
    """Fixture providing PostgresDocumentStore instance."""
    return PostgresDocumentStore(db_connection)


def test_create_document_and_content(document_store) -> None:
    """Test creating document record and storing content."""
    doc_id = uuid4()
    content = "Test document content for extraction"
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    document = Document(
        doc_id=doc_id,
        source_url="https://example.com/test",
        source_type=SourceType.WEB,
        content_hash=content_hash,
        ingested_at=datetime.now(UTC),
        extraction_state=ExtractionState.PENDING,
        extraction_version=None,
        updated_at=datetime.now(UTC),
        metadata={"test": "data"},
    )

    # Should not raise
    document_store.create(document, content)

    # Verify document exists in database
    retrieved_content = document_store.get_content(doc_id)
    assert retrieved_content == content


def test_query_pending_returns_pending_documents(document_store) -> None:
    """Test querying documents with extraction_state=PENDING."""
    # Create 3 documents: 2 PENDING, 1 COMPLETED
    pending_docs = []

    for i in range(2):
        doc_id = uuid4()
        content = f"Pending document {i}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        doc = Document(
            doc_id=doc_id,
            source_url=f"https://example.com/pending/{i}",
            source_type=SourceType.WEB,
            content_hash=content_hash,
            ingested_at=datetime.now(UTC),
            extraction_state=ExtractionState.PENDING,
            extraction_version=None,
            updated_at=datetime.now(UTC),
            metadata=None,
        )
        document_store.create(doc, content)
        pending_docs.append(doc)

    # Create completed document (should not be returned)
    completed_id = uuid4()
    completed_content = "Completed document"
    completed_hash = hashlib.sha256(completed_content.encode()).hexdigest()
    completed_doc = Document(
        doc_id=completed_id,
        source_url="https://example.com/completed",
        source_type=SourceType.WEB,
        content_hash=completed_hash,
        ingested_at=datetime.now(UTC),
        extraction_state=ExtractionState.COMPLETED,
        extraction_version="1.0.0",
        updated_at=datetime.now(UTC),
        metadata=None,
    )
    document_store.create(completed_doc, completed_content)

    # Query pending
    results = document_store.query_pending()

    assert len(results) == 2
    assert all(doc.extraction_state == ExtractionState.PENDING for doc in results)


def test_update_document_changes_extraction_state(document_store) -> None:
    """Test updating document extraction state."""
    doc_id = uuid4()
    content = "Test content"
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    # Create in PENDING state
    document = Document(
        doc_id=doc_id,
        source_url="https://example.com/test",
        source_type=SourceType.WEB,
        content_hash=content_hash,
        ingested_at=datetime.now(UTC),
        extraction_state=ExtractionState.PENDING,
        extraction_version=None,
        updated_at=datetime.now(UTC),
        metadata=None,
    )
    document_store.create(document, content)

    # Update to COMPLETED
    updated_doc = document.model_copy(
        update={"extraction_state": ExtractionState.COMPLETED, "extraction_version": "1.0.0"}
    )
    document_store.update_document(updated_doc)

    # Query should return empty (no pending)
    results = document_store.query_pending()
    assert len(results) == 0


def test_get_content_raises_on_missing_document(document_store) -> None:
    """Test that get_content raises KeyError for missing documents."""
    missing_id = uuid4()

    with pytest.raises(KeyError, match=str(missing_id)):
        document_store.get_content(missing_id)


def test_duplicate_content_hash_handles_fk_constraint(document_store, db_connection) -> None:
    """Test that duplicate content_hash doesn't cause FK constraint violation.

    Reproduces bug: When content_hash already exists, ON CONFLICT DO NOTHING
    skips the documents insert, then document_content insert fails with FK error.
    """
    # Create first document with content
    content = "Test content for duplicate detection"
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    doc1 = Document(
        doc_id=uuid4(),
        source_url="https://example.com/original",
        source_type=SourceType.WEB,
        content_hash=content_hash,
        ingested_at=datetime.now(UTC),
        extraction_state=ExtractionState.PENDING,
        extraction_version=None,
        updated_at=datetime.now(UTC),
        metadata={},
    )

    # First insert should succeed
    document_store.create(doc1, content)

    # Create second document with SAME content_hash but different doc_id/URL
    doc2 = Document(
        doc_id=uuid4(),  # Different doc_id
        source_url="https://example.com/duplicate",  # Different URL
        source_type=SourceType.WEB,
        content_hash=content_hash,  # SAME content_hash
        ingested_at=datetime.now(UTC),
        extraction_state=ExtractionState.PENDING,
        extraction_version=None,
        updated_at=datetime.now(UTC),
        metadata={},
    )

    # Second insert should NOT raise FK constraint error
    # Currently FAILS with: IntegrityError: insert or update on table "document_content"
    # violates foreign key constraint "document_content_doc_id_fkey"
    document_store.create(doc2, content)  # This should handle gracefully

    # Verify: Only first document exists (deduplication worked)
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM rag.documents WHERE content_hash = %s", (content_hash,))
        result = cur.fetchone()
        count = result['count'] if isinstance(result, dict) else result[0]
        assert count == 1, f"Should have exactly one document with this content_hash, got count={count}"

        cur.execute("SELECT doc_id FROM rag.documents WHERE content_hash = %s", (content_hash,))
        result2 = cur.fetchone()
        stored_doc_id = result2['doc_id'] if isinstance(result2, dict) else result2[0]
        assert stored_doc_id == str(doc1.doc_id), "Should keep first document's doc_id"
