"""PostgreSQL implementation of DocumentStore protocol.

Implements document persistence and querying for extraction pipeline.
"""

from datetime import UTC, datetime
from uuid import UUID

from psycopg2.extensions import connection
from psycopg2.extras import Json, RealDictCursor

from packages.common.logging import get_logger
from packages.schemas.models import Document, ExtractionState, SourceType

logger = get_logger(__name__)


class PostgresDocumentStore:
    """PostgreSQL implementation of DocumentStore protocol.

    Implements the DocumentStore protocol from ExtractPendingUseCase.
    Handles Document CRUD operations and content storage.
    """

    def __init__(self, conn: connection) -> None:
        """Initialize with PostgreSQL connection.

        Args:
            conn: psycopg2 connection object.
        """
        self.conn = conn
        logger.info("Initialized PostgresDocumentStore")

    def create(self, document: Document, content: str) -> None:
        """Create document record and store content.

        Args:
            document: Document model to persist.
            content: Full document text content.
        """
        with self.conn.cursor() as cur:
            # Insert document metadata
            cur.execute(
                """
                INSERT INTO rag.documents (
                    doc_id, source_url, source_type, content_hash,
                    ingested_at, extraction_state, extraction_version,
                    updated_at, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (content_hash) DO NOTHING
            """,
                (
                    str(document.doc_id),
                    document.source_url,
                    document.source_type.value,
                    document.content_hash,
                    document.ingested_at,
                    document.extraction_state.value,
                    document.extraction_version,
                    document.updated_at,
                    Json(document.metadata) if document.metadata else None,
                ),
            )

            # Store full content in separate table
            cur.execute(
                """
                INSERT INTO rag.document_content (doc_id, content, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (doc_id) DO NOTHING
            """,
                (str(document.doc_id), content, datetime.now(UTC)),
            )

        self.conn.commit()
        logger.debug(f"Created document {document.doc_id}")

    def query_pending(self, limit: int | None = None) -> list[Document]:
        """Query documents with extraction_state=PENDING.

        Args:
            limit: Optional max number of documents to return.

        Returns:
            list[Document]: Documents awaiting extraction.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT * FROM rag.documents
                WHERE extraction_state = 'pending'
                ORDER BY ingested_at ASC
            """
            params: list[object] = []
            if limit is not None:
                query += " LIMIT %s"
                params.append(limit)

            cur.execute(query, params)
            rows = cur.fetchall()

        documents = []
        for row in rows:
            doc = Document(
                doc_id=UUID(row["doc_id"]),
                source_url=row["source_url"],
                source_type=SourceType(row["source_type"]),
                content_hash=row["content_hash"],
                ingested_at=row["ingested_at"],
                extraction_state=ExtractionState(row["extraction_state"]),
                extraction_version=row["extraction_version"],
                updated_at=row["updated_at"],
                metadata=row["metadata"],
            )
            documents.append(doc)

        logger.info(f"Found {len(documents)} pending documents")
        return documents

    def query_by_date(self, since_date: datetime) -> list[Document]:
        """Query documents modified since specified date.

        Args:
            since_date: Return documents updated after this datetime.

        Returns:
            list[Document]: Documents modified since the specified date.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM rag.documents
                WHERE updated_at >= %s
                ORDER BY updated_at DESC
            """,
                (since_date,),
            )
            rows = cur.fetchall()

        documents = []
        for row in rows:
            doc = Document(
                doc_id=UUID(row["doc_id"]),
                source_url=row["source_url"],
                source_type=SourceType(row["source_type"]),
                content_hash=row["content_hash"],
                ingested_at=row["ingested_at"],
                extraction_state=ExtractionState(row["extraction_state"]),
                extraction_version=row["extraction_version"],
                updated_at=row["updated_at"],
                metadata=row["metadata"],
            )
            documents.append(doc)

        logger.info(f"Found {len(documents)} documents since {since_date}")
        return documents

    def get_content(self, doc_id: UUID) -> str:
        """Get full document content by doc_id.

        Args:
            doc_id: Document UUID.

        Returns:
            str: Full document text.

        Raises:
            KeyError: If document not found.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT content FROM rag.document_content WHERE doc_id = %s", (str(doc_id),))
            row = cur.fetchone()

        if row is None:
            raise KeyError(f"Document content not found for {doc_id}")

        content: str = row["content"]
        return content

    def update_document(self, document: Document) -> None:
        """Update document metadata.

        Args:
            document: Document with updated fields.

        Raises:
            KeyError: If document not found.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE rag.documents SET
                    extraction_state = %s,
                    extraction_version = %s,
                    updated_at = %s,
                    metadata = %s
                WHERE doc_id = %s
            """,
                (
                    document.extraction_state.value,
                    document.extraction_version,
                    datetime.now(UTC),
                    Json(document.metadata) if document.metadata else None,
                    str(document.doc_id),
                ),
            )
            if cur.rowcount == 0:
                self.conn.rollback()
                raise KeyError(f"Document not found for update: {document.doc_id}")
        self.conn.commit()
        logger.debug(f"Updated document {document.doc_id}")

    def query_documents(
        self,
        limit: int = 10,
        offset: int = 0,
        source_type: SourceType | None = None,
        extraction_state: ExtractionState | None = None,
    ) -> list[Document]:
        """Query documents with filters and pagination.

        Args:
            limit: Maximum documents to return.
            offset: Number of documents to skip.
            source_type: Optional source type filter.
            extraction_state: Optional extraction state filter.

        Returns:
            list[Document]: Matching documents.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Build query with optional filters
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

            cur.execute(query, params)
            rows = cur.fetchall()

        documents = []
        for row in rows:
            doc = Document(
                doc_id=UUID(row["doc_id"]),
                source_url=row["source_url"],
                source_type=SourceType(row["source_type"]),
                content_hash=row["content_hash"],
                ingested_at=row["ingested_at"],
                extraction_state=ExtractionState(row["extraction_state"]),
                extraction_version=row["extraction_version"],
                updated_at=row["updated_at"],
                metadata=row["metadata"],
            )
            documents.append(doc)

        logger.debug(f"Queried {len(documents)} documents (limit={limit}, offset={offset})")
        return documents

    def count_documents(
        self,
        source_type: SourceType | None = None,
        extraction_state: ExtractionState | None = None,
    ) -> int:
        """Count documents with optional filters.

        Args:
            source_type: Optional source type filter.
            extraction_state: Optional extraction state filter.

        Returns:
            int: Total count of matching documents.
        """
        with self.conn.cursor() as cur:
            query = "SELECT COUNT(*) FROM rag.documents WHERE 1=1"
            params: list[str] = []

            if source_type:
                query += " AND source_type = %s"
                params.append(source_type.value)

            if extraction_state:
                query += " AND extraction_state = %s"
                params.append(extraction_state.value)

            cur.execute(query, params)
            result = cur.fetchone()

        count = result[0] if result else 0
        logger.debug(f"Counted {count} documents")
        return count

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
        logger.debug("PostgreSQL connection closed")


__all__ = ["PostgresDocumentStore"]
