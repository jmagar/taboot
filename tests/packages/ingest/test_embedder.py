"""Tests for document embedder using TEI.

Tests batch embedding using Text Embeddings Inference (TEI) service.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from unittest.mock import Mock, patch
import httpx


class TestEmbedder:
    """Tests for the Embedder class."""

    def test_embedder_embeds_single_text(self) -> None:
        """Test that Embedder can embed a single text."""
        from packages.ingest.embedder import Embedder

        embedder = Embedder(tei_url="http://taboot-embed:80")

        # Mock the HTTP client to return a valid response
        with patch.object(embedder, '_client') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = [[0.1] * 1024]  # 1024-dim vector
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            result = embedder.embed_texts(["Hello world"])

            assert len(result) == 1
            assert len(result[0]) == 1024
            assert isinstance(result[0], list)
            assert all(isinstance(x, float) for x in result[0])

    def test_embedder_embeds_batch(self) -> None:
        """Test that Embedder can embed multiple texts in batch."""
        from packages.ingest.embedder import Embedder

        embedder = Embedder(tei_url="http://taboot-embed:80", batch_size=32)

        texts = [f"Document {i}" for i in range(10)]

        with patch.object(embedder, '_client') as mock_client:
            mock_response = Mock()
            # Return 10 vectors of 1024 dimensions each
            mock_response.json.return_value = [[0.1] * 1024 for _ in range(10)]
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            result = embedder.embed_texts(texts)

            assert len(result) == 10
            assert all(len(vec) == 1024 for vec in result)

    def test_embedder_returns_1024_dim_vectors(self) -> None:
        """Test that Embedder returns exactly 1024-dimensional vectors (Qwen3-Embedding-0.6B)."""
        from packages.ingest.embedder import Embedder

        embedder = Embedder(tei_url="http://taboot-embed:80")

        with patch.object(embedder, '_client') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = [[0.1] * 1024]
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            result = embedder.embed_texts(["Test text"])

            assert len(result[0]) == 1024

    def test_embedder_handles_empty_input(self) -> None:
        """Test that Embedder handles empty input list."""
        from packages.ingest.embedder import Embedder

        embedder = Embedder(tei_url="http://taboot-embed:80")
        result = embedder.embed_texts([])

        assert result == []

    def test_embedder_configurable_batch_size(self) -> None:
        """Test that Embedder respects configurable batch_size parameter."""
        from packages.ingest.embedder import Embedder

        embedder = Embedder(tei_url="http://taboot-embed:80", batch_size=16)
        assert embedder.batch_size == 16

        embedder_large = Embedder(tei_url="http://taboot-embed:80", batch_size=64)
        assert embedder_large.batch_size == 64

    def test_embedder_uses_tei_url_from_config(self) -> None:
        """Test that Embedder uses TEI service URL from configuration."""
        from packages.ingest.embedder import Embedder

        custom_url = "http://custom-embed:8080"
        embedder = Embedder(tei_url=custom_url)

        assert embedder.tei_url == custom_url

    def test_embedder_batches_large_input(self) -> None:
        """Test that Embedder processes large input in batches."""
        from packages.ingest.embedder import Embedder

        embedder = Embedder(tei_url="http://taboot-embed:80", batch_size=8)

        # Create 20 texts (should be split into 3 batches: 8, 8, 4)
        texts = [f"Text {i}" for i in range(20)]

        with patch.object(embedder, '_client') as mock_client:
            mock_response = Mock()
            # Mock will be called multiple times for batches
            mock_response.json.side_effect = [
                [[0.1] * 1024 for _ in range(8)],  # First batch
                [[0.2] * 1024 for _ in range(8)],  # Second batch
                [[0.3] * 1024 for _ in range(4)],  # Third batch
            ]
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            result = embedder.embed_texts(texts)

            assert len(result) == 20
            assert mock_client.post.call_count == 3

    def test_embedder_handles_http_error(self) -> None:
        """Test that Embedder raises error when TEI service returns HTTP error."""
        from packages.ingest.embedder import Embedder, EmbedderError

        embedder = Embedder(tei_url="http://taboot-embed:80")

        with patch.object(embedder, '_client') as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Server Error", request=Mock(), response=Mock()
            )
            mock_client.post.return_value = mock_response

            with pytest.raises(EmbedderError):
                embedder.embed_texts(["Test"])

    def test_embedder_validates_vector_dimensions(self) -> None:
        """Test that Embedder validates returned vector dimensions."""
        from packages.ingest.embedder import Embedder, EmbedderError

        embedder = Embedder(tei_url="http://taboot-embed:80")

        with patch.object(embedder, '_client') as mock_client:
            mock_response = Mock()
            # Return wrong dimension (768 instead of 1024)
            mock_response.json.return_value = [[0.1] * 768]
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            with pytest.raises(EmbedderError, match="Expected 1024 dimensions"):
                embedder.embed_texts(["Test"])

    def test_embedder_closes_client(self) -> None:
        """Test that Embedder properly closes HTTP client."""
        from packages.ingest.embedder import Embedder

        embedder = Embedder(tei_url="http://taboot-embed:80")

        with patch.object(embedder, '_client') as mock_client:
            embedder.close()
            mock_client.close.assert_called_once()

    def test_embedder_context_manager(self) -> None:
        """Test that Embedder works as a context manager."""
        from packages.ingest.embedder import Embedder

        with Embedder(tei_url="http://taboot-embed:80") as embedder:
            with patch.object(embedder, '_client') as mock_client:
                mock_response = Mock()
                mock_response.json.return_value = [[0.1] * 1024]
                mock_response.raise_for_status = Mock()
                mock_client.post.return_value = mock_response

                result = embedder.embed_texts(["Test"])
                assert len(result) == 1
