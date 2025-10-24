"""Qdrant writer for batched upserts with metadata.

Provides:
- Batched Qdrant point upserts with configurable batch size
- Metadata mapping from Chunk model to Qdrant payload
- Point ID generation from chunk_id
- Error handling with proper exceptions

All operations use JSON structured logging and correlation ID tracking.
"""

import uuid
from collections.abc import Sequence

from qdrant_client import QdrantClient
from qdrant_client.http import models

from packages.common.logging import get_logger
from packages.schemas.models import Chunk

logger = get_logger(__name__)


class QdrantWriteError(Exception):
    """Raised when Qdrant write operation fails."""

    pass


class QdrantWriter:
    """Writer for Qdrant vector database with batched upserts.

    Manages batched writes to Qdrant with metadata mapping and proper error handling.
    All operations include logging with batch statistics.

    Attributes:
        client: The underlying QdrantClient instance.
        collection_name: Name of the Qdrant collection.
        batch_size: Maximum points per batch (default 100).

    Example:
        >>> writer = QdrantWriter(
        ...     url="http://localhost:6333",
        ...     collection_name="documents",
        ...     batch_size=100,
        ... )
        >>> chunks = [...]  # List of Chunk objects
        >>> embeddings = [...]  # List of embedding vectors
        >>> writer.upsert_batch(chunks, embeddings)
        >>> writer.close()
    """

    def __init__(
        self,
        url: str,
        collection_name: str,
        batch_size: int = 100,
    ) -> None:
        """Initialize Qdrant writer.

        Args:
            url: Qdrant server URL (e.g., "http://localhost:6333").
            collection_name: Name of the collection to write to.
            batch_size: Maximum points per batch (must be positive).

        Raises:
            ValueError: If batch_size is not positive.
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        self.collection_name = collection_name
        self.batch_size = batch_size
        self.client = QdrantClient(url=url)

        logger.info(
            "Qdrant writer initialized",
            extra={
                "url": url,
                "collection_name": collection_name,
                "batch_size": batch_size,
            },
        )

    def upsert_single(self, chunk: Chunk, embedding: list[float]) -> None:
        """Upsert a single point with metadata.

        Args:
            chunk: Chunk object with metadata.
            embedding: Embedding vector (must be 1024-dimensional).

        Raises:
            QdrantWriteError: If upsert operation fails.
        """
        self.upsert_batch([chunk], [embedding])

    def upsert_batch(
        self,
        chunks: Sequence[Chunk],
        embeddings: Sequence[list[float]],
    ) -> None:
        """Upsert a batch of points with metadata.

        Automatically splits large batches into smaller ones based on batch_size.

        Args:
            chunks: Sequence of Chunk objects.
            embeddings: Sequence of embedding vectors (1024-dimensional each).

        Raises:
            ValueError: If chunks and embeddings have different lengths.
            ValueError: If embeddings have wrong dimensions.
            QdrantWriteError: If upsert operation fails.
        """
        # Handle empty batch
        if len(chunks) == 0:
            logger.debug("Empty batch, skipping upsert")
            return

        # Validate inputs
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        # Validate embedding dimensions (1024 for Qwen3-Embedding-0.6B)
        for i, emb in enumerate(embeddings):
            if len(emb) != 1024:
                raise ValueError(
                    f"All embeddings must be 1024-dimensional, got {len(emb)} at index {i}"
                )

        correlation_id = str(uuid.uuid4())
        total_chunks = len(chunks)

        logger.info(
            "Starting batch upsert",
            extra={
                "correlation_id": correlation_id,
                "total_chunks": total_chunks,
                "batch_size": self.batch_size,
                "collection_name": self.collection_name,
            },
        )

        # Split into batches
        num_batches = (total_chunks + self.batch_size - 1) // self.batch_size

        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_chunks)

            batch_chunks = chunks[start_idx:end_idx]
            batch_embeddings = embeddings[start_idx:end_idx]

            self._upsert_batch_internal(
                batch_chunks,
                batch_embeddings,
                correlation_id,
                batch_idx,
                num_batches,
            )

        logger.info(
            "Batch upsert completed",
            extra={
                "correlation_id": correlation_id,
                "total_chunks": total_chunks,
                "num_batches": num_batches,
            },
        )

    def _upsert_batch_internal(
        self,
        chunks: Sequence[Chunk],
        embeddings: Sequence[list[float]],
        correlation_id: str,
        batch_idx: int,
        num_batches: int,
    ) -> None:
        """Internal method to upsert a single batch.

        Args:
            chunks: Sequence of Chunk objects.
            embeddings: Sequence of embedding vectors.
            correlation_id: Correlation ID for logging.
            batch_idx: Current batch index (0-based).
            num_batches: Total number of batches.

        Raises:
            QdrantWriteError: If upsert operation fails.
        """
        # Build points
        points = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            point = models.PointStruct(
                id=str(chunk.chunk_id),
                vector=embedding,
                payload={
                    "doc_id": str(chunk.doc_id),
                    "content": chunk.content,
                    "section": chunk.section,
                    "position": chunk.position,
                    "token_count": chunk.token_count,
                    "source_url": chunk.source_url,
                    "source_type": chunk.source_type.value,
                    "ingested_at": chunk.ingested_at,
                    "tags": chunk.tags,
                },
            )
            points.append(point)

        logger.debug(
            "Upserting batch",
            extra={
                "correlation_id": correlation_id,
                "batch_idx": batch_idx + 1,
                "num_batches": num_batches,
                "batch_size": len(points),
            },
        )

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
        except Exception as e:
            logger.error(
                "Failed to upsert batch",
                extra={
                    "correlation_id": correlation_id,
                    "batch_idx": batch_idx + 1,
                    "batch_size": len(points),
                    "error": str(e),
                },
            )
            raise QdrantWriteError(
                f"Failed to upsert points to collection '{self.collection_name}': {e}"
            ) from e

        logger.debug(
            "Batch upserted successfully",
            extra={
                "correlation_id": correlation_id,
                "batch_idx": batch_idx + 1,
                "num_batches": num_batches,
                "batch_size": len(points),
            },
        )

    async def upsert_batch_async(
        self,
        chunks: Sequence[Chunk],
        embeddings: Sequence[list[float]],
    ) -> None:
        """Upsert a batch of points with metadata asynchronously.

        Automatically splits large batches into smaller ones based on batch_size.

        Args:
            chunks: Sequence of Chunk objects.
            embeddings: Sequence of embedding vectors (1024-dimensional each).

        Raises:
            ValueError: If chunks and embeddings have different lengths.
            ValueError: If embeddings have wrong dimensions.
            QdrantWriteError: If upsert operation fails.
        """
        # Handle empty batch
        if len(chunks) == 0:
            logger.debug("Empty batch, skipping upsert")
            return

        # Validate inputs
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        # Validate embedding dimensions (1024 for Qwen3-Embedding-0.6B)
        for i, emb in enumerate(embeddings):
            if len(emb) != 1024:
                raise ValueError(
                    f"All embeddings must be 1024-dimensional, got {len(emb)} at index {i}"
                )

        correlation_id = str(uuid.uuid4())
        total_chunks = len(chunks)

        logger.info(
            "Starting async batch upsert",
            extra={
                "correlation_id": correlation_id,
                "total_chunks": total_chunks,
                "batch_size": self.batch_size,
                "collection_name": self.collection_name,
            },
        )

        # Split into batches
        num_batches = (total_chunks + self.batch_size - 1) // self.batch_size

        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_chunks)

            batch_chunks = chunks[start_idx:end_idx]
            batch_embeddings = embeddings[start_idx:end_idx]

            await self._upsert_batch_internal_async(
                batch_chunks,
                batch_embeddings,
                correlation_id,
                batch_idx,
                num_batches,
            )

        logger.info(
            "Async batch upsert completed",
            extra={
                "correlation_id": correlation_id,
                "total_chunks": total_chunks,
                "num_batches": num_batches,
            },
        )

    async def _upsert_batch_internal_async(
        self,
        chunks: Sequence[Chunk],
        embeddings: Sequence[list[float]],
        correlation_id: str,
        batch_idx: int,
        num_batches: int,
    ) -> None:
        """Internal method to upsert a single batch asynchronously.

        Args:
            chunks: Sequence of Chunk objects.
            embeddings: Sequence of embedding vectors.
            correlation_id: Correlation ID for logging.
            batch_idx: Current batch index (0-based).
            num_batches: Total number of batches.

        Raises:
            QdrantWriteError: If upsert operation fails.
        """
        # Build points
        points = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            point = models.PointStruct(
                id=str(chunk.chunk_id),
                vector=embedding,
                payload={
                    "doc_id": str(chunk.doc_id),
                    "content": chunk.content,
                    "section": chunk.section,
                    "position": chunk.position,
                    "token_count": chunk.token_count,
                    "source_url": chunk.source_url,
                    "source_type": chunk.source_type.value,
                    "ingested_at": chunk.ingested_at,
                    "tags": chunk.tags,
                },
            )
            points.append(point)

        logger.debug(
            "Upserting batch asynchronously",
            extra={
                "correlation_id": correlation_id,
                "batch_idx": batch_idx + 1,
                "num_batches": num_batches,
                "batch_size": len(points),
            },
        )

        try:
            # Note: Qdrant client's upsert is synchronous, but we wrap it in async context
            # For true async, we'd need AsyncQdrantClient, but that requires more refactoring
            # This is acceptable as the network I/O is still non-blocking via httpx
            import asyncio

            await asyncio.to_thread(
                self.client.upsert,
                collection_name=self.collection_name,
                points=points,
            )
        except Exception as e:
            logger.error(
                "Failed to upsert batch asynchronously",
                extra={
                    "correlation_id": correlation_id,
                    "batch_idx": batch_idx + 1,
                    "batch_size": len(points),
                    "error": str(e),
                },
            )
            raise QdrantWriteError(
                f"Failed to upsert points to collection '{self.collection_name}': {e}"
            ) from e

        logger.debug(
            "Batch upserted successfully (async)",
            extra={
                "correlation_id": correlation_id,
                "batch_idx": batch_idx + 1,
                "num_batches": num_batches,
                "batch_size": len(points),
            },
        )

    def close(self) -> None:
        """Close Qdrant client connection.

        Should be called when writer is no longer needed to free resources.

        Example:
            >>> writer = QdrantWriter(url="http://localhost:6333", collection_name="docs")
            >>> try:
            ...     # Use writer
            ...     pass
            ... finally:
            ...     writer.close()
        """
        try:
            self.client.close()
            logger.debug("Qdrant writer closed", extra={"collection_name": self.collection_name})
        except Exception as e:
            logger.warning("Error closing Qdrant writer", extra={"error": str(e)})


# Export public API
__all__ = ["QdrantWriter", "QdrantWriteError"]
