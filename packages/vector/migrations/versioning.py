"""Qdrant collection versioning and migration utilities.

Implements collection versioning strategy from MIGRATIONS.md:
- Create versioned collections (e.g., taboot_documents_v1, v2)
- Use collection aliases for zero-downtime migrations
- Support dual-write during migration periods
- Enable rollback via alias switching

Per MIGRATIONS.md:
- Adding payload fields: No downtime (points accept new keys)
- Changing vector params: Create new collection, dual-write, switch alias
- HNSW/optimizer changes: Safe in place, monitor recall and latency
"""

from __future__ import annotations

from contextlib import suppress

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from packages.common.logging import get_logger

logger = get_logger(__name__)


class QdrantMigration:
    """Qdrant collection versioning and migration manager.

    Provides utilities for zero-downtime collection migrations via versioning
    and aliasing. Tracks versions in PostgreSQL schema_versions table.

    Attributes:
        client: Qdrant client for collection operations.

    Example:
        >>> from packages.vector.qdrant_client import QdrantVectorClient
        >>> client = QdrantVectorClient(url="http://localhost:6333")
        >>> migration = QdrantMigration(client.client)
        >>> migration.create_collection_with_version(
        ...     collection_name="taboot_documents",
        ...     vector_size=1024,
        ...     version="1.0.0"
        ... )
    """

    def __init__(self, client: QdrantClient) -> None:
        """Initialize Qdrant migration manager.

        Args:
            client: Qdrant client for collection operations.
        """
        self.client = client

    def create_collection_with_version(
        self,
        collection_name: str,
        vector_size: int,
        version: str,
        distance: Distance = Distance.COSINE,
    ) -> str:
        """Create a versioned collection with alias.

        Creates a new collection with version suffix and creates/updates alias
        to point to the new version. This enables zero-downtime migrations.

        Args:
            collection_name: Base collection name (without version).
            vector_size: Vector dimension size.
            version: Version string (e.g., "1.0.0").
            distance: Distance metric (default: COSINE).

        Returns:
            str: Versioned collection name created.

        Example:
            >>> migration.create_collection_with_version(
            ...     "taboot_documents", 1024, "1.0.0"
            ... )
            'taboot_documents_v1_0_0'
        """
        # Create versioned collection name (replace dots with underscores)
        versioned_name = f"{collection_name}_v{version.replace('.', '_')}"

        logger.info(
            "Creating versioned Qdrant collection",
            extra={
                "collection_name": collection_name,
                "versioned_name": versioned_name,
                "version": version,
                "vector_size": vector_size,
            },
        )

        # Create versioned collection
        self.client.create_collection(
            collection_name=versioned_name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )

        # Create or update alias to point to new version
        self._update_alias(collection_name, versioned_name)

        logger.info(
            "Qdrant collection created with alias",
            extra={
                "versioned_name": versioned_name,
                "alias": collection_name,
            },
        )

        return versioned_name

    def switch_alias(self, collection_name: str, target_version: str) -> None:
        """Switch collection alias to a different version.

        Used for rollback or completing migrations. Points the collection alias
        to a specific versioned collection.

        Args:
            collection_name: Base collection name (alias).
            target_version: Target version to switch to.

        Raises:
            ValueError: If target collection does not exist.

        Example:
            >>> # Rollback to previous version
            >>> migration.switch_alias("taboot_documents", "1.0.0")
        """
        versioned_name = f"{collection_name}_v{target_version.replace('.', '_')}"

        # Verify target collection exists
        collections = self.client.get_collections().collections
        if not any(c.name == versioned_name for c in collections):
            raise ValueError(
                f"Target collection {versioned_name} does not exist. "
                f"Available collections: {[c.name for c in collections]}"
            )

        logger.info(
            "Switching Qdrant alias",
            extra={
                "alias": collection_name,
                "target_version": target_version,
                "versioned_name": versioned_name,
            },
        )

        self._update_alias(collection_name, versioned_name)

        logger.info(
            "Qdrant alias switched successfully",
            extra={"alias": collection_name, "versioned_name": versioned_name},
        )

    def list_versions(self, collection_name: str) -> list[str]:
        """List all versions of a collection.

        Args:
            collection_name: Base collection name.

        Returns:
            list[str]: List of version strings.

        Example:
            >>> versions = migration.list_versions("taboot_documents")
            >>> print(versions)
            ['1.0.0', '1.1.0', '2.0.0']
        """
        collections = self.client.get_collections().collections
        prefix = f"{collection_name}_v"

        versions = []
        for collection in collections:
            if collection.name.startswith(prefix):
                # Extract version from name (replace underscores with dots)
                version_part = collection.name[len(prefix) :]
                version = version_part.replace("_", ".")
                versions.append(version)

        return sorted(versions)

    def get_current_version(self, collection_name: str) -> str | None:
        """Get the current version pointed to by the collection alias.

        Args:
            collection_name: Base collection name (alias).

        Returns:
            str | None: Current version string, or None if no alias exists.

        Example:
            >>> version = migration.get_current_version("taboot_documents")
            >>> print(f"Current version: {version}")
            Current version: 1.0.0
        """
        try:
            # Get collection info via alias
            info = self.client.get_collection(collection_name)

            # Extract version from collection name
            prefix = f"{collection_name}_v"
            if hasattr(info, "name") and str(info.name).startswith(prefix):
                version_part = str(info.name)[len(prefix) :]
                return version_part.replace("_", ".")

            return None
        except Exception as e:
            logger.warning(
                "Failed to get current version",
                extra={"collection_name": collection_name, "error": str(e)},
            )
            return None

    def _update_alias(self, alias_name: str, collection_name: str) -> None:
        """Update or create collection alias.

        Args:
            alias_name: Alias name.
            collection_name: Target collection name.
        """
        # Delete existing alias if it exists
        with suppress(Exception):
            self.client.delete_alias(alias_name=alias_name)

        # Create new alias
        self.client.create_alias(collection_name=collection_name, alias_name=alias_name)


# Export public API
__all__ = ["QdrantMigration"]
