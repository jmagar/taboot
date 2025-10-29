"""SwagGraphWriter - Batched Neo4j writer for SWAG ingestion.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/batched.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging

from packages.graph.client import Neo4jClient
from packages.schemas.swag import (
    LocationBlock,
    Proxy,
    ProxyHeader,
    ProxyRoute,
    SwagConfigFile,
    UpstreamConfig,
)

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

    def write_swag_config_files(self, config_files: list[SwagConfigFile]) -> dict[str, int]:
        """Write SwagConfigFile nodes to Neo4j using batched UNWIND.

        Creates or updates SwagConfigFile nodes with all properties.
        Uses MERGE on unique key (file_path) for idempotency.

        Args:
            config_files: List of SwagConfigFile entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total config files written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not config_files:
            logger.info("No SWAG config files to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare config file parameters
        config_params = [
            {
                "file_path": cf.file_path,
                "version": cf.version,
                "parsed_at": cf.parsed_at.isoformat() if cf.parsed_at else None,
                "created_at": cf.created_at.isoformat(),
                "updated_at": cf.updated_at.isoformat(),
                "source_timestamp": (
                    cf.source_timestamp.isoformat() if cf.source_timestamp else None
                ),
                "extraction_tier": cf.extraction_tier,
                "extraction_method": cf.extraction_method,
                "confidence": cf.confidence,
                "extractor_version": cf.extractor_version,
            }
            for cf in config_files
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(config_params), self.batch_size):
                batch = config_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (cf:SwagConfigFile {file_path: row.file_path})
                SET cf.version = row.version,
                    cf.parsed_at = row.parsed_at,
                    cf.created_at = row.created_at,
                    cf.updated_at = row.updated_at,
                    cf.source_timestamp = row.source_timestamp,
                    cf.extraction_tier = row.extraction_tier,
                    cf.extraction_method = row.extraction_method,
                    cf.confidence = row.confidence,
                    cf.extractor_version = row.extractor_version
                RETURN count(cf) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote SwagConfigFile batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} SwagConfigFile node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_proxies(self, proxies: list[Proxy]) -> dict[str, int]:
        """Write Proxy nodes to Neo4j using batched UNWIND.

        Creates or updates Proxy nodes with all properties including extraction metadata.
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
                "proxy_type": p.proxy_type,
                "config_path": p.config_path,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
                "source_timestamp": (
                    p.source_timestamp.isoformat() if p.source_timestamp else None
                ),
                "extraction_tier": p.extraction_tier,
                "extraction_method": p.extraction_method,
                "confidence": p.confidence,
                "extractor_version": p.extractor_version,
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
                    p.config_path = row.config_path,
                    p.created_at = row.created_at,
                    p.updated_at = row.updated_at,
                    p.source_timestamp = row.source_timestamp,
                    p.extraction_tier = row.extraction_tier,
                    p.extraction_method = row.extraction_method,
                    p.confidence = row.confidence,
                    p.extractor_version = row.extractor_version
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

    def write_proxy_routes(self, proxy_name: str, routes: list[ProxyRoute]) -> dict[str, int]:
        """Write ProxyRoute nodes and ROUTES_TO relationships to Neo4j.

        Creates ProxyRoute nodes and relationships from Proxy to Service nodes
        with routing metadata (server_name, upstream_app, port, protocol, TLS).

        Args:
            proxy_name: Name of the Proxy node (source).
            routes: List of ProxyRoute entities to write.

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
            logger.info("No proxy routes to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        with self.neo4j_client.session() as session:
            # Prepare route parameters
            route_params = [
                {
                    "proxy_name": proxy_name,
                    "server_name": r.server_name,
                    "upstream_app": r.upstream_app,
                    "upstream_port": r.upstream_port,
                    "upstream_proto": r.upstream_proto,
                    "tls_enabled": r.tls_enabled,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat(),
                    "source_timestamp": (
                        r.source_timestamp.isoformat() if r.source_timestamp else None
                    ),
                    "extraction_tier": r.extraction_tier,
                    "extraction_method": r.extraction_method,
                    "confidence": r.confidence,
                    "extractor_version": r.extractor_version,
                }
                for r in routes
            ]

            # Execute in batches
            for i in range(0, len(route_params), self.batch_size):
                batch = route_params[i : i + self.batch_size]

                # Create ProxyRoute nodes and ROUTES_TO relationships
                query = """
                UNWIND $rows AS row
                MATCH (p:Proxy {name: row.proxy_name})
                MERGE (pr:ProxyRoute {
                    server_name: row.server_name,
                    upstream_app: row.upstream_app,
                    upstream_port: row.upstream_port
                })
                SET pr.upstream_proto = row.upstream_proto,
                    pr.tls_enabled = row.tls_enabled,
                    pr.created_at = row.created_at,
                    pr.updated_at = row.updated_at,
                    pr.source_timestamp = row.source_timestamp,
                    pr.extraction_tier = row.extraction_tier,
                    pr.extraction_method = row.extraction_method,
                    pr.confidence = row.confidence,
                    pr.extractor_version = row.extractor_version
                MERGE (p)-[r:ROUTES_TO]->(pr)
                SET r.server_name = row.server_name,
                    r.tls = row.tls_enabled
                RETURN count(pr) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote ProxyRoute batch {batches_executed}: "
                    f"{len(batch)} routes, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} ProxyRoute node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_location_blocks(
        self, proxy_name: str, locations: list[LocationBlock]
    ) -> dict[str, int]:
        """Write LocationBlock nodes and HAS_LOCATION relationships to Neo4j.

        Creates LocationBlock nodes with path, proxy_pass_url, and auth configuration.
        Links them to the parent Proxy node via HAS_LOCATION relationships.

        Args:
            proxy_name: Name of the Proxy node (source).
            locations: List of LocationBlock entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total location blocks written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If proxy_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not proxy_name:
            raise ValueError("proxy_name cannot be empty")

        if not locations:
            logger.info("No location blocks to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        with self.neo4j_client.session() as session:
            # Prepare location parameters
            location_params = [
                {
                    "proxy_name": proxy_name,
                    "path": loc.path,
                    "proxy_pass_url": loc.proxy_pass_url,
                    "auth_enabled": loc.auth_enabled,
                    "auth_type": loc.auth_type,
                    "created_at": loc.created_at.isoformat(),
                    "updated_at": loc.updated_at.isoformat(),
                    "source_timestamp": (
                        loc.source_timestamp.isoformat() if loc.source_timestamp else None
                    ),
                    "extraction_tier": loc.extraction_tier,
                    "extraction_method": loc.extraction_method,
                    "confidence": loc.confidence,
                    "extractor_version": loc.extractor_version,
                }
                for loc in locations
            ]

            # Execute in batches
            for i in range(0, len(location_params), self.batch_size):
                batch = location_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (p:Proxy {name: row.proxy_name})
                MERGE (lb:LocationBlock {path: row.path, proxy_name: row.proxy_name})
                SET lb.proxy_pass_url = row.proxy_pass_url,
                    lb.auth_enabled = row.auth_enabled,
                    lb.auth_type = row.auth_type,
                    lb.created_at = row.created_at,
                    lb.updated_at = row.updated_at,
                    lb.source_timestamp = row.source_timestamp,
                    lb.extraction_tier = row.extraction_tier,
                    lb.extraction_method = row.extraction_method,
                    lb.confidence = row.confidence,
                    lb.extractor_version = row.extractor_version
                MERGE (p)-[r:HAS_LOCATION]->(lb)
                RETURN count(lb) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote LocationBlock batch {batches_executed}: "
                    f"{len(batch)} locations, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} LocationBlock node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_upstream_configs(
        self, proxy_name: str, upstreams: list[UpstreamConfig]
    ) -> dict[str, int]:
        """Write UpstreamConfig nodes and HAS_UPSTREAM relationships to Neo4j.

        Creates UpstreamConfig nodes with app, port, and protocol configuration.
        Links them to the parent Proxy node via HAS_UPSTREAM relationships.

        Args:
            proxy_name: Name of the Proxy node (source).
            upstreams: List of UpstreamConfig entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total upstream configs written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If proxy_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not proxy_name:
            raise ValueError("proxy_name cannot be empty")

        if not upstreams:
            logger.info("No upstream configs to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        with self.neo4j_client.session() as session:
            # Prepare upstream parameters
            upstream_params = [
                {
                    "proxy_name": proxy_name,
                    "app": u.app,
                    "port": u.port,
                    "proto": u.proto,
                    "created_at": u.created_at.isoformat(),
                    "updated_at": u.updated_at.isoformat(),
                    "source_timestamp": (
                        u.source_timestamp.isoformat() if u.source_timestamp else None
                    ),
                    "extraction_tier": u.extraction_tier,
                    "extraction_method": u.extraction_method,
                    "confidence": u.confidence,
                    "extractor_version": u.extractor_version,
                }
                for u in upstreams
            ]

            # Execute in batches
            for i in range(0, len(upstream_params), self.batch_size):
                batch = upstream_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (p:Proxy {name: row.proxy_name})
                MERGE (uc:UpstreamConfig {app: row.app, port: row.port, proto: row.proto})
                SET uc.created_at = row.created_at,
                    uc.updated_at = row.updated_at,
                    uc.source_timestamp = row.source_timestamp,
                    uc.extraction_tier = row.extraction_tier,
                    uc.extraction_method = row.extraction_method,
                    uc.confidence = row.confidence,
                    uc.extractor_version = row.extractor_version
                MERGE (p)-[r:HAS_UPSTREAM]->(uc)
                RETURN count(uc) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote UpstreamConfig batch {batches_executed}: "
                    f"{len(batch)} upstreams, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} UpstreamConfig node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_proxy_headers(self, proxy_name: str, headers: list[ProxyHeader]) -> dict[str, int]:
        """Write ProxyHeader nodes and HAS_HEADER relationships to Neo4j.

        Creates ProxyHeader nodes with header name, value, and type.
        Links them to the parent Proxy node via HAS_HEADER relationships.

        Args:
            proxy_name: Name of the Proxy node (source).
            headers: List of ProxyHeader entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total proxy headers written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If proxy_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not proxy_name:
            raise ValueError("proxy_name cannot be empty")

        if not headers:
            logger.info("No proxy headers to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        with self.neo4j_client.session() as session:
            # Prepare header parameters
            header_params = [
                {
                    "proxy_name": proxy_name,
                    "header_name": h.header_name,
                    "header_value": h.header_value,
                    "header_type": h.header_type,
                    "created_at": h.created_at.isoformat(),
                    "updated_at": h.updated_at.isoformat(),
                    "source_timestamp": (
                        h.source_timestamp.isoformat() if h.source_timestamp else None
                    ),
                    "extraction_tier": h.extraction_tier,
                    "extraction_method": h.extraction_method,
                    "confidence": h.confidence,
                    "extractor_version": h.extractor_version,
                }
                for h in headers
            ]

            # Execute in batches
            for i in range(0, len(header_params), self.batch_size):
                batch = header_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (p:Proxy {name: row.proxy_name})
                MERGE (ph:ProxyHeader {
                    header_name: row.header_name,
                    header_value: row.header_value,
                    header_type: row.header_type,
                    proxy_name: row.proxy_name
                })
                SET ph.created_at = row.created_at,
                    ph.updated_at = row.updated_at,
                    ph.source_timestamp = row.source_timestamp,
                    ph.extraction_tier = row.extraction_tier,
                    ph.extraction_method = row.extraction_method,
                    ph.confidence = row.confidence,
                    ph.extractor_version = row.extractor_version
                MERGE (p)-[r:HAS_HEADER]->(ph)
                RETURN count(ph) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote ProxyHeader batch {batches_executed}: "
                    f"{len(batch)} headers, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} ProxyHeader node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}


# Export public API
__all__ = ["SwagGraphWriter"]
