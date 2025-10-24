"""SwagGraphWriter - Batched Neo4j writer for SWAG ingestion.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/batched.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging
from typing import Any

from packages.graph.client import Neo4jClient
from packages.schemas.models import Proxy

logger = logging.getLogger(__name__)


class SwagGraphWriter:
    """Batched Neo4j writer for SWAG proxy and route ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize SwagGraphWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized SwagGraphWriter (batch_size={batch_size})")

    def write_proxies(self, proxies: list[Proxy]) -> dict[str, int]:
        """Write Proxy nodes to Neo4j using batched UNWIND.

        Creates or updates Proxy nodes with all properties.
        Uses MERGE on unique key (name) for idempotency.

        Args:
            proxies: List of Proxy entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total proxies written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not proxies:
            logger.info("No proxies to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare proxy parameters
        proxy_params = [
            {
                "name": p.name,
                "proxy_type": p.proxy_type.value,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
                "metadata": p.metadata or {},
                "config_path": p.config_path,
                "extraction_version": p.extraction_version,
            }
            for p in proxies
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(proxy_params), self.batch_size):
                batch = proxy_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (p:Proxy {name: row.name})
                SET p.proxy_type = row.proxy_type,
                    p.created_at = row.created_at,
                    p.updated_at = row.updated_at,
                    p.metadata = row.metadata,
                    p.config_path = row.config_path,
                    p.extraction_version = row.extraction_version
                RETURN count(p) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote proxy batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Proxy node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_routes(self, proxy_name: str, routes: list[dict[str, Any]]) -> dict[str, int]:
        """Write ROUTES_TO relationships to Neo4j using batched UNWIND.

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
            dict[str, int]: Statistics with keys:
                - total_written: Total routes written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If proxy_name is empty or routes are invalid.
            Exception: If Neo4j write operation fails.
        """
        if not proxy_name:
            raise ValueError("proxy_name cannot be empty")

        if not routes:
            logger.info("No routes to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        with self.neo4j_client.session() as session:
            # Step 1: Create Service nodes in batch (UNWIND)
            service_rows = [{"name": route["target_service"]} for route in routes]

            # Deduplicate service names
            unique_services = list({s["name"]: s for s in service_rows}.values())

            for i in range(0, len(unique_services), self.batch_size):
                batch = unique_services[i : i + self.batch_size]

                service_query = """
                UNWIND $rows AS row
                MERGE (s:Service {name: row.name})
                RETURN count(s) AS created_count
                """

                result = session.run(service_query, {"rows": batch})
                result.consume()

                batches_executed += 1

                logger.debug(
                    f"Created/merged Service nodes batch {batches_executed}: {len(batch)} services"
                )

            # Step 2: Create ROUTES_TO relationships in batch (UNWIND)
            rel_rows = [
                {
                    "proxy_name": proxy_name,
                    "service_name": route["target_service"],
                    "host": route["host"],
                    "path": route["path"],
                    "tls": route["tls"],
                }
                for route in routes
            ]

            for i in range(0, len(rel_rows), self.batch_size):
                batch = rel_rows[i : i + self.batch_size]

                rel_query = """
                UNWIND $rows AS row
                MATCH (p:Proxy {name: row.proxy_name})
                MATCH (s:Service {name: row.service_name})
                MERGE (p)-[r:ROUTES_TO]->(s)
                SET r.host = row.host,
                    r.path = row.path,
                    r.tls = row.tls
                RETURN count(r) AS created_count
                """

                result = session.run(rel_query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote ROUTES_TO batch {batches_executed}: "
                    f"{len(batch)} relationships, "
                    f"counters={summary.counters}"
                )

        logger.info(
            f"Wrote {total_written} ROUTES_TO relationship(s) in {batches_executed} batch(es)"
        )

        return {"total_written": total_written, "batches_executed": batches_executed}


# Export public API
__all__ = ["SwagGraphWriter"]
