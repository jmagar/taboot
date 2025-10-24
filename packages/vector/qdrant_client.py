"""Qdrant client for vector storage and collection management.

Provides:
- Qdrant client initialization and connection pooling
- Collection management (create, delete, check existence)
- Connection health checks
- Error handling with proper exceptions

All operations use JSON structured logging and correlation ID tracking.
"""

from types import TracebackType

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import CollectionInfo

from packages.common.logging import get_logger
from packages.vector.collections import create_collection as create_from_contract

logger = get_logger(__name__)


class QdrantConnectionError(Exception):
    """Raised when Qdrant connection or operation fails."""

    ...


class QdrantVectorClient:
    """Client for Qdrant vector database operations.

    Manages connection to Qdrant and provides collection management operations.
    All operations include proper error handling and logging.

    Attributes:
        client: The underlying QdrantClient instance.
        collection_name: Name of the Qdrant collection.
        embedding_dim: Dimension of embedding vectors (default 1024 for Qwen3-Embedding-0.6B).

    Example:
        >>> client = QdrantVectorClient(
        ...     url="http://localhost:6333",
        ...     collection_name="documents",
        ...     embedding_dim=1024,
        ... )
        >>> if not client.collection_exists():
        ...     client.create_collection()
        >>> client.close()
    """

    def __init__(
        self,
        url: str,
        collection_name: str,
        embedding_dim: int = 1024,
    ) -> None:
        """Initialize Qdrant client.

        Args:
            url: Qdrant server URL (e.g., "http://localhost:6333").
            collection_name: Name of the collection to manage.
            embedding_dim: Dimension of embedding vectors (default 1024).

        Raises:
            QdrantConnectionError: If connection to Qdrant fails.
        """
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        try:
            self.client = QdrantClient(url=url)
            logger.info(
                "Qdrant client initialized",
                extra={
                    "url": url,
                    "collection_name": collection_name,
                    "embedding_dim": embedding_dim,
                },
            )
        except Exception as e:
            logger.exception(
                "Failed to initialize Qdrant client",
                extra={"url": url},
            )
            raise QdrantConnectionError(f"Failed to connect to Qdrant at {url}: {e}") from e

    def health_check(self) -> bool:
        """Check if Qdrant server is healthy and responsive.

        Returns:
            bool: True if server is healthy, False otherwise.

        Example:
            >>> client = QdrantVectorClient(url="http://localhost:6333", collection_name="docs")
            >>> if client.health_check():
            ...     print("Qdrant is healthy")
        """
        try:
            self.client.get_collections()
            logger.debug("Qdrant health check passed")
            return True
        except Exception:
            logger.exception("Qdrant health check failed")
            return False

    def collection_exists(self) -> bool:
        """Check if collection exists in Qdrant.

        Returns:
            bool: True if collection exists, False otherwise.

        Raises:
            QdrantConnectionError: If check fails due to connection issues.

        Example:
            >>> client = QdrantVectorClient(url="http://localhost:6333", collection_name="docs")
            >>> if client.collection_exists():
            ...     print("Collection exists")
        """
        try:
            exists = self.client.collection_exists(self.collection_name)
            logger.debug(
                "Collection existence check",
                extra={"collection_name": self.collection_name, "exists": exists},
            )
            return exists
        except Exception as e:
            logger.exception(
                "Failed to check collection existence",
                extra={"collection_name": self.collection_name},
            )
            raise QdrantConnectionError(f"Failed to check collection existence: {e}") from e

    def create_collection(self) -> None:
        """Create collection with HNSW indexing configuration.

        Creates collection with configuration from:
        specs/001-taboot-rag-platform/contracts/qdrant-collection.json

        Configuration includes:
        - 1024-dimensional vectors (Qwen3-Embedding-0.6B)
        - Cosine distance metric
        - HNSW indexing (M=16, ef_construct=200)

        Raises:
            QdrantConnectionError: If creation fails (except when collection already exists).

        Example:
            >>> client = QdrantVectorClient(url="http://localhost:6333", collection_name="docs")
            >>> client.create_collection()
        """
        try:
            create_from_contract(self.client, self.collection_name)
        except Exception as e:
            raise QdrantConnectionError(f"Failed to create collection: {e}") from e

    def delete_collection(self) -> None:
        """Delete collection from Qdrant.

        Warning: This is a destructive operation that cannot be undone.

        Raises:
            QdrantConnectionError: If deletion fails (except when collection doesn't exist).

        Example:
            >>> client = QdrantVectorClient(url="http://localhost:6333", collection_name="docs")
            >>> client.delete_collection()
        """
        try:
            self.client.delete_collection(self.collection_name)
            logger.info("Collection deleted", extra={"collection_name": self.collection_name})
        except UnexpectedResponse as e:
            # Collection not found (404) - log warning but don't raise
            if e.status_code == 404:
                logger.warning(
                    "Collection not found for deletion",
                    extra={"collection_name": self.collection_name},
                )
            else:
                logger.exception(
                    "Failed to delete collection",
                    extra={
                        "collection_name": self.collection_name,
                        "status_code": e.status_code,
                    },
                )
                raise QdrantConnectionError(f"Failed to delete collection: {e}") from e
        except Exception as e:
            logger.exception(
                "Failed to delete collection",
                extra={"collection_name": self.collection_name},
            )
            raise QdrantConnectionError(f"Failed to delete collection: {e}") from e

    def get_collection_info(self) -> CollectionInfo | None:
        """Get collection information and statistics.

        Returns:
            Collection info object or None if collection doesn't exist.

        Raises:
            QdrantConnectionError: If retrieval fails due to connection issues.

        Example:
            >>> client = QdrantVectorClient(url="http://localhost:6333", collection_name="docs")
            >>> info = client.get_collection_info()
            >>> if info:
            ...     print(f"Status: {info.status}, Vectors: {info.vectors_count}")
        """
        try:
            info = self.client.get_collection(self.collection_name)
            logger.debug(
                "Collection info retrieved",
                extra={
                    "collection_name": self.collection_name,
                    "status": info.status,
                    "vectors_count": info.vectors_count,
                },
            )
            return info
        except UnexpectedResponse as e:
            # Collection not found (404) - return None
            if e.status_code == 404:
                logger.debug(
                    "Collection not found",
                    extra={"collection_name": self.collection_name},
                )
                return None
            else:
                logger.exception(
                    "Failed to get collection info",
                    extra={
                        "collection_name": self.collection_name,
                        "status_code": e.status_code,
                    },
                )
                raise QdrantConnectionError(f"Failed to get collection info: {e}") from e
        except Exception as e:
            logger.exception(
                "Failed to get collection info",
                extra={"collection_name": self.collection_name},
            )
            raise QdrantConnectionError(f"Failed to get collection info: {e}") from e

    def close(self) -> None:
        """Close Qdrant client connection.

        Should be called when client is no longer needed to free resources.

        Example:
            >>> client = QdrantVectorClient(url="http://localhost:6333", collection_name="docs")
            >>> try:
            ...     # Use client
            ...     pass
            ... finally:
            ...     client.close()
        """
        try:
            self.client.close()
            logger.debug("Qdrant client closed", extra={"collection_name": self.collection_name})
        except Exception:
            logger.exception("Error closing Qdrant client")

    def __enter__(self) -> "QdrantVectorClient":
        """Enter context manager (client already initialised in __init__)."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager and close the underlying client."""
        self.close()


# Export public API
__all__ = ["QdrantVectorClient", "QdrantConnectionError"]
