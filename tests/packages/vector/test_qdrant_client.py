"""Unit tests for Qdrant client."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from packages.vector.qdrant_client import QdrantConnectionError, QdrantVectorClient


class TestQdrantVectorClient:
    """Test suite for QdrantVectorClient."""

    @pytest.fixture
    def mock_qdrant_client(self) -> Mock:
        """Create a mock Qdrant client."""
        return Mock(spec=QdrantClient)

    @pytest.fixture
    def client(self, mock_qdrant_client: Mock) -> QdrantVectorClient:
        """Create QdrantVectorClient with mocked dependencies."""
        with patch("packages.vector.qdrant_client.QdrantClient", return_value=mock_qdrant_client):
            return QdrantVectorClient(
                url="http://localhost:6333",
                collection_name="test_collection",
                embedding_dim=1024,
            )

    def test_init_creates_client(self, mock_qdrant_client: Mock) -> None:
        """Test client initialization."""
        with patch("packages.vector.qdrant_client.QdrantClient", return_value=mock_qdrant_client):
            client = QdrantVectorClient(
                url="http://localhost:6333",
                collection_name="test_collection",
                embedding_dim=1024,
            )
            assert client.collection_name == "test_collection"
            assert client.embedding_dim == 1024

    def test_health_check_success(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test successful health check."""
        # Mock health check response
        mock_qdrant_client.get_collections.return_value = MagicMock()

        is_healthy = client.health_check()

        assert is_healthy is True
        mock_qdrant_client.get_collections.assert_called_once()

    def test_health_check_failure(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test health check failure."""
        # Mock connection error
        mock_qdrant_client.get_collections.side_effect = Exception("Connection refused")

        is_healthy = client.health_check()

        assert is_healthy is False

    def test_collection_exists_true(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test collection existence check when collection exists."""
        # Mock collection exists
        mock_qdrant_client.collection_exists.return_value = True

        exists = client.collection_exists()

        assert exists is True
        mock_qdrant_client.collection_exists.assert_called_once_with("test_collection")

    def test_collection_exists_false(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test collection existence check when collection doesn't exist."""
        # Mock collection doesn't exist
        mock_qdrant_client.collection_exists.return_value = False

        exists = client.collection_exists()

        assert exists is False
        mock_qdrant_client.collection_exists.assert_called_once_with("test_collection")

    def test_collection_exists_error(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test collection existence check raises error on connection failure."""
        # Mock connection error
        mock_qdrant_client.collection_exists.side_effect = Exception("Connection error")

        with pytest.raises(QdrantConnectionError, match="Failed to check collection existence"):
            client.collection_exists()

    def test_create_collection_success(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test successful collection creation."""
        # Mock successful creation
        mock_qdrant_client.create_collection.return_value = True

        client.create_collection()

        # Verify create_collection was called with correct parameters
        mock_qdrant_client.create_collection.assert_called_once()
        call_args = mock_qdrant_client.create_collection.call_args
        assert call_args[1]["collection_name"] == "test_collection"
        assert isinstance(call_args[1]["vectors_config"], models.VectorParams)
        assert call_args[1]["vectors_config"].size == 1024
        assert call_args[1]["vectors_config"].distance == models.Distance.COSINE

    def test_create_collection_already_exists(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test collection creation when collection already exists."""
        # Mock collection already exists error
        mock_qdrant_client.create_collection.side_effect = UnexpectedResponse(
            status_code=409,
            reason_phrase="Conflict",
            content=b"Collection already exists",
            headers={},
        )

        # Should not raise error, just log warning
        client.create_collection()

        mock_qdrant_client.create_collection.assert_called_once()

    def test_create_collection_error(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test collection creation raises error on failure."""
        # Mock generic error
        mock_qdrant_client.create_collection.side_effect = Exception("Failed to create")

        with pytest.raises(QdrantConnectionError, match="Failed to create collection"):
            client.create_collection()

    def test_delete_collection_success(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test successful collection deletion."""
        # Mock successful deletion
        mock_qdrant_client.delete_collection.return_value = True

        client.delete_collection()

        mock_qdrant_client.delete_collection.assert_called_once_with("test_collection")

    def test_delete_collection_not_found(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test collection deletion when collection doesn't exist."""
        # Mock not found error
        mock_qdrant_client.delete_collection.side_effect = UnexpectedResponse(
            status_code=404,
            reason_phrase="Not Found",
            content=b"Collection not found",
            headers={},
        )

        # Should not raise error, just log warning
        client.delete_collection()

        mock_qdrant_client.delete_collection.assert_called_once()

    def test_delete_collection_error(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test collection deletion raises error on failure."""
        # Mock generic error
        mock_qdrant_client.delete_collection.side_effect = Exception("Failed to delete")

        with pytest.raises(QdrantConnectionError, match="Failed to delete collection"):
            client.delete_collection()

    def test_get_collection_info_success(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test successful collection info retrieval."""
        # Mock collection info
        mock_info = MagicMock()
        mock_info.status = "green"
        mock_info.vectors_count = 1000
        mock_qdrant_client.get_collection.return_value = mock_info

        info = client.get_collection_info()

        assert info is not None
        assert info.status == "green"
        assert info.vectors_count == 1000
        mock_qdrant_client.get_collection.assert_called_once_with("test_collection")

    def test_get_collection_info_not_found(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test collection info retrieval when collection doesn't exist."""
        # Mock not found error
        mock_qdrant_client.get_collection.side_effect = UnexpectedResponse(
            status_code=404,
            reason_phrase="Not Found",
            content=b"Collection not found",
            headers={},
        )

        info = client.get_collection_info()

        assert info is None

    def test_get_collection_info_error(
        self,
        client: QdrantVectorClient,
        mock_qdrant_client: Mock,
    ) -> None:
        """Test collection info retrieval raises error on failure."""
        # Mock generic error
        mock_qdrant_client.get_collection.side_effect = Exception("Failed to get info")

        with pytest.raises(QdrantConnectionError, match="Failed to get collection info"):
            client.get_collection_info()

    def test_close(self, client: QdrantVectorClient, mock_qdrant_client: Mock) -> None:
        """Test client close."""
        # Mock close
        mock_qdrant_client.close = Mock()

        client.close()

        mock_qdrant_client.close.assert_called_once()
