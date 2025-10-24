"""IngestWebUseCase - Core orchestration for web document ingestion.

Orchestrates the complete ingestion pipeline:
WebReader → Normalizer → Chunker → Embedder → QdrantWriter

With job state tracking and error handling per data-model.md.
"""

import hashlib
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from llama_index.core import Document as LlamaDocument

from packages.clients.postgres_document_store import PostgresDocumentStore
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
        """
        self.web_reader = web_reader
        self.normalizer = normalizer
        self.chunker = chunker
        self.embedder = embedder
        self.qdrant_writer = qdrant_writer
        self.document_store = document_store
        self.collection_name = collection_name

        logger.info(f"Initialized IngestWebUseCase (collection={collection_name})")

    def execute(
        self, url: str, limit: int | None = None, job_id: "UUID | None" = None
    ) -> IngestionJob:
        """Execute the full ingestion pipeline for a URL.

        Pipeline flow:
        1. Create IngestionJob (state=PENDING)
        2. Transition to RUNNING
        3. WebReader.load_data(url, limit) → docs[]
        4. For each doc:
           a. Normalizer.normalize(doc.text) → markdown
           b. Chunker.chunk_document(markdown_doc) → chunks[]
           c. Embedder.embed_texts([chunk.text]) → embeddings[]
           d. QdrantWriter.upsert_batch(chunks, embeddings)
           e. Update job: pages_processed++, chunks_created+=len(chunks)
        5. Transition to COMPLETED (or FAILED on error)
        6. Return job

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

            # Step 4: Process each document
            all_chunks: list[Chunk] = []
            for doc in docs:
                chunks = self._process_document(doc, job, url)
                all_chunks.extend(chunks)

                # Update pages_processed
                job = job.model_copy(update={"pages_processed": job.pages_processed + 1})

            # Step 4c-4d: Embed and upsert all chunks in batch
            if all_chunks:
                logger.info(f"Embedding {len(all_chunks)} chunks")
                chunk_texts = [chunk.content for chunk in all_chunks]
                embeddings = self.embedder.embed_texts(chunk_texts)

                logger.info(f"Upserting {len(all_chunks)} chunks to Qdrant")
                self.qdrant_writer.upsert_batch(all_chunks, embeddings)

                # Update chunks_created
                job = job.model_copy(
                    update={"chunks_created": job.chunks_created + len(all_chunks)}
                )

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

    def _create_job(self, url: str, job_id: "UUID | None" = None) -> IngestionJob:
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
        # Step 4a: Normalize HTML to Markdown
        markdown = self.normalizer.normalize(doc.text)

        # Create a new Document with normalized text
        normalized_doc = LlamaDocument(
            text=markdown,
            metadata=doc.metadata if doc.metadata else {},
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

            # Calculate token count (rough estimate: split by whitespace)
            token_count = len(chunk_doc.text.split())
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

        return chunks


# Export public API
__all__ = ["IngestWebUseCase"]
