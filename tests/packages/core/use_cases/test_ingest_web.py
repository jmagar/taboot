"""Tests for IngestWebUseCase orchestrator.

Tests the full ingestion pipeline orchestration:
WebReader → Normalizer → Chunker → Embedder → QdrantWriter
With job state tracking and error handling.
"""

from unittest.mock import Mock
from uuid import UUID

import pytest
from llama_index.core import Document as LlamaDocument

from packages.schemas.models import Chunk, IngestionJob, JobState, SourceType


class TestIngestWebUseCase:
    """Test IngestWebUseCase orchestration."""

    @pytest.fixture
    def mock_web_reader(self) -> Mock:
        """Create mock WebReader."""
        reader = Mock()
        # Return 2 documents by default
        reader.load_data.return_value = [
            LlamaDocument(
                text="<html><body><h1>Test Page 1</h1><p>Content 1</p></body></html>",
                metadata={"source_url": "https://example.com/page1"},
            ),
            LlamaDocument(
                text="<html><body><h1>Test Page 2</h1><p>Content 2</p></body></html>",
                metadata={"source_url": "https://example.com/page2"},
            ),
        ]
        return reader

    @pytest.fixture
    def mock_normalizer(self) -> Mock:
        """Create mock Normalizer."""
        normalizer = Mock()
        normalizer.normalize.side_effect = lambda html: f"# Normalized\n\n{html[:50]}"
        return normalizer

    @pytest.fixture
    def mock_chunker(self) -> Mock:
        """Create mock Chunker."""
        chunker = Mock()
        # Return 3 chunks per document
        def chunk_doc(doc: LlamaDocument) -> list[LlamaDocument]:
            return [
                LlamaDocument(
                    text=f"Chunk {i} of {doc.metadata.get('source_url', 'unknown')}",
                    metadata={**doc.metadata, "chunk_index": i, "chunk_count": 3},
                )
                for i in range(3)
            ]

        chunker.chunk_document.side_effect = chunk_doc
        return chunker

    @pytest.fixture
    def mock_embedder(self) -> Mock:
        """Create mock Embedder."""
        embedder = Mock()
        # Return 768-dim embeddings
        embedder.embed_texts.side_effect = lambda texts: [[0.1] * 768 for _ in texts]
        return embedder

    @pytest.fixture
    def mock_qdrant_writer(self) -> Mock:
        """Create mock QdrantWriter."""
        writer = Mock()
        writer.upsert_batch.return_value = None
        return writer

    def test_execute_orchestrates_full_pipeline(
        self,
        mock_web_reader: Mock,
        mock_normalizer: Mock,
        mock_chunker: Mock,
        mock_embedder: Mock,
        mock_qdrant_writer: Mock,
    ) -> None:
        """Test that execute orchestrates the full ingestion pipeline."""
        # Import here to avoid circular dependency in fixture setup
        from packages.core.use_cases.ingest_web import IngestWebUseCase

        use_case = IngestWebUseCase(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="test_collection",
        )

        # Execute
        url = "https://example.com"
        limit = 10
        job = use_case.execute(url=url, limit=limit)

        # Verify pipeline orchestration
        mock_web_reader.load_data.assert_called_once_with(url, limit)
        assert mock_normalizer.normalize.call_count == 2  # 2 documents
        assert mock_chunker.chunk_document.call_count == 2  # 2 documents
        mock_embedder.embed_texts.assert_called_once()  # 1 batch call
        mock_qdrant_writer.upsert_batch.assert_called_once()

        # Verify job state
        assert isinstance(job, IngestionJob)
        assert job.source_type == SourceType.WEB
        assert job.source_target == url
        assert job.state == JobState.COMPLETED
        assert job.pages_processed == 2
        assert job.chunks_created == 6  # 2 docs * 3 chunks each
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.completed_at >= job.started_at
        assert job.errors is None

    def test_execute_creates_job_in_pending_state(
        self,
        mock_web_reader: Mock,
        mock_normalizer: Mock,
        mock_chunker: Mock,
        mock_embedder: Mock,
        mock_qdrant_writer: Mock,
    ) -> None:
        """Test that execute creates a job in PENDING state initially."""
        from packages.core.use_cases.ingest_web import IngestWebUseCase

        use_case = IngestWebUseCase(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="test_collection",
        )

        job = use_case.execute(url="https://example.com", limit=5)

        # Job should start in PENDING, then move to RUNNING, then COMPLETED
        assert job.state == JobState.COMPLETED
        assert job.created_at is not None

    def test_execute_transitions_to_running(
        self,
        mock_web_reader: Mock,
        mock_normalizer: Mock,
        mock_chunker: Mock,
        mock_embedder: Mock,
        mock_qdrant_writer: Mock,
    ) -> None:
        """Test that job transitions from PENDING to RUNNING."""
        from packages.core.use_cases.ingest_web import IngestWebUseCase

        use_case = IngestWebUseCase(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="test_collection",
        )

        job = use_case.execute(url="https://example.com", limit=5)

        assert job.started_at is not None
        assert job.started_at >= job.created_at

    def test_execute_updates_pages_processed_incrementally(
        self,
        mock_web_reader: Mock,
        mock_normalizer: Mock,
        mock_chunker: Mock,
        mock_embedder: Mock,
        mock_qdrant_writer: Mock,
    ) -> None:
        """Test that pages_processed is updated for each document."""
        from packages.core.use_cases.ingest_web import IngestWebUseCase

        # Setup reader to return 3 documents
        mock_web_reader.load_data.return_value = [
            LlamaDocument(text="Doc 1", metadata={"source_url": "https://example.com/1"}),
            LlamaDocument(text="Doc 2", metadata={"source_url": "https://example.com/2"}),
            LlamaDocument(text="Doc 3", metadata={"source_url": "https://example.com/3"}),
        ]

        use_case = IngestWebUseCase(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="test_collection",
        )

        job = use_case.execute(url="https://example.com", limit=5)

        assert job.pages_processed == 3

    def test_execute_updates_chunks_created_incrementally(
        self,
        mock_web_reader: Mock,
        mock_normalizer: Mock,
        mock_chunker: Mock,
        mock_embedder: Mock,
        mock_qdrant_writer: Mock,
    ) -> None:
        """Test that chunks_created is updated for each batch."""
        from packages.core.use_cases.ingest_web import IngestWebUseCase

        use_case = IngestWebUseCase(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="test_collection",
        )

        job = use_case.execute(url="https://example.com", limit=5)

        # 2 docs * 3 chunks each = 6 total
        assert job.chunks_created == 6

    def test_execute_handles_empty_document_list(
        self,
        mock_web_reader: Mock,
        mock_normalizer: Mock,
        mock_chunker: Mock,
        mock_embedder: Mock,
        mock_qdrant_writer: Mock,
    ) -> None:
        """Test that execute handles empty document list gracefully."""
        from packages.core.use_cases.ingest_web import IngestWebUseCase

        # Return empty list
        mock_web_reader.load_data.return_value = []

        use_case = IngestWebUseCase(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="test_collection",
        )

        job = use_case.execute(url="https://example.com", limit=5)

        assert job.state == JobState.COMPLETED
        assert job.pages_processed == 0
        assert job.chunks_created == 0
        mock_normalizer.normalize.assert_not_called()
        mock_chunker.chunk_document.assert_not_called()
        mock_embedder.embed_texts.assert_not_called()
        mock_qdrant_writer.upsert_batch.assert_not_called()

    def test_execute_handles_web_reader_error(
        self,
        mock_web_reader: Mock,
        mock_normalizer: Mock,
        mock_chunker: Mock,
        mock_embedder: Mock,
        mock_qdrant_writer: Mock,
    ) -> None:
        """Test that execute handles WebReader errors and marks job as FAILED."""
        from packages.core.use_cases.ingest_web import IngestWebUseCase

        # Simulate WebReader error
        mock_web_reader.load_data.side_effect = Exception("Connection timeout")

        use_case = IngestWebUseCase(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="test_collection",
        )

        job = use_case.execute(url="https://example.com", limit=5)

        assert job.state == JobState.FAILED
        assert job.errors is not None
        assert len(job.errors) == 1
        assert "Connection timeout" in job.errors[0]["error"]
        assert job.completed_at is not None

    def test_execute_handles_embedder_error(
        self,
        mock_web_reader: Mock,
        mock_normalizer: Mock,
        mock_chunker: Mock,
        mock_embedder: Mock,
        mock_qdrant_writer: Mock,
    ) -> None:
        """Test that execute handles Embedder errors and marks job as FAILED."""
        from packages.core.use_cases.ingest_web import IngestWebUseCase

        # Simulate Embedder error
        mock_embedder.embed_texts.side_effect = Exception("TEI service unavailable")

        use_case = IngestWebUseCase(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="test_collection",
        )

        job = use_case.execute(url="https://example.com", limit=5)

        assert job.state == JobState.FAILED
        assert job.errors is not None
        assert len(job.errors) == 1
        assert "TEI service unavailable" in job.errors[0]["error"]

    def test_execute_handles_qdrant_writer_error(
        self,
        mock_web_reader: Mock,
        mock_normalizer: Mock,
        mock_chunker: Mock,
        mock_embedder: Mock,
        mock_qdrant_writer: Mock,
    ) -> None:
        """Test that execute handles QdrantWriter errors and marks job as FAILED."""
        from packages.core.use_cases.ingest_web import IngestWebUseCase

        # Simulate QdrantWriter error
        mock_qdrant_writer.upsert_batch.side_effect = Exception("Qdrant connection refused")

        use_case = IngestWebUseCase(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="test_collection",
        )

        job = use_case.execute(url="https://example.com", limit=5)

        assert job.state == JobState.FAILED
        assert job.errors is not None
        assert len(job.errors) == 1
        assert "Qdrant connection refused" in job.errors[0]["error"]

    def test_execute_creates_valid_chunk_models(
        self,
        mock_web_reader: Mock,
        mock_normalizer: Mock,
        mock_chunker: Mock,
        mock_embedder: Mock,
        mock_qdrant_writer: Mock,
    ) -> None:
        """Test that execute creates valid Chunk models for Qdrant."""
        from packages.core.use_cases.ingest_web import IngestWebUseCase

        use_case = IngestWebUseCase(
            web_reader=mock_web_reader,
            normalizer=mock_normalizer,
            chunker=mock_chunker,
            embedder=mock_embedder,
            qdrant_writer=mock_qdrant_writer,
            collection_name="test_collection",
        )

        job = use_case.execute(url="https://example.com", limit=5)

        # Verify upsert_batch was called with Chunk models
        mock_qdrant_writer.upsert_batch.assert_called_once()
        chunks_arg = mock_qdrant_writer.upsert_batch.call_args[0][0]
        embeddings_arg = mock_qdrant_writer.upsert_batch.call_args[0][1]

        # Verify chunks are Chunk models
        assert all(isinstance(chunk, Chunk) for chunk in chunks_arg)
        assert len(chunks_arg) == 6  # 2 docs * 3 chunks

        # Verify embeddings match chunks
        assert len(embeddings_arg) == len(chunks_arg)
        assert all(len(emb) == 768 for emb in embeddings_arg)

        # Verify chunk metadata
        for chunk in chunks_arg:
            assert isinstance(chunk.chunk_id, UUID)
            assert isinstance(chunk.doc_id, UUID)
            assert chunk.source_type == SourceType.WEB
            assert chunk.source_url == "https://example.com"
            assert chunk.position >= 0
            assert chunk.token_count > 0
