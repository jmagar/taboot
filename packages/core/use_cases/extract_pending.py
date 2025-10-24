"""ExtractPendingUseCase - Core orchestration for pending document extraction.

Orchestrates the extraction of pending documents:
DocumentStore → ExtractionOrchestratorPort → DocumentStore (update state)

With per-document error handling and batch summary statistics.
"""

import logging
from typing import Protocol
from uuid import UUID

from packages.schemas.models import Document, ExtractionJob, ExtractionState

logger = logging.getLogger(__name__)


class ExtractionOrchestratorPort(Protocol):
    """Port for extraction orchestrator (dependency inversion)."""

    async def process_document(self, doc_id: UUID, content: str) -> ExtractionJob:
        """Process a single document through extraction pipeline."""
        ...


class DocumentStore(Protocol):
    """Protocol for document persistence operations.

    Defines the interface for querying and updating documents.
    Implementations can use PostgreSQL, in-memory stores, or other backends.
    """

    def query_pending(self, limit: int | None = None) -> list[Document]:
        """Query documents in PENDING extraction state.

        Args:
            limit: Optional maximum number of documents to return.

        Returns:
            list[Document]: List of documents with extraction_state == PENDING.
        """
        ...

    def get_content(self, doc_id: UUID) -> str:
        """Get document text content by doc_id.

        Args:
            doc_id: Document UUID.

        Returns:
            str: Document text content.
        """
        ...

    def update_document(self, document: Document) -> None:
        """Update document in store.

        Args:
            document: Document instance with updated fields.
        """
        ...


class ExtractPendingUseCase:
    """Use case for extracting pending documents via multi-tier extraction.

    Orchestrates the extraction pipeline:
    1. Query pending documents from store
    2. For each document, call ExtractionOrchestratorPort.process_document()
    3. Update document extraction_state based on ExtractionJob result
    4. Return summary statistics

    NO framework dependencies - only imports from packages.schemas and packages.common.

    Attributes:
        orchestrator: ExtractionOrchestratorPort for multi-tier extraction.
        document_store: DocumentStore for persistence operations.
    """

    def __init__(
        self,
        orchestrator: ExtractionOrchestratorPort,
        document_store: DocumentStore,
    ) -> None:
        """Initialize ExtractPendingUseCase with dependencies.

        Args:
            orchestrator: ExtractionOrchestratorPort instance for extraction.
            document_store: DocumentStore instance for persistence.
        """
        self.orchestrator = orchestrator
        self.document_store = document_store

        logger.info("Initialized ExtractPendingUseCase")

    async def execute(self, limit: int | None = None) -> dict[str, int]:
        """Execute extraction pipeline for pending documents.

        Pipeline flow:
        1. Query documents where extraction_state == PENDING
        2. For each document:
           a. Get document content
           b. Call orchestrator.process_document(doc.doc_id, content)
           c. Update doc.extraction_state from job.state
           d. Update doc.extraction_version from job metadata
           e. Persist changes to store
        3. Aggregate results and return summary

        Args:
            limit: Optional maximum number of documents to process.

        Returns:
            dict[str, int]: Summary statistics with keys:
                - processed: Total documents attempted
                - succeeded: Documents successfully extracted
                - failed: Documents that failed extraction
        """
        # Step 1: Query pending documents
        logger.info("Querying pending documents (limit=%s)", limit)
        pending_docs = self.document_store.query_pending(limit=limit)
        logger.info("Found %s pending documents", len(pending_docs))

        # Early exit for empty queue
        if not pending_docs:
            logger.info("No pending documents to process")
            return {"processed": 0, "succeeded": 0, "failed": 0}

        # Initialize counters
        processed = 0
        succeeded = 0
        failed = 0

        # Step 2: Process each document
        for doc in pending_docs:
            try:
                # Log progress every 10 documents
                if processed > 0 and processed % 10 == 0:
                    logger.info(
                        "Progress: %s/%s documents processed (succeeded=%s, failed=%s)",
                        processed,
                        len(pending_docs),
                        succeeded,
                        failed,
                    )

                # Step 2a: Get document content
                content = self.document_store.get_content(doc.doc_id)

                # Step 2b: Call orchestrator
                logger.debug(f"Processing document {doc.doc_id}")
                job: ExtractionJob = await self.orchestrator.process_document(doc.doc_id, content)

                # Step 2c-2d: Update document state from job
                # Note: extraction_version would come from orchestrator metadata
                # For now, we only update the state
                updated_doc = doc.model_copy(
                    update={
                        "extraction_state": job.state,
                    }
                )

                # Step 2e: Persist changes
                self.document_store.update_document(updated_doc)

                # Update counters based on job result
                processed += 1
                if job.state == ExtractionState.COMPLETED:
                    succeeded += 1
                    logger.debug(
                        f"Document {doc.doc_id} extracted successfully: "
                        f"tier_a={job.tier_a_triples}, tier_b={job.tier_b_windows}, "
                        f"tier_c={job.tier_c_triples}"
                    )
                else:
                    failed += 1
                    logger.warning(f"Document {doc.doc_id} extraction failed: state={job.state}")

            except (ConnectionError, TimeoutError) as e:
                # Service connectivity issues - mark as failed and continue
                processed += 1
                failed += 1
                logger.error(
                    "Service connection error processing document %s: %s",
                    doc.doc_id,
                    e,
                    exc_info=True,
                )
            except (KeyError, ValueError) as e:
                # Data validation issues - mark as failed and continue
                processed += 1
                failed += 1
                logger.error(
                    "Data validation error processing document %s: %s", doc.doc_id, e, exc_info=True
                )
            except Exception as e:
                # Unexpected errors - log with full context, mark as failed, continue
                processed += 1
                failed += 1
                logger.exception("Unexpected error processing document %s: %s", doc.doc_id, e)

        # Step 3: Log final summary
        logger.info(
            f"Extraction complete: processed={processed}, succeeded={succeeded}, failed={failed}"
        )

        return {
            "processed": processed,
            "succeeded": succeeded,
            "failed": failed,
        }


# Export public API
__all__ = ["ExtractPendingUseCase", "DocumentStore", "ExtractionOrchestratorPort"]
