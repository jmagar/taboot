"""TailscaleWriter - Batched Neo4j writer for Tailscale entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/swag_writer.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.

Handles three Tailscale entity types:
- TailscaleDevice: Devices/nodes in the tailnet mesh
- TailscaleNetwork: Network segments and subnets
- TailscaleACL: Access control list rules
"""

import logging

from packages.graph.client import Neo4jClient
from packages.schemas.tailscale import TailscaleACL, TailscaleDevice, TailscaleNetwork

logger = logging.getLogger(__name__)


class TailscaleWriter:
    """Batched Neo4j writer for Tailscale entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize TailscaleWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized TailscaleWriter (batch_size={batch_size})")

    def write_devices(self, devices: list[TailscaleDevice]) -> dict[str, int]:
        """Write TailscaleDevice nodes to Neo4j using batched UNWIND.

        Creates or updates TailscaleDevice nodes with all properties.
        Uses MERGE on unique key (device_id) for idempotency.

        Args:
            devices: List of TailscaleDevice entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total devices written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If devices list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not devices:
            logger.info("No devices to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare device parameters
        try:
            device_params = [
                {
                    "device_id": d.device_id,
                    "hostname": d.hostname,
                    "long_domain": d.long_domain,
                    "os": d.os,
                    "ipv4_address": d.ipv4_address,
                    "ipv6_address": d.ipv6_address,
                    "endpoints": d.endpoints,
                    "key_expiry": d.key_expiry.isoformat() if d.key_expiry else None,
                    "is_exit_node": d.is_exit_node,
                    "subnet_routes": d.subnet_routes,
                    "ssh_enabled": d.ssh_enabled,
                    "tailnet_dns_name": d.tailnet_dns_name,
                    "created_at": d.created_at.isoformat(),
                    "updated_at": d.updated_at.isoformat(),
                    "source_timestamp": (
                        d.source_timestamp.isoformat() if d.source_timestamp else None
                    ),
                    "extraction_tier": d.extraction_tier,
                    "extraction_method": d.extraction_method,
                    "confidence": d.confidence,
                    "extractor_version": d.extractor_version,
                }
                for d in devices
            ]
        except AttributeError as e:
            logger.error(f"Invalid TailscaleDevice entity in batch: {e}")
            raise ValueError(f"Invalid TailscaleDevice entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(device_params), self.batch_size):
                    batch = device_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (d:TailscaleDevice {device_id: row.device_id})
                    SET d.hostname = row.hostname,
                        d.os = row.os,
                        d.long_domain = row.long_domain,
                        d.ipv4_address = row.ipv4_address,
                        d.ipv6_address = row.ipv6_address,
                        d.endpoints = row.endpoints,
                        d.key_expiry = row.key_expiry,
                        d.is_exit_node = row.is_exit_node,
                        d.subnet_routes = row.subnet_routes,
                        d.ssh_enabled = row.ssh_enabled,
                        d.tailnet_dns_name = row.tailnet_dns_name,
                        d.created_at = row.created_at,
                        d.updated_at = row.updated_at,
                        d.source_timestamp = row.source_timestamp,
                        d.extraction_tier = row.extraction_tier,
                        d.extraction_method = row.extraction_method,
                        d.confidence = row.confidence,
                        d.extractor_version = row.extractor_version
                    RETURN count(d) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote TailscaleDevice batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} TailscaleDevice node(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write TailscaleDevices to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_devices": len(devices)},
            )
            raise

    def write_networks(self, networks: list[TailscaleNetwork]) -> dict[str, int]:
        """Write TailscaleNetwork nodes to Neo4j using batched UNWIND.

        Creates or updates TailscaleNetwork nodes with all properties.
        Uses MERGE on unique key (network_id) for idempotency.

        Args:
            networks: List of TailscaleNetwork entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total networks written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If networks list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not networks:
            logger.info("No networks to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare network parameters
        try:
            network_params = [
                {
                    "network_id": n.network_id,
                    "name": n.name,
                    "cidr": n.cidr,
                    "global_nameservers": n.global_nameservers,
                    "search_domains": n.search_domains,
                    "created_at": n.created_at.isoformat(),
                    "updated_at": n.updated_at.isoformat(),
                    "source_timestamp": (
                        n.source_timestamp.isoformat() if n.source_timestamp else None
                    ),
                    "extraction_tier": n.extraction_tier,
                    "extraction_method": n.extraction_method,
                    "confidence": n.confidence,
                    "extractor_version": n.extractor_version,
                }
                for n in networks
            ]
        except AttributeError as e:
            logger.error(f"Invalid TailscaleNetwork entity in batch: {e}")
            raise ValueError(f"Invalid TailscaleNetwork entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(network_params), self.batch_size):
                    batch = network_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (n:TailscaleNetwork {network_id: row.network_id})
                    SET n.name = row.name,
                        n.cidr = row.cidr,
                        n.global_nameservers = row.global_nameservers,
                        n.search_domains = row.search_domains,
                        n.created_at = row.created_at,
                        n.updated_at = row.updated_at,
                        n.source_timestamp = row.source_timestamp,
                        n.extraction_tier = row.extraction_tier,
                        n.extraction_method = row.extraction_method,
                        n.confidence = row.confidence,
                        n.extractor_version = row.extractor_version
                    RETURN count(n) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote TailscaleNetwork batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} TailscaleNetwork node(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write TailscaleNetworks to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_networks": len(networks)},
            )
            raise

    def write_acls(self, acls: list[TailscaleACL]) -> dict[str, int]:
        """Write TailscaleACL nodes to Neo4j using batched UNWIND.

        Creates or updates TailscaleACL nodes with all properties.
        Uses MERGE on unique key (rule_id) for idempotency.

        Args:
            acls: List of TailscaleACL entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total ACLs written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If acls list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not acls:
            logger.info("No ACLs to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare ACL parameters
        try:
            acl_params = [
                {
                    "rule_id": a.rule_id,
                    "action": a.action,
                    "source_tags": a.source_tags,
                    "destination_tags": a.destination_tags,
                    "ports": a.ports,
                    "created_at": a.created_at.isoformat(),
                    "updated_at": a.updated_at.isoformat(),
                    "source_timestamp": (
                        a.source_timestamp.isoformat() if a.source_timestamp else None
                    ),
                    "extraction_tier": a.extraction_tier,
                    "extraction_method": a.extraction_method,
                    "confidence": a.confidence,
                    "extractor_version": a.extractor_version,
                }
                for a in acls
            ]
        except AttributeError as e:
            logger.error(f"Invalid TailscaleACL entity in batch: {e}")
            raise ValueError(f"Invalid TailscaleACL entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(acl_params), self.batch_size):
                    batch = acl_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (a:TailscaleACL {rule_id: row.rule_id})
                    SET a.action = row.action,
                        a.source_tags = row.source_tags,
                        a.destination_tags = row.destination_tags,
                        a.ports = row.ports,
                        a.created_at = row.created_at,
                        a.updated_at = row.updated_at,
                        a.source_timestamp = row.source_timestamp,
                        a.extraction_tier = row.extraction_tier,
                        a.extraction_method = row.extraction_method,
                        a.confidence = row.confidence,
                        a.extractor_version = row.extractor_version
                    RETURN count(a) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote TailscaleACL batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} TailscaleACL node(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write TailscaleACLs to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_acls": len(acls)},
            )
            raise

    def write_device_in_network(self, device_id: str, network_id: str) -> dict[str, int]:
        """Write BELONGS_TO relationship between device and network.

        Creates a BELONGS_TO relationship from TailscaleDevice to TailscaleNetwork.

        Args:
            device_id: Device ID (must exist in Neo4j).
            network_id: Network ID (must exist in Neo4j).

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total relationships written (1)
                - batches_executed: Number of batches executed (1)

        Raises:
            ValueError: If device_id or network_id is empty.
            Exception: If Neo4j write operation fails.
        """
        if not device_id or not network_id:
            raise ValueError("device_id and network_id cannot be empty")

        try:
            with self.neo4j_client.session() as session:
                query = """
                MATCH (d:TailscaleDevice {device_id: $device_id})
                MATCH (n:TailscaleNetwork {network_id: $network_id})
                MERGE (d)-[r:BELONGS_TO]->(n)
                RETURN count(r) AS created_count
                """

                result = session.run(query, {"device_id": device_id, "network_id": network_id})
                summary = result.consume()

                logger.debug(
                    f"Wrote BELONGS_TO relationship: device={device_id}, network={network_id}, "
                    f"counters={summary.counters}"
                )

            logger.info(
                f"Wrote BELONGS_TO relationship between device {device_id} and network {network_id}"
            )

            return {"total_written": 1, "batches_executed": 1}

        except Exception as e:
            logger.error(
                f"Failed to write device-network relationship: {e}",
                extra={"device_id": device_id, "network_id": network_id},
            )
            raise

    def write_acl_applies_to_device(self, rule_id: str, device_id: str) -> dict[str, int]:
        """Write APPLIES_TO relationship between ACL and device.

        Creates an APPLIES_TO relationship from TailscaleACL to TailscaleDevice.

        Args:
            rule_id: ACL rule ID (must exist in Neo4j).
            device_id: Device ID (must exist in Neo4j).

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total relationships written (1)
                - batches_executed: Number of batches executed (1)

        Raises:
            ValueError: If rule_id or device_id is empty.
            Exception: If Neo4j write operation fails.
        """
        if not rule_id or not device_id:
            raise ValueError("rule_id and device_id cannot be empty")

        try:
            with self.neo4j_client.session() as session:
                query = """
                MATCH (a:TailscaleACL {rule_id: $rule_id})
                MATCH (d:TailscaleDevice {device_id: $device_id})
                MERGE (a)-[r:APPLIES_TO]->(d)
                RETURN count(r) AS created_count
                """

                result = session.run(query, {"rule_id": rule_id, "device_id": device_id})
                summary = result.consume()

                logger.debug(
                    f"Wrote APPLIES_TO relationship: acl={rule_id}, device={device_id}, "
                    f"counters={summary.counters}"
                )

            logger.info(
                f"Wrote APPLIES_TO relationship between ACL {rule_id} and device {device_id}"
            )

            return {"total_written": 1, "batches_executed": 1}

        except Exception as e:
            logger.error(
                f"Failed to write ACL-device relationship: {e}",
                extra={"rule_id": rule_id, "device_id": device_id},
            )
            raise


# Export public API
__all__ = ["TailscaleWriter"]
