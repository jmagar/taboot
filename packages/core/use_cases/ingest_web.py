"""IngestWebUseCase - Core orchestration for web document ingestion.

Orchestrates the complete ingestion pipeline:
WebReader → Normalizer → Chunker → Embedder → QdrantWriter

With job state tracking and error handling per data-model.md.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from llama_index.core import Document as LlamaDocument

from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.common.token_utils import count_tokens
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.web import WebReader
from packages.schemas.models import (
    Chunk,
    ExtractionState,
    IngestionJob,
    JobState,
    SourceType,
)
from packages.schemas.models import (
    Document as DocumentModel,
)
from packages.vector.writer import QdrantWriter

logger = logging.getLogger(__name__)


class IngestWebUseCase:
    """Use case for ingesting web documents into Qdrant vector store.

    Orchestrates the full ingestion pipeline with job tracking and error handling.
    NO framework dependencies - only imports from adapter packages.

    Attributes:
        web_reader: WebReader adapter for crawling web pages.
        normalizer: Normalizer adapter for HTML-to-Markdown conversion.
        chunker: Chunker adapter for semantic chunking.
        embedder: Embedder adapter for text embedding.
        qdrant_writer: QdrantWriter adapter for vector storage.
        document_store: PostgresDocumentStore for document tracking.
        collection_name: Qdrant collection name for storing chunks.
    """

    def __init__(
        self,
        web_reader: WebReader,
        normalizer: Normalizer,
        chunker: Chunker,
        embedder: Embedder,
        qdrant_writer: QdrantWriter,
        document_store: PostgresDocumentStore,
        collection_name: str,
        flush_threshold: int = 1000,
        *,
        document_ingested_callback: Callable[[DocumentModel, int], None] | None = None,
    ) -> None:
        """Initialize IngestWebUseCase with all dependencies.

        Args:
            web_reader: WebReader instance for crawling.
            normalizer: Normalizer instance for HTML conversion.
            chunker: Chunker instance for semantic chunking.
            embedder: Embedder instance for text embedding.
            qdrant_writer: QdrantWriter instance for vector storage.
            document_store: PostgresDocumentStore for document tracking.
            collection_name: Qdrant collection name.
            flush_threshold: Number of chunks to accumulate before flushing (default: 1000).
            document_ingested_callback: Optional hook invoked after a document is
                persisted; receives the Document model and chunk count.
        """
        self.web_reader = web_reader
        self.normalizer = normalizer
        self.chunker = chunker
        self.embedder = embedder
        self.qdrant_writer = qdrant_writer
        self.document_store = document_store
        self.collection_name = collection_name
        self.flush_threshold = flush_threshold
        self._document_ingested_callback = document_ingested_callback

        logger.info(
            f"Initialized IngestWebUseCase (collection={collection_name}, "
            f"flush_threshold={flush_threshold})"
        )

    async def execute(
        self, url: str, limit: int | None = None, job_id: UUID | None = None
    ) -> IngestionJob:
        """Execute the full ingestion pipeline for a URL asynchronously.

        Pipeline flow:
        1. Create IngestionJob (state=PENDING)
        2. Transition to RUNNING
        3. WebReader.load_data(url, limit) → docs[]
        4. For each doc:
           a. Normalizer.normalize(doc.text) → markdown
           b. Chunker.chunk_document(markdown_doc) → chunks[]
           c. Accumulate chunks with flush threshold
           d. When threshold reached: embed and upsert batch
        5. Final flush for remaining chunks
        6. Transition to COMPLETED (or FAILED on error)
        7. Return job

        Args:
            url: URL to crawl and ingest.
            limit: Optional maximum number of pages to crawl.
            job_id: Optional pre-generated job UUID for async execution.

        Returns:
            IngestionJob: Job with final state and metadata.
        """
        # Step 1: Create job in PENDING state
        job = self._create_job(url, job_id=job_id)
        logger.info(f"Created ingestion job {job.job_id} for {url} (limit={limit})")

        try:
            # Step 2: Transition to RUNNING
            job = self._transition_to_running(job)

            # Step 3: Load documents
            logger.info(f"Loading documents from {url}")
            docs = self.web_reader.load_data(url, limit)
            logger.info(f"Loaded {len(docs)} documents from {url}")

            # Early exit for empty document list
            if not docs:
                logger.info(f"No documents to process for {url}")
                job = self._transition_to_completed(job)
                return job

            # Step 4: Process each document with batched flushing
            all_chunks: list[Chunk] = []
            for doc in docs:
                chunks = self._process_document(doc, job, url)
                all_chunks.extend(chunks)

                # Update pages_processed
                job = job.model_copy(update={"pages_processed": job.pages_processed + 1})

                # Flush when threshold reached
                if len(all_chunks) >= self.flush_threshold:
                    job = await self._flush_chunks(all_chunks, job)
                    all_chunks = []

            # Final flush for remaining chunks
            if all_chunks:
                job = await self._flush_chunks(all_chunks, job)

            # Step 5: Transition to COMPLETED
            job = self._transition_to_completed(job)
            logger.info(
                f"Completed ingestion job {job.job_id}: "
                f"{job.pages_processed} pages, {job.chunks_created} chunks"
            )

            return job

        except ConnectionError as e:
            # Network/service connectivity issues
            logger.error(
                "Connection error during ingestion job %s: %s", job.job_id, e, exc_info=True
            )
            job = self._transition_to_failed(job, f"Connection failed: {str(e)}")
            return job
        except TimeoutError as e:
            # Timeout during crawling or embedding
            logger.error("Timeout during ingestion job %s: %s", job.job_id, e, exc_info=True)
            job = self._transition_to_failed(job, f"Operation timed out: {str(e)}")
            return job
        except (KeyError, ValueError) as e:
            # Data validation or integrity issues
            logger.error(
                "Data validation error during ingestion job %s: %s",
                job.job_id,
                e,
                exc_info=True,
            )
            job = self._transition_to_failed(job, f"Data error: {str(e)}")
            return job
        except Exception as e:
            # Unexpected errors - preserve full context
            logger.exception("Unexpected error during ingestion job %s: %s", job.job_id, e)
            job = self._transition_to_failed(job, f"Unexpected error: {str(e)}")
            return job

    def _create_job(self, url: str, job_id: UUID | None = None) -> IngestionJob:
        """Create a new IngestionJob in PENDING state.

        Args:
            url: Source URL for the job.
            job_id: Optional pre-generated job UUID.

        Returns:
            IngestionJob: Job in PENDING state.
        """
        return IngestionJob(
            job_id=job_id or uuid4(),
            source_type=SourceType.WEB,
            source_target=url,
            state=JobState.PENDING,
            created_at=datetime.now(UTC),
            pages_processed=0,
            chunks_created=0,
        )

    def _transition_to_running(self, job: IngestionJob) -> IngestionJob:
        """Transition job from PENDING to RUNNING.

        Args:
            job: Job in PENDING state.

        Returns:
            IngestionJob: Job in RUNNING state with started_at set.
        """
        return job.model_copy(
            update={
                "state": JobState.RUNNING,
                "started_at": datetime.now(UTC),
            }
        )

    def _transition_to_completed(self, job: IngestionJob) -> IngestionJob:
        """Transition job from RUNNING to COMPLETED.

        Args:
            job: Job in RUNNING state.

        Returns:
            IngestionJob: Job in COMPLETED state with completed_at set.
        """
        return job.model_copy(
            update={
                "state": JobState.COMPLETED,
                "completed_at": datetime.now(UTC),
            }
        )

    async def _flush_chunks(self, chunks: list[Chunk], job: IngestionJob) -> IngestionJob:
        """Flush batch of chunks to vector store asynchronously.

        Args:
            chunks: List of chunks to flush.
            job: Current job for tracking.

        Returns:
            IngestionJob: Updated job with chunks_created incremented.
        """
        logger.info(f"Flushing {len(chunks)} chunks to vector store")

        # Embed chunks
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = await self.embedder.embed_texts_async(chunk_texts)

        # Upsert to Qdrant
        await self.qdrant_writer.upsert_batch_async(chunks, embeddings)

        # Update chunks_created
        return job.model_copy(update={"chunks_created": job.chunks_created + len(chunks)})

    def _transition_to_failed(self, job: IngestionJob, error_msg: str) -> IngestionJob:
        """Transition job from RUNNING to FAILED.

        Args:
            job: Job in RUNNING state.
            error_msg: Error message to record.

        Returns:
            IngestionJob: Job in FAILED state with error recorded.
        """
        error_entry = {
            "error": error_msg,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        errors = job.errors if job.errors else []
        errors.append(error_entry)

        return job.model_copy(
            update={
                "state": JobState.FAILED,
                "completed_at": datetime.now(UTC),
                "errors": errors,
            }
        )

    def _process_document(
        self, doc: LlamaDocument, job: IngestionJob, source_url: str
    ) -> list[Chunk]:
        """Process a single document through the pipeline.

        Args:
            doc: LlamaDocument to process.
            job: Current job for doc_id generation.
            source_url: Original source URL.

        Returns:
            list[Chunk]: Processed chunks with metadata.
        """
        # Step 4a: Normalize only when we don't already have Markdown
        metadata = doc.metadata or {}
        format_hint = metadata.get("content_format") or metadata.get("format")
        content_type = metadata.get("content_type") or metadata.get("contentType")

        is_markdown = False
        if isinstance(format_hint, str) and format_hint.lower() == "markdown":
            is_markdown = True
        if isinstance(content_type, str) and "markdown" in content_type.lower():
            is_markdown = True

        if is_markdown:
            markdown = (doc.text or "").strip()
        else:
            markdown = self.normalizer.normalize(doc.text)

        # Filter metadata to only essential fields needed for chunking/retrieval
        # This prevents LlamaIndex SentenceSplitter from failing when metadata
        # serialization exceeds chunk_size (512 tokens)
        filtered_metadata = {}
        if metadata:
            # Only keep fields that are: (1) needed for retrieval or (2) small
            allowed_keys = {"source_url", "section", "title"}
            filtered_metadata = {
                k: v for k, v in metadata.items()
                if k in allowed_keys and isinstance(v, (str, int, float, bool))
            }

        # Create a new Document with normalized text
        normalized_doc = LlamaDocument(
            text=markdown,
            metadata=filtered_metadata,
        )

        # Step 4b: Chunk the normalized document
        chunk_docs = self.chunker.chunk_document(normalized_doc)

        # Convert LlamaIndex Documents to Chunk models
        chunks: list[Chunk] = []
        doc_id = uuid4()  # One doc_id per document
        ingested_at = int(datetime.now(UTC).timestamp())

        for chunk_doc in chunk_docs:
            # Extract metadata
            chunk_index = chunk_doc.metadata.get("chunk_index", 0)

            # Calculate token count using tiktoken
            token_count = count_tokens(chunk_doc.text)
            token_count = max(1, min(token_count, 512))  # Clamp to [1, 512]

            # Create Chunk model
            chunk = Chunk(
                chunk_id=uuid4(),
                doc_id=doc_id,
                content=chunk_doc.text,
                section=None,  # TODO: Extract section from metadata if available
                position=chunk_index,
                token_count=token_count,
                source_url=source_url,
                source_type=SourceType.WEB,
                ingested_at=ingested_at,
                tags=None,
            )
            chunks.append(chunk)

        # Create Document record in PostgreSQL for extraction pipeline
        content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

        doc_record = DocumentModel(
            doc_id=doc_id,
            source_url=source_url,
            source_type=SourceType.WEB,
            content_hash=content_hash,
            ingested_at=datetime.now(UTC),
            extraction_state=ExtractionState.PENDING,
            extraction_version=None,
            updated_at=datetime.now(UTC),
            metadata={"chunk_count": len(chunks)},
        )

        # Store document and content for extraction
        self.document_store.create(doc_record, markdown)

        if self._document_ingested_callback is not None:
            try:
                self._document_ingested_callback(doc_record, len(chunks))
            except Exception:  # noqa: BLE001 - callback failures should not break ingestion
                logger.exception("Document ingested callback failed", extra={"doc_id": str(doc_id)})

        return chunks


# Export public API
__all__ = ["IngestWebUseCase"]
