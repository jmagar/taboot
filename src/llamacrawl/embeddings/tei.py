"""TEI (Text Embeddings Inference) embedding integration for LlamaIndex.

This module provides a custom embedding class that integrates HuggingFace's
Text Embeddings Inference (TEI) service with LlamaIndex. The implementation
extends BaseEmbedding to call the TEI HTTP API for generating embeddings.

The TEI service is deployed via Docker and serves the Qwen3-Embedding-0.6B model,
which outputs 1024-dimensional vectors with last-token pooling.
"""

from typing import Any

import httpx
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.bridge.pydantic import PrivateAttr

from llamacrawl.utils.logging import get_logger
from llamacrawl.utils.retry import async_retry_with_backoff, retry_with_backoff

logger = get_logger(__name__)


class TEIEmbedding(BaseEmbedding):
    """Custom embedding class for HuggingFace Text Embeddings Inference (TEI).

    This class integrates with a self-hosted TEI service to generate embeddings
    using the Qwen3-Embedding-0.6B model (1024 dimensions, last-token pooling).

    The TEI API endpoint is called via HTTP POST to /embed with batch support.
    Implements retry logic for transient failures and proper error handling.

    Attributes:
        model_name: Model identifier for tracking (default: "Qwen3-Embedding-0.6B")
        embed_batch_size: Batch size for encoding (default: 128, max supported by TEI)

    Example:
        >>> from llamacrawl.config import get_config
        >>> config = get_config()
        >>> embed_model = TEIEmbedding(
        ...     base_url=config.tei_embedding_url,
        ...     model_name="Qwen3-Embedding-0.6B",
        ...     embed_batch_size=128
        ... )
        >>> embedding = embed_model.get_text_embedding("What is machine learning?")
        >>> len(embedding)
        1024
    """

    _base_url: str = PrivateAttr()
    _timeout: float = PrivateAttr()
    _truncate: bool = PrivateAttr()
    _normalize: bool = PrivateAttr()

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        model_name: str = "Qwen3-Embedding-0.6B",
        embed_batch_size: int = 128,
        timeout: float = 30.0,
        truncate: bool = True,
        normalize: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize TEI embedding client.

        Args:
            base_url: TEI service endpoint URL (default: http://localhost:8080)
            model_name: Model name for tracking (default: Qwen3-Embedding-0.6B)
            embed_batch_size: Batch size for encoding (default: 128, TEI max)
            timeout: Request timeout in seconds (default: 30.0)
            truncate: Whether to truncate long texts to model max length (default: True)
            normalize: Whether to L2 normalize embeddings (default: True)
            **kwargs: Additional arguments passed to BaseEmbedding

        Note:
            - embed_batch_size should match TEI --max-client-batch-size (128)
            - Qwen3-Embedding-0.6B outputs 1024-dimensional vectors
            - TEI uses last-token pooling for this model
        """
        super().__init__(
            model_name=model_name,
            embed_batch_size=embed_batch_size,
            **kwargs,
        )
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._truncate = truncate
        self._normalize = normalize

        logger.info(
            "Initialized TEI embedding client",
            extra={
                "base_url": self._base_url,
                "model_name": model_name,
                "embed_batch_size": embed_batch_size,
                "timeout": timeout,
            },
        )

    @classmethod
    def class_name(cls) -> str:
        """Return class name for serialization.

        Returns:
            Class name string for LlamaIndex serialization
        """
        return "TEIEmbedding"

    @retry_with_backoff(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        exceptions=(httpx.HTTPError, httpx.TimeoutException, ConnectionError),
    )
    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Internal method to get embeddings from TEI service (synchronous).

        Makes a POST request to the TEI /embed endpoint with a batch of texts.
        Handles errors and retries transient failures automatically.

        Args:
            texts: List of texts to embed (max 128 per batch)

        Returns:
            List of embeddings, one per input text (1024-dim vectors)

        Raises:
            RuntimeError: If TEI request fails after retries
            httpx.HTTPError: If HTTP error occurs
            httpx.TimeoutException: If request times out

        Note:
            - TEI returns embeddings in same order as inputs
            - Batch size should not exceed TEI --max-client-batch-size
        """
        url = f"{self._base_url}/embed"
        headers = {"Content-Type": "application/json"}
        payload = {
            "inputs": texts,
            "truncate": self._truncate,
            "normalize": self._normalize,
        }

        logger.debug(
            "Requesting embeddings from TEI",
            extra={
                "url": url,
                "num_texts": len(texts),
                "truncate": self._truncate,
                "normalize": self._normalize,
            },
        )

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                embeddings: list[list[float]] = response.json()

                logger.debug(
                    "Successfully received embeddings from TEI",
                    extra={
                        "num_embeddings": len(embeddings),
                        "embedding_dim": len(embeddings[0]) if embeddings else 0,
                    },
                )

                return embeddings

        except httpx.HTTPStatusError as e:
            logger.error(
                "TEI embedding request failed with HTTP error",
                extra={
                    "url": url,
                    "status_code": e.response.status_code,
                    "error": str(e),
                    "num_texts": len(texts),
                },
            )
            raise RuntimeError(
                f"TEI embedding request failed: HTTP {e.response.status_code}"
            ) from e

        except httpx.TimeoutException as e:
            logger.error(
                "TEI embedding request timed out",
                extra={
                    "url": url,
                    "timeout": self._timeout,
                    "num_texts": len(texts),
                },
            )
            raise RuntimeError(f"TEI embedding request timed out after {self._timeout}s") from e

        except httpx.HTTPError as e:
            logger.error(
                "TEI embedding request failed",
                extra={
                    "url": url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "num_texts": len(texts),
                },
            )
            raise RuntimeError(f"TEI embedding request failed: {str(e)}") from e

    @async_retry_with_backoff(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        exceptions=(httpx.HTTPError, httpx.TimeoutException, ConnectionError),
    )
    async def _aembed_texts(self, texts: list[str]) -> list[list[float]]:
        """Internal method to get embeddings from TEI service (asynchronous).

        Makes an async POST request to the TEI /embed endpoint with a batch of texts.
        Handles errors and retries transient failures automatically.

        Args:
            texts: List of texts to embed (max 128 per batch)

        Returns:
            List of embeddings, one per input text (1024-dim vectors)

        Raises:
            RuntimeError: If TEI request fails after retries
            httpx.HTTPError: If HTTP error occurs
            httpx.TimeoutException: If request times out

        Note:
            - TEI returns embeddings in same order as inputs
            - Batch size should not exceed TEI --max-client-batch-size
        """
        url = f"{self._base_url}/embed"
        headers = {"Content-Type": "application/json"}
        payload = {
            "inputs": texts,
            "truncate": self._truncate,
            "normalize": self._normalize,
        }

        logger.debug(
            "Requesting embeddings from TEI (async)",
            extra={
                "url": url,
                "num_texts": len(texts),
                "truncate": self._truncate,
                "normalize": self._normalize,
            },
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                embeddings: list[list[float]] = response.json()

                logger.debug(
                    "Successfully received embeddings from TEI (async)",
                    extra={
                        "num_embeddings": len(embeddings),
                        "embedding_dim": len(embeddings[0]) if embeddings else 0,
                    },
                )

                return embeddings

        except httpx.HTTPStatusError as e:
            logger.error(
                "TEI embedding request failed with HTTP error (async)",
                extra={
                    "url": url,
                    "status_code": e.response.status_code,
                    "error": str(e),
                    "num_texts": len(texts),
                },
            )
            raise RuntimeError(
                f"TEI embedding request failed: HTTP {e.response.status_code}"
            ) from e

        except httpx.TimeoutException as e:
            logger.error(
                "TEI embedding request timed out (async)",
                extra={
                    "url": url,
                    "timeout": self._timeout,
                    "num_texts": len(texts),
                },
            )
            raise RuntimeError(f"TEI embedding request timed out after {self._timeout}s") from e

        except httpx.HTTPError as e:
            logger.error(
                "TEI embedding request failed (async)",
                extra={
                    "url": url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "num_texts": len(texts),
                },
            )
            raise RuntimeError(f"TEI embedding request failed: {str(e)}") from e

    def _get_query_embedding(self, query: str) -> list[float]:
        """Get embedding for a single query (synchronous).

        This method is called by LlamaIndex to embed query strings.

        Args:
            query: Query text to embed

        Returns:
            Embedding vector (1024-dim for Qwen3-Embedding-0.6B)

        Note:
            Internally calls _embed_texts with a single-item list
        """
        embeddings = self._embed_texts([query])
        return embeddings[0]

    def _get_text_embedding(self, text: str) -> list[float]:
        """Get embedding for a single text (synchronous).

        This method is called by LlamaIndex to embed document chunks.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1024-dim for Qwen3-Embedding-0.6B)

        Note:
            Internally calls _embed_texts with a single-item list
        """
        embeddings = self._embed_texts([text])
        return embeddings[0]

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts in batch (synchronous).

        This method is called by LlamaIndex for batch embedding operations.
        Uses the TEI batch endpoint for efficiency.

        Args:
            texts: List of texts to embed (recommended max 128 per call)

        Returns:
            List of embedding vectors, one per input text

        Note:
            - TEI supports up to 128 texts per batch (--max-client-batch-size)
            - Batch embedding is 10x faster than individual calls
            - For >128 texts, LlamaIndex will automatically split into batches
        """
        return self._embed_texts(texts)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        """Get embedding for a single query (asynchronous).

        This method is called by LlamaIndex to embed query strings asynchronously.

        Args:
            query: Query text to embed

        Returns:
            Embedding vector (1024-dim for Qwen3-Embedding-0.6B)

        Note:
            Internally calls _aembed_texts with a single-item list
        """
        embeddings = await self._aembed_texts([query])
        return embeddings[0]

    async def _aget_text_embedding(self, text: str) -> list[float]:
        """Get embedding for a single text (asynchronous).

        This method is called by LlamaIndex to embed document chunks asynchronously.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1024-dim for Qwen3-Embedding-0.6B)

        Note:
            Internally calls _aembed_texts with a single-item list
        """
        embeddings = await self._aembed_texts([text])
        return embeddings[0]


# Export public API
__all__ = ["TEIEmbedding"]
