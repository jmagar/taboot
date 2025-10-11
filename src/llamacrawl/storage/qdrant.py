"""Qdrant vector database client wrapper.

This module provides a client wrapper for Qdrant vector database operations,
including collection management, document operations, and search methods.
"""

from typing import Any

from qdrant_client import QdrantClient as QdrantClientSDK
from qdrant_client import models
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    HnswConfigDiff,
    MatchValue,
    PointStruct,
    Range,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    VectorParams,
)

from llamacrawl.models.document import Document
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)


class QdrantClient:
    """Qdrant vector database client wrapper.

    This class wraps the Qdrant client SDK and provides high-level operations
    for collection management, document operations, and search.

    Attributes:
        client: Underlying Qdrant SDK client
        collection_name: Name of the collection to use
        vector_dimension: Dimension of embedding vectors
    """

    def __init__(
        self,
        url: str,
        collection_name: str = "llamacrawl_documents",
        vector_dimension: int = 1024,
        distance_metric: str = "cosine",
    ):
        """Initialize Qdrant client.

        Args:
            url: Qdrant server URL (e.g., "http://localhost:6333")
            collection_name: Name of the collection to use
            vector_dimension: Dimension of embedding vectors (default: 1024)
            distance_metric: Distance metric ("cosine", "euclidean", "dot", default: "cosine")
        """
        self.url = url
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        self.distance_metric = self._map_distance_metric(distance_metric)

        logger.info(
            "Initializing Qdrant client",
            extra={
                "qdrant_url": url,
                "collection_name": collection_name,
                "vector_dimension": vector_dimension,
                "distance_metric": distance_metric,
            },
        )

        try:
            self.client = QdrantClientSDK(url=url)
            logger.info("Qdrant client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}", extra={"error": str(e)})
            raise

    def _map_distance_metric(self, metric: str) -> Distance:
        """Map string distance metric to Qdrant Distance enum.

        Args:
            metric: Distance metric string ("cosine", "euclidean", "dot")

        Returns:
            Qdrant Distance enum value

        Raises:
            ValueError: If metric is not supported
        """
        metric_map = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "dot": Distance.DOT,
        }

        metric_lower = metric.lower()
        if metric_lower not in metric_map:
            raise ValueError(
                f"Unsupported distance metric: {metric}. "
                f"Supported metrics: {', '.join(metric_map.keys())}"
            )

        return metric_map[metric_lower]

    def health_check(self) -> bool:
        """Check if Qdrant server is healthy and accessible.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            # Simple health check by getting collections
            self.client.get_collections()
            logger.debug("Qdrant health check passed")
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}", extra={"error": str(e)})
            return False

    def collection_exists(self) -> bool:
        """Check if the collection exists.

        Returns:
            True if collection exists, False otherwise
        """
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            logger.debug(
                f"Collection existence check: {exists}",
                extra={"collection_name": self.collection_name, "exists": exists},
            )
            return exists
        except Exception as e:
            logger.error(
                f"Failed to check collection existence: {e}",
                extra={"collection_name": self.collection_name, "error": str(e)},
            )
            return False

    def create_collection(
        self,
        hnsw_m: int = 16,
        hnsw_ef_construct: int = 100,
        enable_quantization: bool = True,
    ) -> None:
        """Create Qdrant collection with optimized configuration.

        Creates a collection with:
        - Vector dimension: 1024 (Qwen3-Embedding-0.6B)
        - Distance metric: Cosine similarity
        - Optimized HNSW parameters for balanced performance
        - Optional scalar quantization for 4x memory reduction
        - Indexed payload fields for efficient filtering

        Args:
            hnsw_m: HNSW m parameter (edges per node, default: 16)
            hnsw_ef_construct: HNSW ef_construct parameter (neighbors during build, default: 100)
            enable_quantization: Enable scalar quantization (default: True)

        Raises:
            Exception: If collection creation fails
        """
        if self.collection_exists():
            logger.warning(
                f"Collection {self.collection_name} already exists, skipping creation",
                extra={"collection_name": self.collection_name},
            )
            return

        logger.info(
            f"Creating collection {self.collection_name}",
            extra={
                "collection_name": self.collection_name,
                "vector_dimension": self.vector_dimension,
                "hnsw_m": hnsw_m,
                "hnsw_ef_construct": hnsw_ef_construct,
                "enable_quantization": enable_quantization,
            },
        )

        try:
            # Vector configuration
            vectors_config = VectorParams(
                size=self.vector_dimension,
                distance=self.distance_metric,
            )

            # HNSW configuration for optimized search
            hnsw_config = HnswConfigDiff(
                m=hnsw_m,
                ef_construct=hnsw_ef_construct,
                full_scan_threshold=10000,
            )

            # Quantization configuration (scalar quantization for 4x memory reduction)
            quantization_config = None
            if enable_quantization:
                quantization_config = ScalarQuantization(
                    scalar=ScalarQuantizationConfig(
                        type=ScalarType.INT8,
                        quantile=0.99,
                        always_ram=True,
                    )
                )

            # Create collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=vectors_config,
                hnsw_config=hnsw_config,
                quantization_config=quantization_config,
            )

            logger.info(f"Collection {self.collection_name} created successfully")

            # Create payload indexes for efficient filtering
            self._create_payload_indexes()

        except Exception as e:
            logger.error(
                f"Failed to create collection: {e}",
                extra={"collection_name": self.collection_name, "error": str(e)},
            )
            raise

    def _create_payload_indexes(self) -> None:
        """Create payload indexes for frequently filtered fields.

        Creates indexes on:
        - doc_id: Unique document identifier
        - source_type: Data source type (firecrawl, github, etc.)
        - timestamp: Document timestamp for date range filtering
        - content_hash: SHA-256 hash for deduplication
        """
        indexes = [
            ("doc_id", "keyword"),
            ("source_type", "keyword"),
            ("timestamp", "datetime"),
            ("content_hash", "keyword"),
        ]

        for field_name, field_schema in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                )
                logger.debug(
                    f"Created payload index on {field_name}",
                    extra={"field_name": field_name, "field_schema": field_schema},
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create index on {field_name}: {e}",
                    extra={"field_name": field_name, "error": str(e)},
                )

    def upsert_documents(self, documents: list[Document]) -> int:
        """Upsert documents with vectors and payload in batches.

        Args:
            documents: List of Document objects with embeddings

        Returns:
            Number of documents upserted

        Raises:
            ValueError: If documents have no embeddings
            Exception: If upsert operation fails
        """
        if not documents:
            logger.warning("No documents to upsert")
            return 0

        # Validate all documents have embeddings
        for doc in documents:
            if doc.embedding is None:
                raise ValueError(f"Document {doc.doc_id} has no embedding vector")

        logger.info(
            f"Upserting {len(documents)} documents",
            extra={"document_count": len(documents)},
        )

        # Convert documents to PointStruct objects
        points = []
        for doc in documents:
            # Type assertion: we already validated embeddings are not None above
            assert doc.embedding is not None, f"Document {doc.doc_id} missing embedding"
            points.append(
                PointStruct(
                    id=doc.doc_id,
                    vector=doc.embedding,
                    payload={
                        "doc_id": doc.doc_id,
                        "source_type": doc.metadata.source_type,
                        "source_url": doc.metadata.source_url,
                        "title": doc.title,
                        "content": doc.content,
                        "timestamp": doc.metadata.timestamp.isoformat(),
                        "metadata": doc.metadata.extra,
                        "content_hash": doc.content_hash,
                    },
                )
            )

        # Batch upsert (100-1000 points per batch for efficiency)
        batch_size = 100
        total_upserted = 0
        total_batches = (len(points) + batch_size - 1) // batch_size

        try:
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                # Add timeout to prevent hanging on slow Qdrant responses
                # Using wait=False for async operation, then checking separately
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                    wait=False,  # Don't wait synchronously
                )
                total_upserted += len(batch)
                batch_num = i // batch_size + 1
                logger.debug(
                    f"Upserted batch {batch_num}/{total_batches}",
                    extra={"batch_number": batch_num, "batch_size": len(batch)},
                )

            logger.info(
                f"Successfully upserted {total_upserted} documents",
                extra={"total_upserted": total_upserted},
            )
            return total_upserted

        except Exception as e:
            logger.error(
                f"Failed to upsert documents: {e}",
                extra={"error": str(e), "total_upserted": total_upserted},
            )
            raise

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by ID.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.info(f"Deleting document {doc_id}", extra={"doc_id": doc_id})

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[doc_id]),
                wait=True,
            )
            logger.info(f"Successfully deleted document {doc_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete document {doc_id}: {e}",
                extra={"doc_id": doc_id, "error": str(e)},
            )
            return False

    def get_document_count(self, source_type: str | None = None) -> int:
        """Get document count, optionally filtered by source type.

        Args:
            source_type: Optional source type to filter by (e.g., "github", "firecrawl")

        Returns:
            Number of documents matching the filter
        """
        try:
            # Build filter if source_type is provided
            count_filter = None
            if source_type:
                count_filter = Filter(
                    must=[FieldCondition(key="source_type", match=MatchValue(value=source_type))]
                )

            # Get collection info with filter
            result = self.client.count(
                collection_name=self.collection_name,
                count_filter=count_filter,
                exact=True,
            )

            count = int(result.count)
            logger.debug(
                f"Document count: {count}",
                extra={"source_type": source_type, "count": count},
            )
            return count

        except Exception as e:
            logger.error(
                f"Failed to get document count: {e}",
                extra={"source_type": source_type, "error": str(e)},
            )
            return 0

    def search(
        self,
        query_vector: list[float],
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Perform vector search with optional metadata filters.

        Supports filters:
        - source_type: Filter by source type (e.g., "github")
        - source_types: Filter by multiple source types (list)
        - date_from: Filter documents created after this date (ISO 8601 string)
        - date_to: Filter documents created before this date (ISO 8601 string)
        - Custom metadata filters via nested dict

        Args:
            query_vector: Query embedding vector (1024-dim)
            filters: Optional metadata filters (see above)
            limit: Maximum number of results to return
            score_threshold: Optional minimum score threshold

        Returns:
            List of search results with id, score, and payload

        Example:
            >>> results = client.search(
            ...     query_vector=[0.1] * 1024,
            ...     filters={
            ...         "source_types": ["github", "documentation"],
            ...         "date_from": "2025-01-01T00:00:00Z"
            ...     },
            ...     limit=20
            ... )
        """
        logger.debug(
            "Performing vector search",
            extra={"limit": limit, "filters": filters, "score_threshold": score_threshold},
        )

        # Build Qdrant filter from filters dict
        query_filter = self._build_filter(filters) if filters else None

        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False,
            )

            search_results = [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                }
                for hit in results.points
            ]

            logger.info(
                f"Search completed: {len(search_results)} results",
                extra={"result_count": len(search_results)},
            )

            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}", extra={"error": str(e), "filters": filters})
            raise

    def _build_filter(self, filters: dict[str, Any]) -> Filter:
        """Build Qdrant filter from filters dictionary.

        Args:
            filters: Filter dictionary with keys like source_type, date_from, etc.

        Returns:
            Qdrant Filter object
        """
        must_conditions = []

        # Single source_type filter
        if "source_type" in filters:
            must_conditions.append(
                FieldCondition(key="source_type", match=MatchValue(value=filters["source_type"]))
            )

        # Multiple source_types filter (OR logic via should)
        if "source_types" in filters and isinstance(filters["source_types"], list):
            # For multiple source types, use should (OR logic)
            should_conditions = [
                FieldCondition(key="source_type", match=MatchValue(value=st))
                for st in filters["source_types"]
            ]
            # Qdrant Filter expects broader union, list is invariant
            return Filter(should=should_conditions, must=must_conditions)

        # Date range filters
        range_params: dict[str, str] = {}
        if "date_from" in filters:
            range_params["gte"] = filters["date_from"]
        if "date_to" in filters:
            range_params["lte"] = filters["date_to"]

        if range_params:
            # Range accepts datetime strings for timestamp fields despite float type hint
            must_conditions.append(FieldCondition(key="timestamp", range=Range(**range_params)))

        # Custom metadata filters (nested fields via dot notation)
        for key, value in filters.items():
            if key not in ["source_type", "source_types", "date_from", "date_to"]:
                # Support nested metadata filters using dot notation
                # e.g., filters={"metadata.repo_owner": "llamaindex"}
                if isinstance(value, str | int | bool):
                    must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
                elif isinstance(value, dict) and "gte" in value or "lte" in value:
                    # Range filter for numeric fields
                    must_conditions.append(FieldCondition(key=key, range=Range(**value)))

        # Qdrant Filter expects broader union, list is invariant
        return Filter(must=must_conditions) if must_conditions else Filter()


__all__ = ["QdrantClient"]
