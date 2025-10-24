"""Unit tests for Qdrant writer."""

import uuid
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from qdrant_client import QdrantClient
from qdrant_client.http import models

from packages.schemas.models import Chunk, SourceType
from packages.vector.writer import QdrantWriteError, QdrantWriter


class TestQdrantWriter:
    """Test suite for QdrantWriter."""

    @pytest.fixture
    def mock_qdrant_client(self) -> Mock:
        """Create a mock Qdrant client."""
        return Mock(spec=QdrantClient)

    @pytest.fixture
    def writer(self, mock_qdrant_client: Mock) -> QdrantWriter:
        """Create QdrantWriter with mocked dependencies."""
        with patch("packages.vector.writer.QdrantClient", return_value=mock_qdrant_client):
            return QdrantWriter(
                url="http://localhost:6333",
                collection_name="documents",
                batch_size=100,
            )

    @pytest.fixture
    def sample_chunk(self) -> Chunk:
        """Create a sample Chunk for testing."""
        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        ingested_at = datetime.now(UTC)

        return Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            content="This is a test chunk about kubernetes networking.",
            section="Installation > Prerequisites",
            position=0,
            token_count=50,
            source_url="https://example.com/docs/kubernetes",
            source_type=SourceType.WEB,
            ingested_at=int(ingested_at.timestamp()),
            tags=["kubernetes", "networking"],
        )

    def test_init_creates_writer(self, mock_qdrant_client: Mock) -> None:
        """Test writer initialization."""
        with patch("packages.vector.writer.QdrantClient", return_value=mock_qdrant_client):
            writer = QdrantWriter(
                url="http://localhost:6333",
                collection_name="documents",
                batch_size=100,
            )
            assert writer.collection_name == "documents"
            assert writer.batch_size == 100

    def test_init_validates_batch_size(self, mock_qdrant_client: Mock) -> None:
        """Test writer initialization validates batch size."""
        with patch("packages.vector.writer.QdrantClient", return_value=mock_qdrant_client):
            # Batch size must be positive
            with pytest.raises(ValueError, match="batch_size must be positive"):
                QdrantWriter(
                    url="http://localhost:6333",
                    collection_name="documents",
                    batch_size=0,
                )

            with pytest.raises(ValueError, match="batch_size must be positive"):
                QdrantWriter(
                    url="http://localhost:6333",
                    collection_name="documents",
                    batch_size=-1,
                )

    def test_upsert_single_point_with_metadata(
        self,
        writer: QdrantWriter,
        mock_qdrant_client: Mock,
        sample_chunk: Chunk,
    ) -> None:
        """Test upserting a single point with metadata."""
        # Mock embedding vector (1024-dim)
        embedding = [0.1] * 1024

        # Mock successful upsert
        mock_qdrant_client.upsert.return_value = Mock(status="completed")

        writer.upsert_single(sample_chunk, embedding)

        # Verify upsert was called once
        mock_qdrant_client.upsert.assert_called_once()
        call_args = mock_qdrant_client.upsert.call_args

        # Verify collection name
        assert call_args[1]["collection_name"] == "documents"

        # Verify points structure
        points = call_args[1]["points"]
        assert len(points) == 1
        assert isinstance(points[0], models.PointStruct)
        assert points[0].id == str(sample_chunk.chunk_id)
        assert points[0].vector == embedding

        # Verify metadata payload
        payload = points[0].payload
        assert payload is not None
        assert payload["doc_id"] == str(sample_chunk.doc_id)
        assert payload["content"] == sample_chunk.content
        assert payload["section"] == sample_chunk.section
        assert payload["position"] == sample_chunk.position
        assert payload["token_count"] == sample_chunk.token_count
        assert payload["source_url"] == sample_chunk.source_url
        assert payload["source_type"] == sample_chunk.source_type.value
        assert payload["ingested_at"] == sample_chunk.ingested_at
        assert payload["tags"] == sample_chunk.tags

    def test_upsert_batch_multiple_points(
        self,
        writer: QdrantWriter,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test batch upserting multiple points."""
        # Create batch of chunks with embeddings
        batch_size = 3
        chunks = []
        embeddings = []

        for i in range(batch_size):
            chunk = Chunk(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                content=f"Test chunk {i}",
                section=f"Section {i}",
                position=i,
                token_count=10 + i,
                source_url=f"https://example.com/doc{i}",
                source_type=SourceType.WEB,
                ingested_at=int(datetime.now(UTC).timestamp()),
                tags=[f"tag{i}"],
            )
            chunks.append(chunk)
            embeddings.append([0.1 * (i + 1)] * 1024)

        # Mock successful batch upsert
        mock_qdrant_client.upsert.return_value = Mock(status="completed")

        writer.upsert_batch(chunks, embeddings)

        # Verify upsert was called once
        mock_qdrant_client.upsert.assert_called_once()
        call_args = mock_qdrant_client.upsert.call_args

        # Verify batch of points
        points = call_args[1]["points"]
        assert len(points) == batch_size

        # Verify each point has correct structure
        for i, point in enumerate(points):
            assert isinstance(point, models.PointStruct)
            assert point.id == str(chunks[i].chunk_id)
            assert point.vector == embeddings[i]
            assert point.payload["content"] == f"Test chunk {i}"

    def test_upsert_batch_handles_empty_batch(
        self,
        writer: QdrantWriter,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test batch upsert handles empty batch gracefully."""
        # Empty batch should not call upsert
        writer.upsert_batch([], [])

        # Verify upsert was not called
        mock_qdrant_client.upsert.assert_not_called()

    def test_upsert_batch_validates_matching_lengths(
        self,
        writer: QdrantWriter,
        sample_chunk: Chunk,
    ) -> None:
        """Test batch upsert validates chunks and embeddings have same length."""
        chunks = [sample_chunk]
        embeddings = [[0.1] * 1024, [0.2] * 1024]  # Mismatched length

        with pytest.raises(ValueError, match="chunks and embeddings must have the same length"):
            writer.upsert_batch(chunks, embeddings)

    def test_upsert_batch_validates_embedding_dimensions(
        self,
        writer: QdrantWriter,
        sample_chunk: Chunk,
    ) -> None:
        """Test batch upsert validates embedding dimensions."""
        chunks = [sample_chunk]
        embeddings = [[0.1] * 512]  # Wrong dimension (should be 1024)

        with pytest.raises(ValueError, match="All embeddings must be 1024-dimensional"):
            writer.upsert_batch(chunks, embeddings)

    def test_upsert_batch_splits_large_batches(
        self,
        writer: QdrantWriter,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test batch upsert splits large batches into smaller ones."""
        # Create batch larger than batch_size
        writer.batch_size = 10  # Set small batch size
        num_chunks = 25

        chunks = []
        embeddings = []
        for i in range(num_chunks):
            chunk = Chunk(
                chunk_id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                content=f"Test chunk {i}",
                section="Section",
                position=i,
                token_count=10,
                source_url="https://example.com/doc",
                source_type=SourceType.WEB,
                ingested_at=int(datetime.now(UTC).timestamp()),
                tags=[],
            )
            chunks.append(chunk)
            embeddings.append([0.1] * 1024)

        # Mock successful upserts
        mock_qdrant_client.upsert.return_value = Mock(status="completed")

        writer.upsert_batch(chunks, embeddings)

        # Verify upsert was called 3 times (10 + 10 + 5)
        assert mock_qdrant_client.upsert.call_count == 3

        # Verify batch sizes
        call_args_list = mock_qdrant_client.upsert.call_args_list
        assert len(call_args_list[0][1]["points"]) == 10
        assert len(call_args_list[1][1]["points"]) == 10
        assert len(call_args_list[2][1]["points"]) == 5

    def test_upsert_preserves_optional_fields(
        self,
        writer: QdrantWriter,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test upsert preserves optional fields (section, tags)."""
        # Chunk with missing optional fields
        chunk = Chunk(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            content="Test chunk",
            section=None,  # Optional field missing
            position=0,
            token_count=10,
            source_url="https://example.com/doc",
            source_type=SourceType.WEB,
            ingested_at=int(datetime.now(UTC).timestamp()),
            tags=None,  # Optional field missing
        )
        embedding = [0.1] * 1024

        # Mock successful upsert
        mock_qdrant_client.upsert.return_value = Mock(status="completed")

        writer.upsert_single(chunk, embedding)

        # Verify upsert preserves None values
        call_args = mock_qdrant_client.upsert.call_args
        payload = call_args[1]["points"][0].payload
        assert payload["section"] is None
        assert payload["tags"] is None

    def test_upsert_handles_qdrant_error(
        self,
        writer: QdrantWriter,
        mock_qdrant_client: Mock,
        sample_chunk: Chunk,
    ) -> None:
        """Test upsert handles Qdrant errors properly."""
        embedding = [0.1] * 1024

        # Mock Qdrant error
        mock_qdrant_client.upsert.side_effect = Exception("Qdrant connection error")

        with pytest.raises(QdrantWriteError, match="Failed to upsert points"):
            writer.upsert_single(sample_chunk, embedding)

    def test_close(self, writer: QdrantWriter, mock_qdrant_client: Mock) -> None:
        """Test writer close."""
        mock_qdrant_client.close = Mock()

        writer.close()

        mock_qdrant_client.close.assert_called_once()
