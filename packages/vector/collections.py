"""Qdrant collection configuration loading and creation utilities.

Provides:
- Collection configuration loading from JSON contract
- Collection creation with contract-based parameters
- Idempotent collection management with proper error handling

All operations use JSON structured logging and correlation ID tracking.
"""

import json
import uuid
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from packages.common.logging import get_logger

logger = get_logger(__name__)


class CollectionCreationError(Exception):
    """Raised when collection creation fails (excluding 409 conflicts)."""

    pass


def load_collection_config() -> dict[str, Any]:
    """Load collection configuration from JSON contract file.

    Loads configuration from:
    specs/001-taboot-rag-platform/contracts/qdrant-collection.json

    Returns:
        dict[str, Any]: Parsed collection configuration with required fields:
            - collection_name: Name of the collection
            - vectors: Vector configuration (size, distance, on_disk)
            - hnsw_config: HNSW indexing parameters
            - optimizers_config: Optimizer settings
            - wal_config: Write-ahead log settings
            - payload_schema: Metadata field definitions

    Raises:
        FileNotFoundError: If contract file doesn't exist.
        ValueError: If required fields are missing from configuration.
        json.JSONDecodeError: If JSON is malformed.

    Example:
        >>> config = load_collection_config()
        >>> assert config["collection_name"] == "documents"
        >>> assert config["vectors"]["size"] == 768
    """
    # Path relative to project root
    contract_path = (
        Path(__file__).parent.parent.parent
        / "specs"
        / "001-taboot-rag-platform"
        / "contracts"
        / "qdrant-collection.json"
    )

    correlation_id = str(uuid.uuid4())
    logger.info(
        "Loading collection configuration",
        extra={
            "correlation_id": correlation_id,
            "config_path": str(contract_path),
        },
    )

    if not contract_path.exists():
        logger.error(
            "Collection config file not found",
            extra={
                "correlation_id": correlation_id,
                "config_path": str(contract_path),
            },
        )
        raise FileNotFoundError(f"Collection config not found: {contract_path}")

    try:
        with open(contract_path) as f:
            config: dict[str, Any] = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse collection config JSON",
            extra={
                "correlation_id": correlation_id,
                "config_path": str(contract_path),
                "error": str(e),
            },
        )
        raise

    # Validate required top-level fields
    required_fields = [
        "collection_name",
        "vectors",
        "hnsw_config",
        "optimizers_config",
        "wal_config",
        "payload_schema",
    ]
    missing_fields = [field for field in required_fields if field not in config]
    if missing_fields:
        logger.error(
            "Collection config missing required fields",
            extra={
                "correlation_id": correlation_id,
                "missing_fields": missing_fields,
            },
        )
        raise ValueError(f"Collection config missing required fields: {missing_fields}")

    logger.info(
        "Collection configuration loaded successfully",
        extra={
            "correlation_id": correlation_id,
            "collection_name": config.get("collection_name"),
        },
    )

    return config


