"""ListDocumentsUseCase - List and filter documents with pagination.

Supports filtering by:
- source_type: Filter by ingestion source (web, github, etc.)
- extraction_state: Filter by extraction pipeline state

Implements pagination via limit/offset parameters.
"""

import logging
from typing import Protocol

from pydantic import BaseModel, Field

from packages.schemas.models import Document, ExtractionState, SourceType

logger = logging.getLogger(__name__)


# ========== Protocols ==========


class DocumentsClient(Protocol):
    """Protocol for database client supporting document queries.

    Defines the interface that database adapters must implement.
    """

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
        ...

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
        ...


# ========== Models ==========


class DocumentListResponse(BaseModel):
    """Response model for list documents query.

    Attributes:
        documents: List of Document instances.
        total: Total count of documents matching filters (for pagination).
        limit: Page size limit.
        offset: Pagination offset.
    """

    documents: list[Document] = Field(..., description="List of documents")
    total: int = Field(..., ge=0, description="Total documents matching filters")
    limit: int = Field(..., ge=1, description="Page size limit")
    offset: int = Field(..., ge=0, description="Pagination offset")


# ========== Use Case ==========


class ListDocumentsUseCase:
    """Use case for listing documents with filtering and pagination.

    Supports:
    - Pagination via limit/offset
    - Filtering by source_type (web, github, etc.)
    - Filtering by extraction_state (pending, completed, etc.)
    """

    def __init__(self, db_client: DocumentsClient) -> None:
        """Initialize ListDocumentsUseCase with database client.

        Args:
            db_client: Client implementing DocumentsClient protocol.
        """
        self.db_client = db_client
        logger.info("Initialized ListDocumentsUseCase")

    async def execute(
        self,
        limit: int = 10,
        offset: int = 0,
        source_type: SourceType | None = None,
        extraction_state: ExtractionState | None = None,
    ) -> DocumentListResponse:
        """Execute list documents query with filters and pagination.

        Args:
            limit: Maximum documents to return (default: 10).
            offset: Number of documents to skip (default: 0).
            source_type: Optional source type filter.
            extraction_state: Optional extraction state filter.

        Returns:
            DocumentListResponse with documents and pagination metadata.

        Raises:
            ValueError: If limit < 1 or offset < 0.
        """
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")

        logger.info(
            f"Listing documents: limit={limit}, offset={offset}, "
            f"source_type={source_type}, extraction_state={extraction_state}"
        )

        # Fetch documents with filters
        documents = await self.db_client.fetch_documents(
            limit=limit,
            offset=offset,
            source_type=source_type,
            extraction_state=extraction_state,
        )

        # Get total count for pagination
        total = await self.db_client.count_documents(
            source_type=source_type,
            extraction_state=extraction_state,
        )

        logger.info(f"Found {len(documents)} documents (total={total})")

        return DocumentListResponse(
            documents=documents,
            total=total,
            limit=limit,
            offset=offset,
        )


# Export public API
__all__ = [
    "ListDocumentsUseCase",
    "DocumentListResponse",
    "DocumentsClient",
]
