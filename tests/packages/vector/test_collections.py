"""Unit tests for Qdrant collection creation and management."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from packages.vector.collections import (
    load_collection_config,
)
from packages.vector.qdrant_client import QdrantConnectionError, QdrantVectorClient


@pytest.fixture
def collection_config(collection_config_path: Path) -> dict[str, Any]:
    """Load collection configuration from JSON file."""

    with collection_config_path.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.unit
class TestCollectionCreation:
    """Test suite for Qdrant collection creation functionality."""

    @pytest.fixture
    def mock_qdrant_client(self) -> Mock:
        """Create a mock Qdrant client."""
        return Mock()

    @pytest.fixture
    def client(self, mock_qdrant_client: Mock) -> QdrantVectorClient:
        """Create QdrantVectorClient with mocked dependencies."""
        with patch("packages.vector.qdrant_client.QdrantClient", return_value=mock_qdrant_client):
            return QdrantVectorClient(
                url="http://localhost:6333",
                collection_name="documents",
                embedding_dim=1024,
            )

    def test_collection_config_loads_correctly(self, collection_config_path: Path) -> None:
        """Test that collection configuration JSON loads correctly."""
        # This will fail if implementation doesn't exist yet (RED phase)
        assert collection_config_path.exists(), "Collection config JSON must exist"

        with collection_config_path.open(encoding="utf-8") as f:
            config = json.load(f)

        # Verify structure matches spec
        assert config["collection_name"] == "documents"
        assert config["vectors"]["size"] == 1024
        assert config["vectors"]["distance"] == "Cosine"
        assert config["vectors"]["on_disk"] is False
        assert config["hnsw_config"]["m"] == 16
        assert config["hnsw_config"]["ef_construct"] == 200

    def test_create_collection_with_correct_parameters(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
        collection_config: dict[str, Any],
    ) -> None:
        """Test that collection is created with correct parameters from config."""
        # Mock successful creation
        mock_qdrant_client.create_collection.return_value = True

        # Create collection
        client.create_collection()

        # Verify create_collection was called
        mock_qdrant_client.create_collection.assert_called_once()
        call_args = mock_qdrant_client.create_collection.call_args

        # Verify collection name
        assert call_args[1]["collection_name"] == collection_config["collection_name"]

        # Verify vectors config matches JSON spec
        vectors_config = call_args[1]["vectors_config"]
        assert isinstance(vectors_config, models.VectorParams)
        assert vectors_config.size == collection_config["vectors"]["size"]
        assert vectors_config.distance == models.Distance.COSINE
        assert vectors_config.on_disk == collection_config["vectors"]["on_disk"]

        # Verify HNSW config matches JSON spec
        hnsw_config = call_args[1]["hnsw_config"]
        assert isinstance(hnsw_config, models.HnswConfigDiff)
        assert hnsw_config.m == collection_config["hnsw_config"]["m"]
        assert hnsw_config.ef_construct == collection_config["hnsw_config"]["ef_construct"]
        assert (
            hnsw_config.full_scan_threshold
            == collection_config["hnsw_config"]["full_scan_threshold"]
        )
        assert hnsw_config.on_disk == collection_config["hnsw_config"]["on_disk"]

        # Verify optimizers config matches JSON spec
        optimizers_config = call_args[1]["optimizers_config"]
        assert isinstance(optimizers_config, models.OptimizersConfigDiff)
        assert (
            optimizers_config.deleted_threshold
            == collection_config["optimizers_config"]["deleted_threshold"]
        )
        assert (
            optimizers_config.vacuum_min_vector_number
            == collection_config["optimizers_config"]["vacuum_min_vector_number"]
        )
        assert (
            optimizers_config.indexing_threshold
            == collection_config["optimizers_config"]["indexing_threshold"]
        )
        assert (
            optimizers_config.flush_interval_sec
            == collection_config["optimizers_config"]["flush_interval_sec"]
        )
        assert (
            optimizers_config.max_optimization_threads
            == collection_config["optimizers_config"]["max_optimization_threads"]
        )

        # Verify WAL config matches JSON spec
        wal_config = call_args[1]["wal_config"]
        assert isinstance(wal_config, models.WalConfigDiff)
        assert wal_config.wal_capacity_mb == collection_config["wal_config"]["wal_capacity_mb"]
        assert (
            wal_config.wal_segments_ahead == collection_config["wal_config"]["wal_segments_ahead"]
        )

    def test_create_collection_error_handling_on_failure(
        self, client: QdrantVectorClient, mock_qdrant_client: Mock
    ) -> None:
        """Test error handling when collection creation fails."""
        # Mock a generic error (not 409 conflict)
        error_msg = "Internal server error"
        mock_qdrant_client.create_collection.side_effect = UnexpectedResponse(
            status_code=500,
            reason_phrase="Internal Server Error",
            content=error_msg.encode(),
            headers={},
        )

        # Should raise QdrantConnectionError
        with pytest.raises(QdrantConnectionError, match="Failed to create collection"):
            client.create_collection()

        mock_qdrant_client.create_collection.assert_called_once()

    def test_create_collection_error_handling_on_network_failure(
        self, client: QdrantVectorClient, mock_qdrant_client: Mock
    ) -> None:
        """Test error handling when network connection fails."""
        # Mock a network error
        mock_qdrant_client.create_collection.side_effect = Exception("Connection refused")

        # Should raise QdrantConnectionError
        with pytest.raises(QdrantConnectionError, match="Failed to create collection"):
            client.create_collection()

        mock_qdrant_client.create_collection.assert_called_once()

    def test_create_collection_is_idempotent(
        self, client: QdrantVectorClient, mock_qdrant_client: Mock
    ) -> None:
        """Test that collection creation is idempotent (skips if exists)."""
        # Mock 409 Conflict error (collection already exists)
        mock_qdrant_client.create_collection.side_effect = UnexpectedResponse(
            status_code=409,
            reason_phrase="Conflict",
            content=b"Collection already exists",
            headers={},
        )

        # Should NOT raise error, just log warning
        client.create_collection()

        # Verify create_collection was called
        mock_qdrant_client.create_collection.assert_called_once()

    def test_create_collection_multiple_times_is_safe(
        self, client: QdrantVectorClient, mock_qdrant_client: Mock
    ) -> None:
        """Test that calling create_collection multiple times is safe."""
        # First call succeeds
        mock_qdrant_client.create_collection.return_value = True

        # First creation
        client.create_collection()

        # Second call gets 409 conflict
        mock_qdrant_client.create_collection.side_effect = UnexpectedResponse(
            status_code=409,
            reason_phrase="Conflict",
            content=b"Collection already exists",
            headers={},
        )

        # Second creation should not raise error
        client.create_collection()

        # Verify create_collection was called twice
        assert mock_qdrant_client.create_collection.call_count == 2


@pytest.mark.unit
class TestCollectionConfiguration:
    """Test suite for collection configuration validation."""

    def test_config_has_required_fields(self, collection_config_path: Path) -> None:
        """Test that collection config has all required fields."""
        with collection_config_path.open(encoding="utf-8") as f:
            config = json.load(f)

        # Required top-level fields
        assert "collection_name" in config
        assert "vectors" in config
        assert "hnsw_config" in config
        assert "optimizers_config" in config
        assert "wal_config" in config
        assert "payload_schema" in config

    def test_config_vectors_schema(self, collection_config_path: Path) -> None:
        """Test vectors configuration schema."""
        with collection_config_path.open(encoding="utf-8") as f:
            config = json.load(f)

        vectors = config["vectors"]
        assert vectors["size"] == 1024, "Must use Qwen3-Embedding-0.6B (1024-dim)"
        assert vectors["distance"] == "Cosine", "Must use cosine distance"
        assert isinstance(vectors["on_disk"], bool)

    def test_config_hnsw_schema(self, collection_config_path: Path) -> None:
        """Test HNSW configuration schema."""
        with collection_config_path.open(encoding="utf-8") as f:
            config = json.load(f)

        hnsw = config["hnsw_config"]
        assert hnsw["m"] == 16, "HNSW M parameter must be 16"
        assert hnsw["ef_construct"] == 200, "HNSW ef_construct must be 200"
        assert hnsw["full_scan_threshold"] == 10000
        assert isinstance(hnsw["on_disk"], bool)

    def test_config_payload_schema_has_required_fields(self, collection_config_path: Path) -> None:
        """Test payload schema has required metadata fields."""
        with collection_config_path.open(encoding="utf-8") as f:
            config = json.load(f)

        payload = config["payload_schema"]

        # Required fields for filtering
        required_fields = [
            "chunk_id",
            "doc_id",
            "source_url",
            "source_type",
            "section",
            "ingested_at",
            "tags",
        ]
        for field in required_fields:
            assert field in payload, f"Payload schema must include {field}"
            assert "type" in payload[field]
            assert "index" in payload[field]

    def test_config_performance_targets(self, collection_config_path: Path) -> None:
        """Test that config includes performance targets."""
        with collection_config_path.open(encoding="utf-8") as f:
            config = json.load(f)

        assert "expected_performance" in config
        perf = config["expected_performance"]
        assert "upsert_throughput" in perf
        assert "search_latency_p95" in perf
        assert "memory_usage" in perf

    def test_loader_normalizes_distance_enum(self) -> None:
        """load_collection_config normalises distance to an enum-friendly value."""

        config = load_collection_config()
        assert config["vectors"]["distance"] == "COSINE"