def create_collection(client: QdrantClient, collection_name: str) -> None:
    """Create Qdrant collection with parameters from contract configuration.

    Loads configuration from qdrant-collection.json and creates collection with:
    - 768-dimensional vectors (Qwen3-Embedding-0.6B)
    - Cosine distance metric
    - HNSW indexing (M=16, ef_construct=200)
    - Optimizers and WAL configuration

    Operation is idempotent: if collection already exists (409 Conflict),
    logs a warning but does not raise an error.

    Args:
        client: QdrantClient instance to use for creation.
        collection_name: Name of collection to create (overrides config if different).

    Raises:
        CollectionCreationError: If creation fails with 500 error or other failure.
        FileNotFoundError: If collection config file not found.
        ValueError: If configuration is invalid.
        ConnectionError: If network connection fails.

    Example:
        >>> from qdrant_client import QdrantClient
        >>> client = QdrantClient(url="http://localhost:6333")
        >>> create_collection(client, "documents")
    """
    correlation_id = str(uuid.uuid4())
    logger.info(
        "Creating collection",
        extra={
            "correlation_id": correlation_id,
            "collection_name": collection_name,
        },
    )

    # Load configuration from contract
    config = load_collection_config()

    # Build configuration objects from JSON
    try:
        vectors_config = models.VectorParams(
            size=config["vectors"]["size"],
            distance=models.Distance.COSINE,  # Always use Cosine per spec
            on_disk=config["vectors"]["on_disk"],
        )

        hnsw_config = models.HnswConfigDiff(
            m=config["hnsw_config"]["m"],
            ef_construct=config["hnsw_config"]["ef_construct"],
            full_scan_threshold=config["hnsw_config"]["full_scan_threshold"],
            on_disk=config["hnsw_config"]["on_disk"],
        )

        optimizers_config = models.OptimizersConfigDiff(
            deleted_threshold=config["optimizers_config"]["deleted_threshold"],
            vacuum_min_vector_number=config["optimizers_config"]["vacuum_min_vector_number"],
            indexing_threshold=config["optimizers_config"]["indexing_threshold"],
            flush_interval_sec=config["optimizers_config"]["flush_interval_sec"],
            max_optimization_threads=config["optimizers_config"]["max_optimization_threads"],
        )

        wal_config = models.WalConfigDiff(
            wal_capacity_mb=config["wal_config"]["wal_capacity_mb"],
            wal_segments_ahead=config["wal_config"]["wal_segments_ahead"],
        )

        logger.debug(
            "Collection configuration parsed",
            extra={
                "correlation_id": correlation_id,
                "vector_size": vectors_config.size,
                "hnsw_m": hnsw_config.m,
            },
        )

    except KeyError as e:
        logger.error(
            "Collection config missing required parameter",
            extra={
                "correlation_id": correlation_id,
                "missing_key": str(e),
            },
        )
        raise ValueError(f"Collection config missing required parameter: {e}") from e

    # Create collection with configured parameters
    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=vectors_config,
            hnsw_config=hnsw_config,
            optimizers_config=optimizers_config,
            wal_config=wal_config,
        )
        logger.info(
            "Collection created successfully",
            extra={
                "correlation_id": correlation_id,
                "collection_name": collection_name,
            },
        )
    except UnexpectedResponse as e:
        # 409 Conflict: Collection already exists (idempotent - this is OK)
        if e.status_code == 409:
            logger.warning(
                "Collection already exists (idempotent operation)",
                extra={
                    "correlation_id": correlation_id,
                    "collection_name": collection_name,
                },
            )
            return

        # 500 Internal Server Error or other unexpected error
        logger.error(
            "Failed to create collection",
            extra={
                "correlation_id": correlation_id,
                "collection_name": collection_name,
                "status_code": e.status_code,
                "error": str(e),
            },
        )
        raise CollectionCreationError(
            f"Failed to create collection '{collection_name}': HTTP {e.status_code} - {e}"
        ) from e
    except Exception as e:
        # Network errors or other unexpected failures
        logger.error(
            "Failed to create collection due to network or unexpected error",
            extra={
                "correlation_id": correlation_id,
                "collection_name": collection_name,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise CollectionCreationError(
            f"Failed to create collection '{collection_name}': {e}"
        ) from e


async def create_qdrant_collections() -> None:
    """Create Qdrant collections asynchronously (async wrapper for create_collection).

    This async function is used by the /init endpoint and other async contexts.
    Loads config and creates the main documents collection.

    Raises:
        CollectionCreationError: If collection creation fails.
        FileNotFoundError: If config file not found.
        ValueError: If configuration is invalid.

    Example:
        >>> await create_qdrant_collections()
    """
    from packages.common.config import get_config

    config = get_config()
    client = QdrantClient(url=config.qdrant_url)

    try:
        create_collection(client, config.collection_name)
    finally:
        client.close()


# Export public API
__all__ = [
    "CollectionCreationError",
    "load_collection_config",
    "create_collection",
    "create_qdrant_collections",
]
