"""ReprocessUseCase - Core orchestration for document reprocessing.

Queues documents for re-extraction based on date filtering.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Protocol

from packages.schemas.models import Document, ExtractionState

logger = logging.getLogger(__name__)


class DocumentStore(Protocol):
    """Protocol for document persistence operations."""

    def query_by_date(self, since_date: datetime) -> list[Document]:
        """Query documents modified since specified date."""
        ...

    def update_document(self, document: Document) -> None:
        """Update document in store."""
        ...


class ReprocessUseCase:
    """Use case for reprocessing documents with updated extractors.

    Queues documents for re-extraction by resetting their extraction_state to PENDING.
    """

    def __init__(self, document_store: DocumentStore) -> None:
        """Initialize ReprocessUseCase with dependencies.

        Args:
            document_store: DocumentStore instance for persistence.
        """
        self.document_store = document_store
        logger.info("Initialized ReprocessUseCase")

    def execute(self, since_date: datetime) -> dict[str, int]:
        """Queue documents for reprocessing.

        Args:
            since_date: Only reprocess documents modified after this date.

        Returns:
            dict with 'documents_queued' count.

        Raises:
            ValueError: If since_date is in the future.
        """
        # Validate date
        if since_date > datetime.now(UTC):
            raise ValueError("since_date cannot be in the future")

        logger.info(f"Reprocessing documents since {since_date}")

        # Query documents
        documents = self.document_store.query_by_date(since_date=since_date)
        logger.info(f"Found {len(documents)} documents to reprocess")

        # Reset extraction state for each document
        for doc in documents:
            doc.extraction_state = ExtractionState.PENDING
            doc.updated_at = datetime.now(UTC)
            self.document_store.update_document(doc)

        return {"documents_queued": len(documents)}
