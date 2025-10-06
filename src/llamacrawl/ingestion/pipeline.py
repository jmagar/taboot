"""Core ingestion pipeline orchestrating document processing and storage.

This module provides the IngestionPipeline class that coordinates the complete
ingestion workflow using LlamaIndex components:
1. Deduplication check (DocumentDeduplicator)
2. Document chunking and embedding (LlamaIndex IngestionPipeline)
3. Entity/relationship extraction (PropertyGraphIndex)
4. Storage in Qdrant, Neo4j, and Redis
5. Progress tracking and error handling with DLQ

The pipeline uses distributed locks to prevent concurrent ingestion of the same source
and implements per-document error handling to ensure resilience.
"""

import asyncio
import time
import traceback
import warnings
from collections.abc import Sequence
from typing import Any

import redis.asyncio as aioredis

from llama_index.core import PropertyGraphIndex, Settings
from llama_index.core.indices.property_graph import (
    SimpleLLMPathExtractor,
    ImplicitPathExtractor,
    SchemaLLMPathExtractor,
)
from llama_index.core.ingestion import IngestionCache
from llama_index.core.ingestion import IngestionPipeline as LlamaIngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode
from llama_index.core.schema import Document as LlamaDocument
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.llms.ollama import Ollama
from llama_index.storage.docstore.redis import RedisDocumentStore  # type: ignore[import-not-found]
from llama_index.storage.kvstore.redis import RedisKVStore  # type: ignore[import-not-found]
from llama_index.vector_stores.qdrant import QdrantVectorStore

from llamacrawl.config import Config
from llamacrawl.embeddings.tei import TEIEmbedding
from llamacrawl.ingestion.deduplication import DocumentDeduplicator
from llamacrawl.models.document import Document
from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.storage.qdrant import QdrantClient
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)


