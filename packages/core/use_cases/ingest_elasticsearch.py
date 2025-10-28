"""IngestElasticsearchUseCase - Core orchestration for Elasticsearch document ingestion.

Orchestrates the complete ingestion pipeline:
ElasticsearchReader → Normalizer → Chunker → Embedder → QdrantWriter

With document tracking and error handling per data-model.md.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid4, uuid5

from llama_index.core import Document as LlamaDocument

from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.common.token_utils import count_tokens
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.elasticsearch import ElasticsearchReader
from packages.schemas.models import (
    Chunk,
    ExtractionState,
    SourceType,
)
from packages.schemas.models import (
    Document as DocumentModel,
)
from packages.vector.writer import QdrantWriter

logger = logging.getLogger(__name__)


class IngestElasticsearchUseCase:
    """Use case for ingesting Elasticsearch documents into Qdrant vector store.

    Orchestrates the full ingestion pipeline with document tracking and error handling.
    NO framework dependencies - only imports from adapter packages.

    Attributes:
        elasticsearch_reader: ElasticsearchReader adapter for querying Elasticsearch.
        normalizer: Normalizer adapter for text cleanup.
        chunker: Chunker adapter for semantic chunking.
        embedder: Embedder adapter for text embedding.
        qdrant_writer: QdrantWriter adapter for vector storage.
        document_store: PostgresDocumentStore for document tracking.
        collection_name: Qdrant collection name for storing chunks.
        index: Elasticsearch index name.
    """

    def __init__(
        self,
        elasticsearch_reader: ElasticsearchReader,
        normalizer: Normalizer,
        chunker: Chunker,
        embedder: Embedder,
        qdrant_writer: QdrantWriter,
        document_store: PostgresDocumentStore,
        collection_name: str,
        index: str,
    ) -> None:
        """Initialize IngestElasticsearchUseCase with all dependencies.

        Args:
            elasticsearch_reader: ElasticsearchReader instance for querying.
            normalizer: Normalizer instance for text cleanup.
            chunker: Chunker instance for semantic chunking.
            embedder: Embedder instance for text embedding.
            qdrant_writer: QdrantWriter instance for vector storage.
            document_store: PostgresDocumentStore for document tracking.
            collection_name: Qdrant collection name.
            index: Elasticsearch index name.
        """
        self.elasticsearch_reader = elasticsearch_reader
        self.normalizer = normalizer
        self.chunker = chunker
        self.embedder = embedder
        self.qdrant_writer = qdrant_writer
        self.document_store = document_store
        self.collection_name = collection_name
        self.index = index

        logger.info(
            f"Initialized IngestElasticsearchUseCase (collection={collection_name}, index={index})"
        )

    def execute(self, query: dict[str, object], limit: int | None = None) -> dict[str, int]:
        """Execute the full ingestion pipeline for Elasticsearch documents.

        Pipeline flow:
        1. ElasticsearchReader.load_data(query, limit) → docs[]
        2. Validate docs is not empty
        3. For each doc:
           a. Normalizer.normalize(doc.text) → normalized_text
           b. Chunker.chunk_document(normalized_doc) → chunks[]
           c. Create deterministic doc_id from content hash
           d. Create Chunk models with metadata
           e. Store Document record in PostgreSQL
        4. Embedder.embed_texts([chunk.content]) → embeddings[]
        5. QdrantWriter.upsert_batch(chunks, embeddings)
        6. Return stats: docs_processed, chunks_created

        Args:
            query: Elasticsearch query DSL dict.
            limit: Optional maximum number of documents to process.

        Returns:
            dict[str, int]: Stats with keys "docs_processed" and "chunks_created".

        Raises:
            ValueError: If no documents match the query.
        """
        # Step 1: Load documents from Elasticsearch
        logger.info(f"Loading documents from Elasticsearch index {self.index}")
        docs = self.elasticsearch_reader.load_data(query=query, limit=limit)
        logger.info(f"Loaded {len(docs)} documents from {self.index}")

        # Step 2: Validate docs is not empty
        if not docs:
            msg = f"No documents found in index {self.index} matching query"
            logger.warning(msg)
            raise ValueError(msg)

        # Step 3: Process each document
        all_chunks: list[Chunk] = []
        now_dt = datetime.now(UTC)

        for doc in docs:
            chunks = self._process_document(doc, now_dt)
            all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {len(docs)} documents")

        # Step 4: Embed all chunks in batch
        logger.info(f"Embedding {len(all_chunks)} chunks")
        chunk_texts = [chunk.content for chunk in all_chunks]
        embeddings = self.embedder.embed_texts(chunk_texts)

        # Step 5: Upsert to Qdrant
        logger.info(f"Upserting {len(all_chunks)} chunks to Qdrant")
        self.qdrant_writer.upsert_batch(all_chunks, embeddings)

        # Step 6: Return stats
        stats = {
            "docs_processed": len(docs),
            "chunks_created": len(all_chunks),
        }
        logger.info(
            f"Completed Elasticsearch ingestion: "
            f"{stats['docs_processed']} docs, {stats['chunks_created']} chunks"
        )

        return stats

    def _process_document(self, doc: LlamaDocument, now_dt: datetime) -> list[Chunk]:
        """Process a single document through the pipeline.

        Args:
            doc: LlamaDocument to process.
            now_dt: Current timestamp for ingested_at.

        Returns:
            list[Chunk]: Processed chunks with metadata.
        """
        # Normalize text
        normalized_text = self.normalizer.normalize(doc.text)

        # Filter metadata to only essential fields needed for chunking/retrieval
        # This prevents LlamaIndex SentenceSplitter from failing when metadata
        # serialization exceeds chunk_size (512 tokens)
        filtered_metadata = {}
        if doc.metadata:
            # Only keep fields that are: (1) needed for retrieval or (2) small
            allowed_keys = {"source_url", "_id", "index", "title"}
            filtered_metadata = {
                k: v for k, v in doc.metadata.items()
                if k in allowed_keys and isinstance(v, (str, int, float, bool))
            }

        normalized_doc = LlamaDocument(
            text=normalized_text,
            metadata=filtered_metadata,
        )

        # Chunk
        chunk_docs = self.chunker.chunk_document(normalized_doc)

        # Create deterministic doc_id from content hash
        content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        doc_id = uuid5(NAMESPACE_URL, content_hash)

        # Extract source URL from metadata or construct one
        source_url = doc.metadata.get("source_url", "")
        if not source_url:
            doc_id_field = doc.metadata.get("_id", "")
            source_url = (
                f"elasticsearch://{self.index}/{doc_id_field}"
                if doc_id_field
                else f"elasticsearch://{self.index}"
            )

        # Convert chunks to Chunk models
        ingested_at = int(now_dt.timestamp())
        chunks: list[Chunk] = []

        for chunk_doc in chunk_docs:
            chunk_index = chunk_doc.metadata.get("chunk_index", 0)
            token_count = count_tokens(chunk_doc.text)
            token_count = max(1, min(token_count, 512))

            chunk = Chunk(
                chunk_id=uuid4(),
                doc_id=doc_id,
                content=chunk_doc.text,
                section=None,
                position=chunk_index,
                token_count=token_count,
                source_url=source_url,
                source_type=SourceType.ELASTICSEARCH,
                ingested_at=ingested_at,
                tags=None,
            )
            chunks.append(chunk)

        # Create Document record for extraction pipeline
        doc_record = DocumentModel(
            doc_id=doc_id,
            source_url=source_url,
            source_type=SourceType.ELASTICSEARCH,
            content_hash=content_hash,
            ingested_at=now_dt,
            extraction_state=ExtractionState.PENDING,
            extraction_version=None,
            updated_at=now_dt,
            metadata={
                "index": self.index,
                "elasticsearch_id": doc.metadata.get("_id"),
                "chunk_count": len(chunk_docs),
            },
        )

        # Store document and content for extraction
        self.document_store.create(doc_record, normalized_text)

        return chunks


# Export public API
__all__ = ["IngestElasticsearchUseCase"]
