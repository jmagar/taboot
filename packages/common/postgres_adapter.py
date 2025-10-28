"""PostgreSQL adapter implementing the DocumentRepository port."""

import logging
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from psycopg2.extensions import connection
from psycopg2.extras import Json, RealDictCursor

from packages.core.ports.repositories import DocumentRepository
from packages.schemas.models import Document, ExtractionState, SourceType

logger = logging.getLogger(__name__)


class PostgresDocumentsClient(DocumentRepository):
    """PostgreSQL-backed implementation of DocumentRepository.

    Wraps psycopg2 connection to query documents with filtering and pagination.
    Methods are async-compatible even though underlying operations are synchronous.
    """

    def __init__(self, conn: connection) -> None:
        """Initialize PostgresDocumentsClient with psycopg2 connection.

        Args:
            conn: Active psycopg2 connection with RealDictCursor factory.
        """
        self.conn = conn

    async def list_documents(
        self,
        *,
        limit: int,
        offset: int,
        source_type: SourceType | None = None,
        extraction_state: ExtractionState | None = None,
    ) -> list[Document]:
        """Fetch documents with filters and pagination.

        Args:
            limit: Maximum number of documents to return.
            offset: Number of documents to skip.
            source_type: Optional filter by source type.
            extraction_state: Optional filter by extraction state.

        Returns:
            List of Document instances.
        """
        query = "SELECT * FROM rag.documents WHERE 1=1"
        params: list[str | int] = []

        if source_type:
            query += " AND source_type = %s"
            params.append(source_type.value)

        if extraction_state:
            query += " AND extraction_state = %s"
            params.append(extraction_state.value)

        query += " ORDER BY ingested_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

        return [Document(**cast(dict[str, Any], row)) for row in rows]

    async def count_documents(
        self,
        *,
        source_type: SourceType | None = None,
        extraction_state: ExtractionState | None = None,
    ) -> int:
        """Count total documents matching filters.

        Args:
            source_type: Optional filter by source type.
            extraction_state: Optional filter by extraction state.

        Returns:
            Total count of matching documents.
        """
        query = "SELECT COUNT(*) as count FROM rag.documents WHERE 1=1"
        params: list[str | int] = []

        if source_type:
            query += " AND source_type = %s"
            params.append(source_type.value)

        if extraction_state:
            query += " AND extraction_state = %s"
            params.append(extraction_state.value)

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, tuple(params))
            row = cur.fetchone()

        return int(cast(dict[str, Any], row)["count"]) if row else 0

    async def find_by_id(self, doc_id: UUID) -> Document | None:
        """Retrieve a single document by identifier."""

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM rag.documents WHERE doc_id = %s", (str(doc_id),))
            row = cur.fetchone()

        if not row:
            return None

        return Document(**cast(dict[str, Any], row))

    async def find_pending_extraction(self, limit: int | None = None) -> list[Document]:
        """Return documents pending extraction processing."""

        query = """
            SELECT * FROM rag.documents
            WHERE extraction_state = %s
            ORDER BY ingested_at ASC
        """
        params: list[Any] = [ExtractionState.PENDING.value]

        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

        return [Document(**cast(dict[str, Any], row)) for row in rows]

    async def get_document_content(self, doc_id: UUID) -> str:
        """Fetch raw document content for the given document."""

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT content FROM rag.document_content WHERE doc_id = %s",
                (str(doc_id),),
            )
            row = cur.fetchone()

        if not row:
            raise KeyError(f"Document content not found for {doc_id}")

        return str(cast(dict[str, Any], row)["content"])

    async def save(self, document: Document) -> None:
        """Persist updates to a document record."""

        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE rag.documents SET
                    source_url = %s,
                    source_type = %s,
                    content_hash = %s,
                    ingested_at = %s,
                    extraction_state = %s,
                    extraction_version = %s,
                    updated_at = %s,
                    metadata = %s
                WHERE doc_id = %s
                """,
                (
                    document.source_url,
                    document.source_type.value,
                    document.content_hash,
                    document.ingested_at,
                    document.extraction_state.value,
                    document.extraction_version,
                    datetime.now(UTC),
                    Json(document.metadata) if document.metadata else None,
                    str(document.doc_id),
                ),
            )

            if cur.rowcount == 0:
                raise KeyError(f"Document not found for update: {document.doc_id}")

        self.conn.commit()