class IngestionSummary:
    """Summary statistics for an ingestion run.

    Attributes:
        total: Total documents provided for ingestion
        processed: Documents successfully processed
        deduplicated: Documents skipped due to unchanged content
        failed: Documents that failed processing
        duration_seconds: Total ingestion duration
    """

    def __init__(
        self,
        total: int = 0,
        processed: int = 0,
        deduplicated: int = 0,
        failed: int = 0,
        duration_seconds: float = 0.0,
    ):
        """Initialize ingestion summary.

        Args:
            total: Total documents provided
            processed: Documents successfully processed
            deduplicated: Documents skipped (unchanged)
            failed: Documents that failed
            duration_seconds: Total duration in seconds
        """
        self.total = total
        self.processed = processed
        self.deduplicated = deduplicated
        self.failed = failed
        self.duration_seconds = duration_seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary.

        Returns:
            Dictionary with all summary fields
        """
        return {
            "total": self.total,
            "processed": self.processed,
            "deduplicated": self.deduplicated,
            "failed": self.failed,
            "duration_seconds": round(self.duration_seconds, 2),
            "success_rate": round(self.processed / self.total * 100, 1) if self.total > 0 else 0.0,
        }


class IngestionPipeline:
    """Core ingestion pipeline orchestrating document processing and storage.

    This class coordinates the complete RAG ingestion workflow:
    1. Deduplication via content hashing
    2. Document chunking and embedding via LlamaIndex
    3. Vector storage in Qdrant
    4. Entity/relationship extraction into Neo4j
    5. Cursor updates and error tracking in Redis

    Uses distributed locks to prevent concurrent ingestion of the same source.
    Implements per-document error handling with Dead Letter Queue.

    Attributes:
        config: Configuration object
        redis_client: Redis client for state/cache/locks
        qdrant_client: Qdrant client for vector storage
        neo4j_client: Neo4j client for graph storage
        embed_model: TEI embedding model
        deduplicator: Document deduplicator
        llama_pipeline: LlamaIndex ingestion pipeline
        log_progress_interval: Log progress every N documents
    """

    def __init__(
        self,
        config: Config,
        redis_client: RedisClient,
        qdrant_client: QdrantClient,
        neo4j_client: Neo4jClient,
        embed_model: TEIEmbedding,
        log_progress_interval: int = 10,
    ):
        """Initialize ingestion pipeline with storage clients and embedding model.

        Args:
            config: Configuration object with ingestion settings
            redis_client: Redis client for state management
            qdrant_client: Qdrant client for vector storage
            neo4j_client: Neo4j client for graph storage
            embed_model: TEI embedding model for generating embeddings
            log_progress_interval: Log progress every N documents (default: 10)
        """
        self.config = config
        self.redis_client = redis_client
        self.qdrant_client = qdrant_client
        self.neo4j_client = neo4j_client
        self.embed_model = embed_model
        self.log_progress_interval = log_progress_interval

        # Initialize deduplicator
        self.deduplicator = DocumentDeduplicator(
            redis_client=redis_client,
            remove_punctuation=False,  # Keep punctuation for better deduplication accuracy
        )

        # Initialize Settings.llm for entity extraction
        Settings.llm = Ollama(
            model=config.graph.extraction_model,
            base_url=config.ollama_url,
        )

        # Initialize Settings.embed_model for PropertyGraphIndex
        Settings.embed_model = self.embed_model

        logger.info(
            "Initializing ingestion pipeline",
            extra={
                "chunk_size": config.ingestion.chunk_size,
                "chunk_overlap": config.ingestion.chunk_overlap,
                "batch_size": config.ingestion.batch_size,
            },
        )

        # Initialize LlamaIndex ingestion pipeline with caching
        self._initialize_llama_pipeline()

        logger.info("Ingestion pipeline initialized successfully")

    def _initialize_llama_pipeline(self) -> None:
        """Initialize LlamaIndex IngestionPipeline with transformations and storage.

        Sets up:
        - SentenceSplitter for chunking
        - TEIEmbedding for embeddings
        - RedisDocumentStore for caching (enables incremental updates)
        - QdrantVectorStore for vector storage
        """
        # Get Redis connection parameters
        redis_kwargs = self.redis_client.client.connection_pool.connection_kwargs
        redis_host = redis_kwargs.get("host", "localhost")
        redis_port = redis_kwargs.get("port", 6379)

        # Create async Redis client for LlamaIndex

        # Create Redis document store for caching
        docstore = RedisDocumentStore.from_host_and_port(
            host=redis_host,
            port=redis_port,
            namespace="llamacrawl_docstore",
        )

        # Create ingestion cache using RedisKVStore (BaseKVStore implementation)
        # Reuse existing Redis client connection with namespace support via **kwargs
        cache = IngestionCache(
            cache=RedisKVStore(
                redis_client=self.redis_client.client,
                namespace="llamacrawl_cache",
            ),
        )

        # Create Qdrant vector store for LlamaIndex
        vector_store = QdrantVectorStore(
            client=self.qdrant_client.client,
            collection_name=self.qdrant_client.collection_name,
        )

        # Create transformation pipeline
        transformations = [
            # Chunking transformation
            SentenceSplitter(
                chunk_size=self.config.ingestion.chunk_size,
                chunk_overlap=self.config.ingestion.chunk_overlap,
                separator=" ",
            ),
            # Embedding transformation
            self.embed_model,
        ]

        # Initialize LlamaIndex IngestionPipeline
        self.llama_pipeline = LlamaIngestionPipeline(
            transformations=transformations,
            docstore=docstore,
            vector_store=vector_store,
            cache=cache,
        )

        logger.debug(
            "LlamaIndex IngestionPipeline initialized",
            extra={
                "transformations": len(transformations),
                "docstore": "Redis",
                "vector_store": "Qdrant",
                "cache_enabled": True,
            },
        )

    def ingest_documents(
        self,
        source: str,
        documents: list[Document],
        update_cursor: str | None = None,
    ) -> IngestionSummary:
        """Main ingestion flow for processing documents.

        Workflow:
        1. Deduplication check via content hashes
        2. Convert to LlamaIndex Documents
        3. Run LlamaIndex pipeline (chunking + embedding + vector store)
        4. Extract entities/relationships into Neo4j
        5. Update Redis cursor
        6. Return summary statistics

        Implements per-document error handling: failures are logged to DLQ
        and processing continues for remaining documents.

        Args:
            source: Source identifier (e.g., 'gmail', 'github')
            documents: List of documents to ingest
            update_cursor: Optional cursor value to store after successful ingestion

        Returns:
            IngestionSummary with statistics (total, processed, deduplicated, failed)

        Example:
            >>> pipeline = IngestionPipeline(config, redis, qdrant, neo4j, embed_model)
            >>> docs = reader.load_data()
            >>> summary = pipeline.ingest_documents('github', docs, cursor='2024-09-30T10:00:00Z')
            >>> print(f"Processed {summary.processed}/{summary.total} documents")
        """
        start_time = time.time()
        summary = IngestionSummary(total=len(documents))

        if not documents:
            logger.warning("No documents to ingest", extra={"source": source})
            return summary

        logger.info(
            "Starting document ingestion",
            extra={
                "source": source,
                "document_count": len(documents),
            },
        )

        # Step 1: Deduplication check
        logger.info("Running deduplication check", extra={"source": source})
        new_documents, duplicate_documents = self.deduplicator.get_deduplicated_documents(
            source, documents
        )

        summary.deduplicated = len(duplicate_documents)

        if not new_documents:
            logger.info(
                "All documents are duplicates, skipping ingestion",
                extra={
                    "source": source,
                    "total": summary.total,
                    "duplicates": summary.deduplicated,
                },
            )
            summary.duration_seconds = time.time() - start_time
            return summary

        logger.info(
            f"Processing {len(new_documents)} new/modified documents",
            extra={
                "source": source,
                "new_documents": len(new_documents),
                "duplicates": summary.deduplicated,
            },
        )

        # Step 2: Process documents with error handling
        processed_documents: list[Document] = []
        failed_count = 0

        for idx, doc in enumerate(new_documents):
            try:
                # Log progress periodically
                if (idx + 1) % self.log_progress_interval == 0:
                    logger.info(
                        f"Processing document {idx + 1}/{len(new_documents)}",
                        extra={
                            "source": source,
                            "doc_id": doc.doc_id,
                            "progress": f"{idx + 1}/{len(new_documents)}",
                        },
                    )

                # Step 3: Convert to LlamaIndex Document
                llama_doc = self._convert_to_llama_document(doc)

                # Step 4: Run LlamaIndex pipeline (chunking + embedding + vector store)
                nodes = self.llama_pipeline.run(documents=[llama_doc], show_progress=False)

                logger.debug(
                    "Document processed through LlamaIndex pipeline",
                    extra={
                        "source": source,
                        "doc_id": doc.doc_id,
                        "chunks_created": len(nodes),
                    },
                )

                # Step 5: Extract entities and relationships into Neo4j
                if self.config.graph.auto_extract_entities:
                    self._extract_entities_to_neo4j(source, doc, llama_doc, nodes)

                # Mark document as successfully processed
                processed_documents.append(doc)

            except Exception as e:
                # Log error and push to DLQ
                error_msg = f"{type(e).__name__}: {str(e)}"
                logger.error(
                    f"Failed to process document: {error_msg}",
                    extra={
                        "source": source,
                        "doc_id": doc.doc_id,
                        "error": error_msg,
                        "traceback": traceback.format_exc(),
                    },
                )

                # Push to Dead Letter Queue
                self.redis_client.push_to_dlq(
                    source=source,
                    doc_data={
                        "doc_id": doc.doc_id,
                        "title": doc.title,
                        "content_hash": doc.content_hash,
                        "source_url": doc.metadata.source_url,
                    },
                    error=error_msg,
                )

                failed_count += 1

                # Continue processing remaining documents
                continue

        # Step 6: Update content hashes in Redis for successfully processed documents
        if processed_documents:
            self.deduplicator.update_hashes_batch(source, processed_documents)

        # Step 7: Update cursor if provided
        if update_cursor is not None and processed_documents:
            self.redis_client.set_cursor(source, update_cursor)
            logger.info(
                "Updated cursor after successful ingestion",
                extra={"source": source, "cursor": update_cursor},
            )

        # Calculate summary
        summary.processed = len(processed_documents)
        summary.failed = failed_count
        summary.duration_seconds = time.time() - start_time

        logger.info(
            "Ingestion completed",
            extra={
                "source": source,
                **summary.to_dict(),
            },
        )

        return summary

    def ingest_with_lock(
        self,
        source: str,
        documents: list[Document],
        update_cursor: str | None = None,
        lock_ttl: int = 3600,
    ) -> IngestionSummary:
        """Wrap ingestion with distributed lock to prevent concurrent processing.

        Acquires a distributed lock before ingestion to ensure only one process
        ingests from the same source at a time. Lock auto-expires via TTL.

        Args:
            source: Source identifier
            documents: List of documents to ingest
            update_cursor: Optional cursor value to store after ingestion
            lock_ttl: Lock time-to-live in seconds (default: 1 hour)

        Returns:
            IngestionSummary with statistics

        Raises:
            RuntimeError: If lock cannot be acquired (another process is ingesting)

        Example:
            >>> pipeline = IngestionPipeline(config, redis, qdrant, neo4j, embed_model)
            >>> try:
            ...     summary = pipeline.ingest_with_lock('gmail', docs)
            ... except RuntimeError as e:
            ...     print(f"Ingestion already in progress: {e}")
        """
        lock_key = f"ingest:{source}"

        logger.info(
            "Attempting to acquire ingestion lock",
            extra={"source": source, "lock_key": lock_key, "lock_ttl": lock_ttl},
        )

        # Use context manager for automatic lock release
        with self.redis_client.with_lock(lock_key, ttl=lock_ttl, blocking_timeout=0) as lock:
            if not lock:
                # Lock not acquired - another process is ingesting
                error_msg = f"Another process is already ingesting from {source}"
                logger.warning(
                    "Failed to acquire ingestion lock",
                    extra={"source": source, "lock_key": lock_key},
                )
                raise RuntimeError(error_msg)

            logger.info(
                "Ingestion lock acquired",
                extra={"source": source, "lock_value": lock},
            )

            # Perform ingestion with lock held
            try:
                summary = self.ingest_documents(source, documents, update_cursor)
                return summary

            finally:
                # Lock is automatically released by context manager
                logger.info(
                    "Ingestion lock released",
                    extra={"source": source},
                )

    def _convert_to_llama_document(self, doc: Document) -> LlamaDocument:
        """Convert custom Document model to LlamaIndex Document.

        Optimizes metadata to prevent it from inflating chunk sizes:
        - Excludes all metadata from embeddings (excluded_embed_metadata_keys)
        - Truncates long URLs to 200 chars
        - Preserves full metadata for retrieval/display

        Args:
            doc: Custom Document instance

        Returns:
            LlamaIndex Document with optimized metadata
        """
        # Truncate long URLs to prevent metadata bloat
        source_url = doc.metadata.source_url
        if len(source_url) > 200:
            source_url = source_url[:197] + "..."

        # Build complete metadata dict (stored but not embedded)
        metadata = {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "content_hash": doc.content_hash,
            "source_type": doc.metadata.source_type,
            "source_url": source_url,
            "timestamp": doc.metadata.timestamp.isoformat(),
            **doc.metadata.extra,
        }

        return LlamaDocument(
            text=doc.content,
            metadata=metadata,
            # CRITICAL: Exclude ALL metadata from embeddings to prevent chunk size inflation
            # Metadata is still available for retrieval/display but won't count toward token limit
            excluded_embed_metadata_keys=list(metadata.keys()),
            id_=doc.doc_id,
        )

    def _extract_entities_to_neo4j(
        self,
        source: str,
        doc: Document,
        llama_doc: LlamaDocument,
        nodes: Sequence[BaseNode],
    ) -> None:
        """Extract entities and relationships from document and store in Neo4j.

        Uses LlamaIndex PropertyGraphIndex with SimpleLLMPathExtractor to
        automatically identify entities and relationships from text.

        Args:
            source: Source identifier
            doc: Original document
            llama_doc: LlamaIndex document
            nodes: Processed nodes from ingestion pipeline

        Note:
            This runs after vector storage to ensure consistency.
            Uses SimpleLLMPathExtractor for automatic entity extraction.
        """
        try:
            logger.debug(
                "Extracting entities and relationships",
                extra={"source": source, "doc_id": doc.doc_id},
            )

            # Create Neo4j graph store
            graph_store = Neo4jPropertyGraphStore(
                username=self.config.neo4j_user,
                password=self.config.neo4j_password,
                url=self.config.neo4j_uri,
            )

            # Create entity extractors based on strategy
            kg_extractors = []

            if self.config.graph.extraction_strategy in ["simple", "combined"]:
                kg_extractors.append(
                    SimpleLLMPathExtractor(
                        llm=Settings.llm,
                        max_paths_per_chunk=self.config.graph.max_triplets_per_chunk,
                        num_workers=1,
                    )
                )

            if self.config.graph.extraction_strategy in ["implicit", "combined"]:
                kg_extractors.append(ImplicitPathExtractor())

            # Temporarily disable SchemaLLMPathExtractor - requires Enum types not strings
            # if self.config.graph.extraction_strategy in ["schema", "combined"]:
            #     schema_extractor = SchemaLLMPathExtractor(
            #         llm=Settings.llm,
            #         possible_entities=self.config.graph.entity_types,
            #         possible_relations=self.config.graph.allowed_relation_types,
            #         num_workers=1,
            #     )
            #     kg_extractors.append(schema_extractor)

            # Ensure we have at least one extractor
            if not kg_extractors:
                kg_extractors.append(
                    SimpleLLMPathExtractor(
                        llm=Settings.llm,
                        max_paths_per_chunk=self.config.graph.max_triplets_per_chunk,
                        num_workers=1,
                    )
                )

            logger.debug(
                f"Using {len(kg_extractors)} extractors with strategy: {self.config.graph.extraction_strategy}",
                extra={"strategy": self.config.graph.extraction_strategy, "num_extractors": len(kg_extractors)}
            )

            # Create PropertyGraphIndex for entity extraction
            # Note: This will extract entities from the document and store in Neo4j
            # Suppress RuntimeWarning from LlamaIndex SimpleLLMPathExtractor._aextract
            # Internal LlamaIndex async handling issue - coroutine not properly awaited
            # Functionality is NOT impacted - entity extraction completes successfully
            # TODO: Remove when LlamaIndex fixes upstream async handling
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*")
                PropertyGraphIndex.from_documents(
                    documents=[llama_doc],
                    property_graph_store=graph_store,
                    kg_extractors=kg_extractors,
                    embed_model=self.embed_model,
                    show_progress=False,
                )

            # Also create Document node in Neo4j for graph traversal
            self.neo4j_client.create_document_node(
                doc_id=doc.doc_id,
                properties={
                    "title": doc.title,
                    "source_type": doc.metadata.source_type,
                    "source_url": doc.metadata.source_url,
                    "content_hash": doc.content_hash,
                    "timestamp": doc.metadata.timestamp.isoformat(),
                },
            )

            logger.debug(
                "Entities and relationships extracted successfully",
                extra={"source": source, "doc_id": doc.doc_id},
            )

        except Exception as e:
            # Log error but don't fail ingestion
            error_msg = f"{type(e).__name__}: {str(e) or 'Unknown error'}"
            logger.warning(
                f"Failed to extract entities: {error_msg}",
                extra={
                    "source": source,
                    "doc_id": doc.doc_id,
                    "error": error_msg,
                    "traceback": traceback.format_exc(),
                },
            )


# Export public API
__all__ = ["IngestionPipeline", "IngestionSummary"]
