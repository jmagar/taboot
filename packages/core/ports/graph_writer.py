"""GraphWriterPort - Port interface for graph database operations.

Defines the contract for writing nodes and relationships to graph databases.
Core layer defines this interface; adapters (packages/graph) implement it.

Per CLAUDE.md: Core depends only on packages/schemas and packages/common.
This port allows core use-cases to orchestrate graph writes without
importing framework-specific adapters directly.
"""

from __future__ import annotations

from typing import Any, Protocol

from packages.schemas.models import Proxy


class RouteInfo(Protocol):
    """Protocol for route information extracted from configs.

    Represents a ROUTES_TO relationship between Proxy and Service.
    """

    host: str
    path: str
    target_service: str
    tls: bool


class GraphWriterPort(Protocol):
    """Port interface for graph database write operations.

    Implementations should provide batched writes using UNWIND
    or equivalent bulk operations for performance (target ≥20k edges/min).
    """

    def write_proxies(self, proxies: list[Proxy]) -> dict[str, int]:
        """Write Proxy nodes to graph database.

        Args:
            proxies: List of Proxy entities to write.

        Returns:
            dict[str, int]: Statistics (e.g., {"total_written": N, "batches_executed": M}).

        Raises:
            Exception: If write operation fails.
        """
        ...

    def write_routes(self, proxy_name: str, routes: list[dict[str, Any]]) -> dict[str, int]:
        """Write ROUTES_TO relationships to graph database.

        Creates Service nodes (if missing) and ROUTES_TO relationships
        from Proxy to Service nodes with routing metadata.

        Args:
            proxy_name: Name of the Proxy node (source).
            routes: List of route dictionaries with keys:
                - host: str
                - path: str
                - target_service: str
                - tls: bool

        Returns:
            dict[str, int]: Statistics (e.g., {"total_written": N, "batches_executed": M}).

        Raises:
            Exception: If write operation fails.
        """
        ...


# Export public API
__all__ = ["GraphWriterPort", "RouteInfo"]
