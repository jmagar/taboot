"""Integration test: Ingestion creates Document records in PostgreSQL."""

import pytest

from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.common.db_schema import get_postgres_client
from packages.schemas.models import ExtractionState


@pytest.mark.integration
def test_github_ingestion_creates_document_record() -> None:
    """Test that GitHub ingestion creates Document record in PostgreSQL."""
    # Clear existing records
    conn = get_postgres_client()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM document_content")
        cur.execute("DELETE FROM documents")
    conn.commit()

    # Run GitHub ingestion
    from apps.cli.commands.ingest_github import ingest_github_command

    # This should create Document records in PostgreSQL
    # (Currently it doesn't - test should FAIL)
    ingest_github_command(repo="anthropics/anthropic-sdk-python", limit=1)

    # Query PostgreSQL for created documents
    document_store = PostgresDocumentStore(conn)
    pending_docs = document_store.query_pending()

    # Should have created at least 1 document
    assert len(pending_docs) > 0
    assert all(doc.extraction_state == ExtractionState.PENDING for doc in pending_docs)

    # Cleanup
    with conn.cursor() as cur:
        cur.execute("DELETE FROM document_content")
        cur.execute("DELETE FROM documents")
    conn.commit()
    conn.close()
