"""Deduplication module for content hashing and duplicate detection.

This module provides SHA-256 content hashing with normalization and Redis-backed
deduplication checks for the RAG pipeline. It ensures unchanged documents are
not reprocessed during incremental sync.

Key features:
- Content normalization (whitespace, lowercase, optional punctuation removal)
- SHA-256 hashing for deterministic content fingerprinting
- Batch deduplication via Redis pipelines for efficiency
- Logging of deduplication hits for monitoring
"""

import hashlib
import re

from llamacrawl.models.document import Document
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)


def compute_content_hash(content: str, remove_punctuation: bool = False) -> str:
    """Compute SHA-256 hash of normalized content.

    Normalization steps:
    1. Strip leading/trailing whitespace
    2. Collapse multiple whitespace to single space
    3. Convert to lowercase
    4. Optionally remove punctuation

    This ensures consistent hashing across runs regardless of minor formatting changes.

    Args:
        content: Raw document content to hash
        remove_punctuation: If True, remove all punctuation before hashing (default: False)

    Returns:
        64-character hexadecimal SHA-256 hash

    Example:
        >>> hash1 = compute_content_hash("  The Quick Brown Fox  ")
        >>> hash2 = compute_content_hash("the quick brown fox")
        >>> hash1 == hash2
        True
    """
    # Strip leading/trailing whitespace
    normalized = content.strip()

    # Collapse multiple whitespace (spaces, tabs, newlines) to single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Convert to lowercase for case-insensitive comparison
    normalized = normalized.lower()

    # Optionally remove punctuation
    if remove_punctuation:
        # Remove all punctuation except spaces
        normalized = re.sub(r"[^\w\s]", "", normalized)

    # Compute SHA-256 hash
    hash_bytes = hashlib.sha256(normalized.encode("utf-8"))
    return hash_bytes.hexdigest()


