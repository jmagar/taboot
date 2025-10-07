"""Unit tests for deduplication logic."""

import hashlib
from datetime import datetime
from unittest.mock import Mock

import pytest

from llamacrawl.ingestion.deduplication import (
    DocumentDeduplicator,
    compute_content_hash,
)
from llamacrawl.models.document import Document, DocumentMetadata


@pytest.mark.unit
class TestContentHashing:
    """Test content hashing functions."""

    def test_compute_content_hash(self) -> None:
        """Test basic content hash computation."""
        content = "Sample text content"
        # Normalize: strip, collapse whitespace, lowercase
        normalized = " ".join(content.lower().split())
        expected_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        result = compute_content_hash(content)

        assert result == expected_hash
        assert len(result) == 64  # SHA-256 produces 64 hex chars

    def test_hash_normalization_whitespace(self) -> None:
        """Test whitespace normalization in hashing."""
        text1 = "  Hello    World  "
        text2 = "hello world"

        hash1 = compute_content_hash(text1)
        hash2 = compute_content_hash(text2)

        assert hash1 == hash2

    def test_hash_remove_punctuation(self) -> None:
        """Test punctuation removal in hashing."""
        text1 = "Hello, World!"
        text2 = "Hello World"

        hash_with_punct = compute_content_hash(text1, remove_punctuation=False)
        hash_without_punct = compute_content_hash(text1, remove_punctuation=True)
        hash2 = compute_content_hash(text2, remove_punctuation=True)

        # With punctuation removal, both should match
        assert hash_without_punct == hash2
        # Without removal, they differ
        assert hash_with_punct != hash2


@pytest.mark.unit
class TestDocumentDeduplicator:
    """Test document deduplication."""

    @pytest.fixture
    def mock_redis(self) -> Mock:
        """Create mock Redis client."""
        mock = Mock()
        mock.get_hash.return_value = None
        mock.set_hash.return_value = None
        return mock

    @pytest.fixture
    def dedup(self, mock_redis: Mock) -> DocumentDeduplicator:
        """Create deduplicator instance."""
        return DocumentDeduplicator(redis_client=mock_redis)

    def test_is_duplicate_new_document(self, dedup: DocumentDeduplicator, mock_redis: Mock) -> None:
        """Test new document is not marked as duplicate."""
        mock_redis.get_hash.return_value = None

        is_dup = dedup.is_duplicate("test_source", "doc_001", "test content")

        assert is_dup is False
        mock_redis.get_hash.assert_called_once_with("test_source", "doc_001")

    def test_is_duplicate_same_hash(self, dedup: DocumentDeduplicator, mock_redis: Mock) -> None:
        """Test document with same hash is marked as duplicate."""
        content = "test content"
        expected_hash = compute_content_hash(content)
        mock_redis.get_hash.return_value = expected_hash

        is_dup = dedup.is_duplicate("test_source", "doc_001", content)

        assert is_dup is True

    def test_is_duplicate_different_hash(
        self, dedup: DocumentDeduplicator, mock_redis: Mock
    ) -> None:
        """Test document with different hash is not duplicate."""
        mock_redis.get_hash.return_value = "old_hash_value"

        is_dup = dedup.is_duplicate("test_source", "doc_001", "new content")

        assert is_dup is False

    def test_mark_processed(self, dedup: DocumentDeduplicator, mock_redis: Mock) -> None:
        """Test marking document as processed stores hash."""
        content_hash = "abc123def456"

        dedup.mark_processed("test_source", "doc_001", content_hash)

        mock_redis.set_hash.assert_called_once_with("test_source", "doc_001", content_hash)

    def test_get_deduplicated_documents(
        self, dedup: DocumentDeduplicator, mock_redis: Mock, sample_documents: list[Document]
    ) -> None:
        """Test batch deduplication."""
        # Mock Redis pipeline for batch operations
        mock_pipeline = Mock()
        mock_redis.client.pipeline.return_value = mock_pipeline

        results = []
        for i, doc in enumerate(sample_documents):
            if i >= 5:
                # Return matching hash for duplicate
                stored_hashes_hash = compute_content_hash(doc.content)
                results.extend([stored_hashes_hash, True])
            else:
                # Return None for new document
                results.extend([None, False])

        mock_pipeline.execute.return_value = results

        new_docs, duplicates = dedup.get_deduplicated_documents("test_source", sample_documents)

        assert len(new_docs) == 5
        assert len(duplicates) == 5

    def test_dedup_duplicate_content_new_ids(
        self, dedup: DocumentDeduplicator, mock_redis: Mock, sample_documents: list[Document]
    ) -> None:
        """Documents with new IDs but existing content hashes are treated as duplicates."""

        mock_pipeline = Mock()
        mock_redis.client.pipeline.return_value = mock_pipeline

        # Simulate all stored hashes missing, but content hash already known in set
        results = []
        for doc in sample_documents[:2]:
            results.extend([None, True])  # stored hash missing, hash seen before

        mock_pipeline.execute.return_value = results

        new_docs, duplicates = dedup.get_deduplicated_documents("test_source", sample_documents[:2])

        assert not new_docs
        assert len(duplicates) == 2


@pytest.mark.unit
class TestDeduplicationMetrics:
    """Test deduplication metrics and logging."""

    @pytest.fixture
    def dedup(self, mock_redis_client: Mock) -> DocumentDeduplicator:
        """Create deduplicator."""
        return DocumentDeduplicator(redis_client=mock_redis_client)

    def test_deduplication_rate_calculation(
        self, dedup: DocumentDeduplicator, mock_redis_client: Mock
    ) -> None:
        """Test deduplication rate calculation."""
        # Create 10 documents, mock 3 as duplicates
        docs = [
            Document(
                doc_id=f"test_{i}",
                title=f"Test {i}",
                content=f"Content {i}",
                content_hash=compute_content_hash(f"Content {i}"),
                metadata=DocumentMetadata(
                    source_type="gmail",
                    source_url="http://test.com",
                    timestamp=datetime.now(),
                ),
            )
            for i in range(10)
        ]

        # Mock Redis pipeline
        mock_pipeline = Mock()
        mock_redis_client.client.pipeline.return_value = mock_pipeline

        # Mock: docs 2, 5, 8 are duplicates (return matching hash)
        # Others are new (return None)
        results = []
        for i, doc in enumerate(docs):
            if i in [2, 5, 8]:
                # Return matching hash for duplicate
                results.extend([doc.content_hash, True])
            else:
                # Return None for new document
                results.extend([None, False])

        mock_pipeline.execute.return_value = results

        new_docs, duplicates = dedup.get_deduplicated_documents("test_source", docs)

        assert len(duplicates) == 3
        assert len(new_docs) == 7
        dedup_rate = (len(duplicates) / len(docs)) * 100
        assert dedup_rate == 30.0
