"""Document embedder using TEI (Text Embeddings Inference).

Implements batch embedding with TEI service.
Per data-model.md: Use Qwen3-Embedding-0.6B (1024-dim vectors).
Per .env: TEI service at http://taboot-embed:80
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EmbedderError(Exception):
    """Base exception for Embedder errors."""

    pass


class Embedder:
    """Document embedder using TEI service.

    Implements batch embedding with configurable batch size and dimension validation.
    """

    def __init__(
        self,
        tei_url: str,
        batch_size: int = 32,
        expected_dim: int = 1024,
        timeout: float = 30.0,
    ) -> None:
        """Initialize Embedder with TEI service URL.

        Args:
            tei_url: URL of TEI service (e.g., http://taboot-embed:80).
            batch_size: Number of texts to embed in each batch (default: 32).
            expected_dim: Expected embedding dimension (default: 1024 for Qwen3-Embedding-0.6B).
            timeout: HTTP request timeout in seconds (default: 30.0).

        Raises:
            ValueError: If tei_url is empty or batch_size is invalid.
        """
        if not tei_url:
            raise ValueError("tei_url cannot be empty")

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        if expected_dim <= 0:
            raise ValueError("expected_dim must be positive")

        self.tei_url = tei_url
        self.batch_size = batch_size
        self.expected_dim = expected_dim
        self.timeout = timeout

        # Initialize HTTP client
        self._client = httpx.Client(timeout=timeout)

        logger.info(
            f"Initialized Embedder (tei_url={tei_url}, "
            f"batch_size={batch_size}, expected_dim={expected_dim})"
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts using TEI service.

        Args:
            texts: List of text strings to embed.

        Returns:
            list[list[float]]: List of embedding vectors (each of length expected_dim).

        Raises:
            EmbedderError: If TEI service returns an error or invalid response.
        """
        if not texts:
            logger.debug("Empty text list, returning empty result")
            return []

        logger.debug(f"Embedding {len(texts)} texts")

        all_embeddings: list[list[float]] = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_embeddings = self._embed_batch(batch)
            all_embeddings.extend(batch_embeddings)

        logger.info(f"Embedded {len(all_embeddings)} texts")

        return all_embeddings

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        """Embed a single batch of texts.

        Args:
            batch: List of text strings (size <= batch_size).

        Returns:
            list[list[float]]: List of embedding vectors.

        Raises:
            EmbedderError: If TEI service returns an error or invalid response.
        """
        logger.debug(f"Embedding batch of {len(batch)} texts")

        try:
            # TEI expects JSON payload with "inputs" field
            payload = {"inputs": batch}

            response = self._client.post(
                f"{self.tei_url}/embed",
                json=payload,
            )

            response.raise_for_status()

            embeddings = response.json()

            # Validate response format
            if not isinstance(embeddings, list):
                raise EmbedderError(
                    f"Invalid response format: expected list, got {type(embeddings)}"
                )

            if len(embeddings) != len(batch):
                raise EmbedderError(
                    f"Response length mismatch: expected {len(batch)}, got {len(embeddings)}"
                )

            # Validate dimensions
            for i, embedding in enumerate(embeddings):
                if not isinstance(embedding, list):
                    raise EmbedderError(
                        f"Invalid embedding format at index {i}: "
                        f"expected list, got {type(embedding)}"
                    )

                if len(embedding) != self.expected_dim:
                    raise EmbedderError(
                        f"Invalid embedding dimension at index {i}: "
                        f"Expected {self.expected_dim} dimensions, got {len(embedding)}"
                    )

            logger.debug(f"Successfully embedded batch of {len(batch)} texts")

            return embeddings

        except httpx.HTTPStatusError as e:
            logger.error(f"TEI service HTTP error: {e}")
            raise EmbedderError(f"TEI service HTTP error: {e}") from e

        except httpx.RequestError as e:
            logger.error(f"TEI service request error: {e}")
            raise EmbedderError(f"TEI service request error: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error during embedding: {e}")
            raise EmbedderError(f"Unexpected error during embedding: {e}") from e

    def close(self) -> None:
        """Close the HTTP client."""
        logger.debug("Closing HTTP client")
        self._client.close()

    def __enter__(self) -> "Embedder":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and close HTTP client."""
        self.close()


def get_embedding(text: str, tei_url: str = "http://taboot-embed:80") -> list[float]:
    """
    Get embedding for a single text string.

    Args:
        text: Text to embed
        tei_url: TEI service URL

    Returns:
        Embedding vector (1024-dim)
    """
    embedder = Embedder(tei_url=tei_url)
    try:
        embeddings = embedder.embed_texts([text])
        return embeddings[0]
    finally:
        embedder.close()
