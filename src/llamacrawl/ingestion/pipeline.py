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

import logging
import time
import traceback
import warnings
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

import redis.asyncio as aioredis
from llama_index.core import Settings
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.ingestion import (
    IngestionCache,
)
from llama_index.core.ingestion import (
    IngestionPipeline as LlamaIngestionPipeline,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode
from llama_index.core.schema import Document as LlamaDocument
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.vector_stores.qdrant import QdrantVectorStore

from llamacrawl.config import Config
from llamacrawl.embeddings.tei import TEIEmbedding
from llamacrawl.ingestion.deduplication import DocumentDeduplicator
from llamacrawl.llms import ClaudeAgentLLM
from llamacrawl.models.document import Document
from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.storage.qdrant import QdrantClient
from llamacrawl.storage.redis import PickleableRedisKVStore, RedisClient
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)

# LlamaIndex emits noisy pickling warnings when multiprocessing serializes
# the sentence splitter. Suppress them since the attributes are restored lazily.
warnings.filterwarnings(
    "ignore",
    message=r"Removing unpickleable private attribute .*",
)

_PICKLE_WARNING_SUBSTRING = "Removing unpickleable private attribute"


class _SuppressPickleWarnings(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return _PICKLE_WARNING_SUBSTRING not in record.getMessage()


logging.getLogger().addFilter(_SuppressPickleWarnings())


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
        self._seen_content_hashes: set[str] = set()

        # Initialize deduplicator
        self.deduplicator = DocumentDeduplicator(
            redis_client=redis_client,
            remove_punctuation=False,  # Keep punctuation for better deduplication accuracy
        )

        # Initialize Settings.llm for entity extraction
        Settings.llm = ClaudeAgentLLM(
            model=config.graph.extraction_model,
        )

        # Initialize Settings.embed_model for PropertyGraphIndex when compatible
        if isinstance(self.embed_model, BaseEmbedding):
            Settings.embed_model = self.embed_model
        else:
            logger.debug(
                "Skipping Settings.embed_model assignment; embed_model is not a BaseEmbedding",
                extra={"embed_model_type": type(self.embed_model).__name__},
            )

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
        redis_url = self.config.redis_url or f"redis://{redis_host}:{redis_port}"

        # Create async Redis client for LlamaIndex components
        async_redis_client = aioredis.Redis.from_url(
            redis_url,
            decode_responses=True,
        )

        # Create Redis document store for caching
        docstore = RedisDocumentStore(
            redis_kvstore=PickleableRedisKVStore(
                redis_uri=redis_url,
                redis_client=self.redis_client.client,
                async_redis_client=async_redis_client,
            ),
            namespace="llamacrawl_docstore",
        )

        # Create ingestion cache using RedisKVStore (BaseKVStore implementation)
        # Reuse existing Redis client connection with namespace support via **kwargs
        cache = IngestionCache(
            collection="llamacrawl_cache",
            cache=PickleableRedisKVStore(
                redis_uri=redis_url,
                redis_client=self.redis_client.client,
                async_redis_client=async_redis_client,
            ),
        )

        # Create Qdrant vector store for LlamaIndex
        # Content is stored in _node_content field by LlamaIndex
        vector_store = QdrantVectorStore(
            client=self.qdrant_client.client,
            collection_name=self.qdrant_client.collection_name,
            batch_size=self.config.vector_store.upsert_batch_size,
            parallel=self.config.vector_store.upsert_parallel,
            max_retries=self.config.vector_store.upsert_max_retries,
        )

        # Create transformation pipeline
        transformations = [
            # Chunking transformation
            SentenceSplitter(
                chunk_size=self.config.ingestion.chunk_size,
                chunk_overlap=self.config.ingestion.chunk_overlap,
                separator=" ",
            ),
        ]

        # Add language filter if enabled (BEFORE embedding for cost savings)
        language_filter_config = self.config.ingestion.language_filter
        if language_filter_config.enabled:
            from llamacrawl.ingestion.language_filter import LanguageFilter

            language_filter = LanguageFilter(
                allowed_languages=set(language_filter_config.allowed_languages),
                confidence_threshold=language_filter_config.confidence_threshold,
                min_content_length=language_filter_config.min_content_length,
                log_filtered=language_filter_config.log_filtered,
            )
            transformations.append(language_filter)

            logger.info(
                "Language filtering enabled in pipeline",
                extra={
                    "allowed_languages": language_filter_config.allowed_languages,
                    "confidence_threshold": language_filter_config.confidence_threshold,
                },
            )

        # Add embedding transformation (always last) when compatible
        if isinstance(self.embed_model, BaseEmbedding):
            transformations.append(self.embed_model)
        else:
            logger.debug(
                "Embed model is not a BaseEmbedding; skipping transformation append",
                extra={"embed_model_type": type(self.embed_model).__name__},
            )

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

        # Additional intra-run deduplication based on content hash to avoid
        # re-embedding identical documents discovered under different URLs
        unique_documents: list[Document] = []
        session_duplicates = 0
        for doc in new_documents:
            content_hash = doc.content_hash
            if content_hash and content_hash in self._seen_content_hashes:
                session_duplicates += 1
                logger.debug(
                    "Skipping duplicate document encountered within current run",
                    extra={
                        "source": source,
                        "doc_id": doc.doc_id,
                        "content_hash": content_hash,
                    },
                )
            else:
                if content_hash:
                    self._seen_content_hashes.add(content_hash)
                unique_documents.append(doc)

        if session_duplicates:
            summary.deduplicated += session_duplicates
            logger.info(
                "Skipped additional duplicate documents based on content hash",
                extra={
                    "source": source,
                    "session_duplicates": session_duplicates,
                },
            )

        if not unique_documents:
            logger.info(
                "All documents within this batch were duplicates based on content hash",
                extra={"source": source},
            )
            summary.duration_seconds = time.time() - start_time
            return summary

        new_documents = unique_documents

        # Drop documents with missing or whitespace-only content before embedding
        filtered_documents: list[Document] = []
        skipped_empty_docs = 0
        for doc in new_documents:
            if doc.content and doc.content.strip():
                filtered_documents.append(doc)
            else:
                skipped_empty_docs += 1
                logger.warning(
                    "Skipping document with empty content prior to embedding",
                    extra={
                        "source": source,
                        "doc_id": doc.doc_id,
                        "source_type": doc.metadata.source_type,
                        "source_url": doc.metadata.source_url,
                    },
                )

        if skipped_empty_docs:
            logger.info(
                "Filtered documents with empty content before ingestion",
                extra={
                    "source": source,
                    "skipped_empty_documents": skipped_empty_docs,
                },
            )

        if not filtered_documents:
            summary.failed = skipped_empty_docs
            summary.duration_seconds = time.time() - start_time
            return summary

        new_documents = filtered_documents

        # Step 2: Process documents with error handling
        processed_documents: list[Document] = []
        failed_count = skipped_empty_docs

        batch_size = max(1, self.config.ingestion.batch_size)
        current_batch: list[Document] = []

        for idx, doc in enumerate(new_documents):
            if (idx + 1) % self.log_progress_interval == 0:
                logger.info(
                    f"Processing document {idx + 1}/{len(new_documents)}",
                    extra={
                        "source": source,
                        "doc_id": doc.doc_id,
                        "progress": f"{idx + 1}/{len(new_documents)}",
                    },
                )

            current_batch.append(doc)

            if len(current_batch) >= batch_size:
                processed, failed = self._process_batch(source, current_batch)
                processed_documents.extend(processed)
                failed_count += failed
                current_batch = []

        if current_batch:
            processed, failed = self._process_batch(source, current_batch)
            processed_documents.extend(processed)
            failed_count += failed

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

        Uses ClaudeEntityExtractor with Claude Agent SDK tool use for reliable
        structured output without event loop conflicts.

        Args:
            source: Source identifier
            doc: Original document
            llama_doc: LlamaIndex document
            nodes: Processed nodes from ingestion pipeline

        Note:
            This runs after vector storage to ensure consistency.
            Runs async extraction in a new event loop thread.
        """
        import asyncio
        import threading
        from queue import Queue

        from llamacrawl.ingestion.pipeline_integration import extract_entities_to_neo4j

        try:
            logger.debug(
                "Extracting entities and relationships",
                extra={"source": source, "doc_id": doc.doc_id},
            )

            # Run async extraction in a new thread with fresh event loop
            # This avoids "asyncio.run() cannot be called from a running event loop" errors
            result_queue: Queue[dict[str, int] | Exception] = Queue(maxsize=1)

            def run_async_extraction() -> None:
                """Run extraction in new event loop on background thread."""
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    result = loop.run_until_complete(
                        extract_entities_to_neo4j(
                            config=self.config,
                            neo4j_client=self.neo4j_client,
                            source=source,
                            doc=doc,
                            llama_doc=llama_doc,
                            nodes=nodes,
                        )
                    )
                    result_queue.put(result)
                except Exception as exc:
                    result_queue.put(exc)
                finally:
                    try:
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    except Exception:
                        pass
                    loop.close()

            thread = threading.Thread(target=run_async_extraction, daemon=True)
            thread.start()
            thread.join(timeout=300)  # 5 minute timeout

            if thread.is_alive():
                logger.error(
                    "Entity extraction timed out after 5 minutes",
                    extra={"source": source, "doc_id": doc.doc_id}
                )
                return

            # Get result from queue
            result_or_exc = result_queue.get()
            if isinstance(result_or_exc, Exception):
                raise result_or_exc

            logger.info(
                "Entity extraction completed",
                extra={
                    "source": source,
                    "doc_id": doc.doc_id,
                    **result_or_exc,
                }
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


    def _process_batch(self, source: str, batch: list[Document]) -> tuple[list[Document], int]:
        """Process a batch of documents through the ingestion pipeline.

        Falls back to per-document processing if the batch fails to ensure failures
        don't block the entire batch.
        """
        try:
            processed_docs = self._run_pipeline_batch(source, batch)
            return processed_docs, 0
        except Exception as batch_error:  # pragma: no cover - defensive fallback
            logger.warning(
                "Batch processing failed; falling back to per-document processing",
                extra={
                    "source": source,
                    "batch_size": len(batch),
                    "error": f"{type(batch_error).__name__}: {batch_error}",
                    "traceback": traceback.format_exc(),
                },
            )

            processed_docs: list[Document] = []
            failed_count = 0
            for doc in batch:
                try:
                    processed_docs.extend(self._run_pipeline_batch(source, [doc]))
                except Exception as doc_error:
                    self._handle_document_failure(source, doc, doc_error)
                    failed_count += 1
            return processed_docs, failed_count

    def _run_pipeline_batch(self, source: str, batch: list[Document]) -> list[Document]:
        """Execute the LlamaIndex pipeline for a batch of documents."""
        llama_docs_by_id: dict[str, LlamaDocument] = {}
        llama_docs: list[LlamaDocument] = []

        for doc in batch:
            llama_doc = self._convert_to_llama_document(doc)
            llama_docs.append(llama_doc)
            llama_docs_by_id[doc.doc_id] = llama_doc

        pipeline_workers = (
            self.config.ingestion.pipeline_workers
            if getattr(self.config.ingestion, "pipeline_workers", 1) > 1
            else None
        )

        raw_nodes = self.llama_pipeline.run(
            documents=llama_docs,
            show_progress=False,
            num_workers=pipeline_workers,
        )

        # Drop empty or whitespace-only chunks to avoid downstream embedding errors
        nodes: list[BaseNode] = []
        skipped_empty_chunks = 0
        for node in raw_nodes:
            text_content = node.get_content(metadata_mode="none")
            if not text_content or not text_content.strip():
                skipped_empty_chunks += 1
                continue
            nodes.append(node)

        if skipped_empty_chunks:
            logger.debug(
                "Skipped empty chunks after LlamaIndex pipeline",
                extra={"skipped_chunks": skipped_empty_chunks},
            )

        nodes_by_doc: dict[str, list[BaseNode]] = defaultdict(list)
        for node in nodes:
            ref_doc_id = getattr(node, "ref_doc_id", None) or node.metadata.get("doc_id")
            if ref_doc_id:
                nodes_by_doc[ref_doc_id].append(node)

        for doc in batch:
            logger.debug(
                "Document processed through LlamaIndex pipeline",
                extra={
                    "source": source,
                    "doc_id": doc.doc_id,
                    "chunks_created": len(nodes_by_doc.get(doc.doc_id, [])),
                },
            )

            if self.config.graph.auto_extract_entities:
                logger.info(
                    "Starting entity extraction for %s",
                    doc.doc_id,
                    extra={
                        "source": source,
                        "doc_id": doc.doc_id,
                        "strategy": self.config.graph.extraction_strategy,
                    },
                )
                self._extract_entities_to_neo4j(
                    source,
                    doc,
                    llama_docs_by_id[doc.doc_id],
                    nodes_by_doc.get(doc.doc_id, []),
                )
                logger.info(
                    "Entity extraction completed for %s",
                    doc.doc_id,
                    extra={"doc_id": doc.doc_id},
                )

        return batch

    def _handle_document_failure(self, source: str, doc: Document, error: Exception) -> None:
        """Log a document processing failure and push it to the DLQ if enabled."""
        error_msg = f"{type(error).__name__}: {str(error)}"
        logger.error(
            f"Failed to process document: {error_msg}",
            extra={
                "source": source,
                "doc_id": doc.doc_id,
                "error": error_msg,
                "traceback": traceback.format_exc(),
            },
        )

        # Only push to DLQ if enabled in config
        if self.config.ingestion.dlq.enabled:
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

            # Periodically cleanup old DLQ entries based on retention policy
            # Run cleanup with 10% probability to avoid overhead on every push
            import random
            if random.random() < 0.1:
                try:
                    removed = self.redis_client.cleanup_dlq(
                        source=source,
                        retention_days=self.config.ingestion.dlq.retention_days,
                    )
                    if removed > 0:
                        logger.info(
                            f"DLQ cleanup: removed {removed} old entries",
                            extra={"source": source, "removed_count": removed},
                        )
                except Exception as cleanup_error:
                    logger.warning(
                        f"DLQ cleanup failed: {cleanup_error}",
                        extra={"source": source, "error": str(cleanup_error)},
                    )
        else:
            logger.debug(
                "DLQ is disabled, skipping DLQ push",
                extra={"source": source, "doc_id": doc.doc_id},
            )

# Export public API
__all__ = ["IngestionPipeline", "IngestionSummary"]