class DocumentDeduplicator:
    """Redis-backed document deduplication using content hashing.

    This class provides methods to:
    1. Check if a document has been seen before (unchanged content)
    2. Mark documents as processed with their content hash
    3. Batch deduplicate a list of documents

    Content hashes are stored permanently in Redis (no TTL) under the key:
    hash:<source>:<doc_id>

    Attributes:
        redis: RedisClient instance for state management
        remove_punctuation: If True, remove punctuation before hashing
    """

    def __init__(self, redis_client: RedisClient, remove_punctuation: bool = False):
        """Initialize deduplicator with Redis client.

        Args:
            redis_client: RedisClient instance for hash storage
            remove_punctuation: If True, remove punctuation during normalization
        """
        self.redis = redis_client
        self.remove_punctuation = remove_punctuation

    def is_duplicate(self, source: str, doc_id: str, content: str) -> bool:
        """Check if document content is unchanged from previous ingestion.

        Computes content hash and compares with stored hash in Redis.
        Returns True if hashes match (document unchanged).

        Args:
            source: Source identifier (e.g., 'gmail', 'github')
            doc_id: Unique document identifier
            content: Document content to check

        Returns:
            True if document is duplicate (unchanged), False otherwise

        Example:
            >>> dedup = DocumentDeduplicator(redis_client)
            >>> is_dup = dedup.is_duplicate('gmail', 'msg_123', 'email body text')
            >>> if is_dup:
            ...     logger.info("Skipping unchanged document")
        """
        # Compute hash of current content
        current_hash = compute_content_hash(content, self.remove_punctuation)

        # Retrieve stored hash from Redis
        stored_hash = self.redis.get_hash(source, doc_id)

        # Check if hashes match
        if stored_hash and stored_hash == current_hash:
            logger.debug(
                "Document is duplicate (unchanged content)",
                extra={
                    "source": source,
                    "doc_id": doc_id,
                    "content_hash": current_hash,
                },
            )
            return True

        return False

    def mark_processed(self, source: str, doc_id: str, content_hash: str) -> None:
        """Store content hash in Redis to mark document as processed.

        Hash is stored permanently (no TTL) to enable incremental sync
        across runs without re-embedding unchanged content.

        Args:
            source: Source identifier
            doc_id: Unique document identifier
            content_hash: SHA-256 hash of document content

        Example:
            >>> dedup = DocumentDeduplicator(redis_client)
            >>> content_hash = compute_content_hash(doc.content)
            >>> dedup.mark_processed('github', 'repo/owner#123', content_hash)
        """
        # Store hash in Redis with no TTL (permanent)
        self.redis.set_hash(source, doc_id, content_hash)

        logger.debug(
            "Marked document as processed",
            extra={
                "source": source,
                "doc_id": doc_id,
                "content_hash": content_hash,
            },
        )

    def get_deduplicated_documents(
        self, source: str, documents: list[Document]
    ) -> tuple[list[Document], list[Document]]:
        """Batch deduplicate documents, returning only new/modified ones.

        Uses Redis pipeline for efficient batch operations. For each document:
        1. Compute content hash
        2. Check if hash matches stored value
        3. Filter out unchanged documents

        Args:
            source: Source identifier for all documents
            documents: List of documents to deduplicate

        Returns:
            Tuple of (new_documents, duplicate_documents)
            - new_documents: Documents that are new or modified
            - duplicate_documents: Documents that are unchanged (duplicates)

        Example:
            >>> dedup = DocumentDeduplicator(redis_client)
            >>> new_docs, dup_docs = dedup.get_deduplicated_documents('gmail', all_docs)
            >>> logger.info(f"Processing {len(new_docs)} new/modified documents")
            >>> logger.info(f"Skipping {len(dup_docs)} unchanged documents")
        """
        if not documents:
            return [], []

        new_documents: list[Document] = []
        duplicate_documents: list[Document] = []

        hash_set_key = f"hash_content:{source}"

        # Use Redis pipeline for batch operations (more efficient than individual calls)
        pipeline = self.redis.client.pipeline()

        doc_hashes: list[str] = []

        for doc in documents:
            current_hash = compute_content_hash(doc.content, self.remove_punctuation)
            doc.content_hash = current_hash
            doc_hashes.append(current_hash)

            hash_key = f"hash:{source}:{doc.doc_id}"
            pipeline.get(hash_key)
            pipeline.sismember(hash_set_key, current_hash)

        results = pipeline.execute()

        # Process each document
        for idx, doc in enumerate(documents):
            stored_hash = results[2 * idx]
            hash_seen_before = bool(results[2 * idx + 1])
            current_hash = doc_hashes[idx]

            if stored_hash and stored_hash == current_hash:
                duplicate_documents.append(doc)
                logger.debug(
                    "Document unchanged (duplicate)",
                    extra={
                        "source": source,
                        "doc_id": doc.doc_id,
                        "content_hash": current_hash,
                    },
                )
            elif not stored_hash and hash_seen_before:
                duplicate_documents.append(doc)
                logger.debug(
                    "Document duplicate based on content hash",
                    extra={
                        "source": source,
                        "doc_id": doc.doc_id,
                        "content_hash": current_hash,
                    },
                )
            else:
                new_documents.append(doc)
                logger.debug(
                    "Document new or modified",
                    extra={
                        "source": source,
                        "doc_id": doc.doc_id,
                        "content_hash": current_hash,
                        "previously_seen": bool(stored_hash or hash_seen_before),
                    },
                )

        # Log summary
        total = len(documents)
        dedup_count = len(duplicate_documents)
        new_count = len(new_documents)

        logger.info(
            "Deduplication complete",
            extra={
                "source": source,
                "total_documents": total,
                "new_or_modified": new_count,
                "duplicates": dedup_count,
                "deduplication_rate": round(dedup_count / total * 100, 1) if total > 0 else 0,
            },
        )

        return new_documents, duplicate_documents

    def update_hashes_batch(self, source: str, documents: list[Document]) -> None:
        """Batch update content hashes in Redis for processed documents.

        Uses Redis pipeline for efficient batch operations.

        Args:
            source: Source identifier for all documents
            documents: List of documents to update hashes for

        Example:
            >>> dedup = DocumentDeduplicator(redis_client)
            >>> # After successful ingestion
            >>> dedup.update_hashes_batch('github', processed_docs)
        """
        if not documents:
            return

        # Use Redis pipeline for batch operations
        pipeline = self.redis.client.pipeline()

        hash_set_key = f"hash_content:{source}"

        for doc in documents:
            key = f"hash:{source}:{doc.doc_id}"
            # Use content_hash from document model (already computed)
            pipeline.set(key, doc.content_hash)
            pipeline.sadd(hash_set_key, doc.content_hash)

        # Execute all SET commands at once
        pipeline.execute()

        logger.info(
            "Updated content hashes in batch",
            extra={
                "source": source,
                "document_count": len(documents),
            },
        )

    def clear_hashes(self, source: str, doc_ids: list[str] | None = None) -> int:
        """Clear stored content hashes for a source.

        If doc_ids is provided, clears only those specific documents.
        Otherwise, clears all hashes for the source.

        Args:
            source: Source identifier
            doc_ids: Optional list of specific document IDs to clear

        Returns:
            Number of hashes cleared

        Example:
            >>> dedup = DocumentDeduplicator(redis_client)
            >>> # Clear specific documents
            >>> count = dedup.clear_hashes('gmail', ['msg_1', 'msg_2'])
            >>> # Clear all hashes for source
            >>> count = dedup.clear_hashes('gmail')
        """
        if doc_ids:
            # Clear specific document hashes
            pipeline = self.redis.client.pipeline()
            keys = [f"hash:{source}:{doc_id}" for doc_id in doc_ids]

            for key in keys:
                pipeline.delete(key)

            results = pipeline.execute()
            cleared = int(sum(results))

            logger.info(
                "Cleared specific document hashes",
                extra={
                    "source": source,
                    "document_ids": len(doc_ids),
                    "cleared_count": cleared,
                },
            )

            return cleared

        # Clear all hashes for source
        pattern = f"hash:{source}:*"
        keys = [key.decode('utf-8') for key in self.redis.client.keys(pattern)]

        if not keys:
            logger.info("No hashes to clear", extra={"source": source})
            return 0

        # Delete all matching keys
        deleted = int(self.redis.client.delete(*keys))

        logger.info(
            "Cleared all hashes for source",
            extra={
                "source": source,
                "cleared_count": deleted,
            },
        )

        return deleted


# Export public API
__all__ = [
    "compute_content_hash",
    "DocumentDeduplicator",
]
