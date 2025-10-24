"""Qdrant vector storage adapter package.

Provides:
- Qdrant client for vector storage and collection management
- Collection configuration and creation utilities
- Batched writer for efficient upserts with metadata
- Hybrid search and reranking capabilities
"""

from packages.vector.qdrant_client import QdrantConnectionError, QdrantVectorClient
from packages.vector.collections import (
    CollectionCreationError,
    create_collection,
    create_qdrant_collections,
    load_collection_config,
)
from packages.vector.writer import QdrantWriteError, QdrantWriter

__all__ = [
    # Client
    "QdrantVectorClient",
    "QdrantConnectionError",
    # Collections
    "load_collection_config",
    "create_collection",
    "create_qdrant_collections",
    "CollectionCreationError",
    # Writer
    "QdrantWriter",
    "QdrantWriteError",
]
