"""PostgreSQL adapter implementing DocumentsClient protocol.

Provides async-compatible implementation of DocumentsClient for PostgreSQL queries
using synchronous psycopg2 connection.
"""

import logging
from typing import Any, cast

from psycopg2.extensions import connection

from packages.schemas.models import Document, ExtractionState, SourceType

logger = logging.getLogger(__name__)


class PostgresDocumentsClient:
    """PostgreSQL client implementing DocumentsClient protocol.

    Wraps psycopg2 connection to query documents with filtering and pagination.
    Methods are async-compatible even though underlying operations are synchronous.
    """

    def __init__(self, conn: connection) -> None:
        """Initialize PostgresDocumentsClient with psycopg2 connection.

        Args:
            conn: Active psycopg2 connection with RealDictCursor factory.
        """
        self.conn = conn

    async def fetch_documents(
        self,
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
        query = "SELECT * FROM documents WHERE 1=1"
        params: list[str | int] = []

        if source_type:
            query += " AND source_type = %s"
            params.append(source_type.value)

        if extraction_state:
            query += " AND extraction_state = %s"
            params.append(extraction_state.value)

        query += " ORDER BY ingested_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

        return [Document(**cast(dict[str, Any], row)) for row in rows]

    async def count_documents(
        self,
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
        query = "SELECT COUNT(*) as count FROM documents WHERE 1=1"
        params: list[str | int] = []

        if source_type:
            query += " AND source_type = %s"
            params.append(source_type.value)

        if extraction_state:
            query += " AND extraction_state = %s"
            params.append(extraction_state.value)

        with self.conn.cursor() as cur:
            cur.execute(query, tuple(params))
            row = cur.fetchone()

        return int(cast(dict[str, Any], row)["count"]) if row else 0
