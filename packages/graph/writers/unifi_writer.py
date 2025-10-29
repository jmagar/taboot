"""UnifiWriter - Batched Neo4j writer for Unifi ingestion.

Implements batched UNWIND operations for high throughput.
Handles all 9 Unifi entity types:
- UnifiDevice, UnifiClient, UnifiNetwork, UnifiSite
- PortForwardingRule, FirewallRule, TrafficRule, TrafficRoute, NATRule

Performance target: ≥20k edges/min with 2000-row UNWIND batches.
"""

import json
import logging

from packages.graph.client import Neo4jClient
from packages.schemas.unifi import (
    FirewallRule,
    NATRule,
    PortForwardingRule,
    TrafficRoute,
    TrafficRule,
    UnifiClient,
    UnifiDevice,
    UnifiNetwork,
    UnifiSite,
)

logger = logging.getLogger(__name__)


class UnifiWriter:
    """Batched Neo4j writer for Unifi network infrastructure.

    Implements batched UNWIND operations for high throughput.
    Ensures atomic writes and relationship integrity.

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize UnifiWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized UnifiWriter (batch_size={batch_size})")

    def write_devices(self, devices: list[UnifiDevice]) -> dict[str, int]:
        """Write UnifiDevice nodes to Neo4j using batched UNWIND.

        Creates or updates UnifiDevice nodes with all properties.
        Uses MERGE on unique key (mac) for idempotency.

        Args:
            devices: List of UnifiDevice entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total devices written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not devices:
            logger.info("No devices to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare device parameters
        device_params = [
            {
                "mac": d.mac,
                "hostname": d.hostname,
                "type": d.type,
                "model": d.model,
                "adopted": d.adopted,
                "state": d.state,
                "ip": d.ip,
                "firmware_version": d.firmware_version,
                "link_speed": d.link_speed,
                "connection_type": d.connection_type,
                "uptime": d.uptime,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
                "source_timestamp": d.source_timestamp.isoformat() if d.source_timestamp else None,
                "extraction_tier": d.extraction_tier,
                "extraction_method": d.extraction_method,
                "confidence": d.confidence,
                "extractor_version": d.extractor_version,
            }
            for d in devices
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(device_params), self.batch_size):
                batch = device_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (d:UnifiDevice {mac: row.mac})
                SET d.hostname = row.hostname,
                    d.type = row.type,
                    d.model = row.model,
                    d.adopted = row.adopted,
                    d.state = row.state,
                    d.ip = row.ip,
                    d.firmware_version = row.firmware_version,
                    d.link_speed = row.link_speed,
                    d.connection_type = row.connection_type,
                    d.uptime = row.uptime,
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
                    f"Wrote UnifiDevice batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} UnifiDevice node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_clients(self, clients: list[UnifiClient]) -> dict[str, int]:
        """Write UnifiClient nodes to Neo4j using batched UNWIND.

        Creates or updates UnifiClient nodes with all properties.
        Uses MERGE on unique key (mac) for idempotency.

        Args:
            clients: List of UnifiClient entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total clients written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not clients:
            logger.info("No clients to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare client parameters
        client_params = [
            {
                "mac": c.mac,
                "hostname": c.hostname,
                "ip": c.ip,
                "network": c.network,
                "is_wired": c.is_wired,
                "link_speed": c.link_speed,
                "connection_type": c.connection_type,
                "uptime": c.uptime,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
                "source_timestamp": c.source_timestamp.isoformat() if c.source_timestamp else None,
                "extraction_tier": c.extraction_tier,
                "extraction_method": c.extraction_method,
                "confidence": c.confidence,
                "extractor_version": c.extractor_version,
            }
            for c in clients
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(client_params), self.batch_size):
                batch = client_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (c:UnifiClient {mac: row.mac})
                SET c.hostname = row.hostname,
                    c.ip = row.ip,
                    c.network = row.network,
                    c.is_wired = row.is_wired,
                    c.link_speed = row.link_speed,
                    c.connection_type = row.connection_type,
                    c.uptime = row.uptime,
                    c.created_at = row.created_at,
                    c.updated_at = row.updated_at,
                    c.source_timestamp = row.source_timestamp,
                    c.extraction_tier = row.extraction_tier,
                    c.extraction_method = row.extraction_method,
                    c.confidence = row.confidence,
                    c.extractor_version = row.extractor_version
                RETURN count(c) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote UnifiClient batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} UnifiClient node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_networks(self, networks: list[UnifiNetwork]) -> dict[str, int]:
        """Write UnifiNetwork nodes to Neo4j using batched UNWIND.

        Creates or updates UnifiNetwork nodes with all properties.
        Uses MERGE on unique key (network_id) for idempotency.

        Args:
            networks: List of UnifiNetwork entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total networks written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not networks:
            logger.info("No networks to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare network parameters
        network_params = [
            {
                "network_id": n.network_id,
                "name": n.name,
                "vlan_id": n.vlan_id,
                "subnet": n.subnet,
                "gateway_ip": n.gateway_ip,
                "dns_servers": n.dns_servers,
                "wifi_name": n.wifi_name,
                "created_at": n.created_at.isoformat(),
                "updated_at": n.updated_at.isoformat(),
                "source_timestamp": n.source_timestamp.isoformat() if n.source_timestamp else None,
                "extraction_tier": n.extraction_tier,
                "extraction_method": n.extraction_method,
                "confidence": n.confidence,
                "extractor_version": n.extractor_version,
            }
            for n in networks
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(network_params), self.batch_size):
                batch = network_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (n:UnifiNetwork {network_id: row.network_id})
                SET n.name = row.name,
                    n.vlan_id = row.vlan_id,
                    n.subnet = row.subnet,
                    n.gateway_ip = row.gateway_ip,
                    n.dns_servers = row.dns_servers,
                    n.wifi_name = row.wifi_name,
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
                    f"Wrote UnifiNetwork batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} UnifiNetwork node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_sites(self, sites: list[UnifiSite]) -> dict[str, int]:
        """Write UnifiSite nodes to Neo4j using batched UNWIND.

        Creates or updates UnifiSite nodes with all properties.
        Uses MERGE on unique key (site_id) for idempotency.

        Args:
            sites: List of UnifiSite entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total sites written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not sites:
            logger.info("No sites to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare site parameters
        site_params = [
            {
                "site_id": s.site_id,
                "name": s.name,
                "description": s.description,
                "wan_ip": s.wan_ip,
                "gateway_ip": s.gateway_ip,
                "dns_servers": s.dns_servers,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "source_timestamp": s.source_timestamp.isoformat() if s.source_timestamp else None,
                "extraction_tier": s.extraction_tier,
                "extraction_method": s.extraction_method,
                "confidence": s.confidence,
                "extractor_version": s.extractor_version,
            }
            for s in sites
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(site_params), self.batch_size):
                batch = site_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (s:UnifiSite {site_id: row.site_id})
                SET s.name = row.name,
                    s.description = row.description,
                    s.wan_ip = row.wan_ip,
                    s.gateway_ip = row.gateway_ip,
                    s.dns_servers = row.dns_servers,
                    s.created_at = row.created_at,
                    s.updated_at = row.updated_at,
                    s.source_timestamp = row.source_timestamp,
                    s.extraction_tier = row.extraction_tier,
                    s.extraction_method = row.extraction_method,
                    s.confidence = row.confidence,
                    s.extractor_version = row.extractor_version
                RETURN count(s) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote UnifiSite batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} UnifiSite node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_port_forwarding_rules(
        self, rules: list[PortForwardingRule]
    ) -> dict[str, int]:
        """Write PortForwardingRule nodes to Neo4j using batched UNWIND.

        Creates or updates PortForwardingRule nodes with all properties.
        Uses MERGE on unique key (rule_id) for idempotency.

        Args:
            rules: List of PortForwardingRule entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total rules written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not rules:
            logger.info("No port forwarding rules to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare rule parameters
        rule_params = [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "enabled": r.enabled,
                "proto": r.proto,
                "src": r.src,
                "dst_port": r.dst_port,
                "fwd": r.fwd,
                "fwd_port": r.fwd_port,
                "pfwd_interface": r.pfwd_interface,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "source_timestamp": r.source_timestamp.isoformat() if r.source_timestamp else None,
                "extraction_tier": r.extraction_tier,
                "extraction_method": r.extraction_method,
                "confidence": r.confidence,
                "extractor_version": r.extractor_version,
            }
            for r in rules
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(rule_params), self.batch_size):
                batch = rule_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (r:PortForwardingRule {rule_id: row.rule_id})
                SET r.name = row.name,
                    r.enabled = row.enabled,
                    r.proto = row.proto,
                    r.src = row.src,
                    r.dst_port = row.dst_port,
                    r.fwd = row.fwd,
                    r.fwd_port = row.fwd_port,
                    r.pfwd_interface = row.pfwd_interface,
                    r.created_at = row.created_at,
                    r.updated_at = row.updated_at,
                    r.source_timestamp = row.source_timestamp,
                    r.extraction_tier = row.extraction_tier,
                    r.extraction_method = row.extraction_method,
                    r.confidence = row.confidence,
                    r.extractor_version = row.extractor_version
                RETURN count(r) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote PortForwardingRule batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(
            f"Wrote {total_written} PortForwardingRule node(s) in {batches_executed} batch(es)"
        )

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_firewall_rules(self, rules: list[FirewallRule]) -> dict[str, int]:
        """Write FirewallRule nodes to Neo4j using batched UNWIND.

        Creates or updates FirewallRule nodes with all properties.
        Uses MERGE on unique key (rule_id) for idempotency.

        Args:
            rules: List of FirewallRule entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total rules written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not rules:
            logger.info("No firewall rules to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare rule parameters
        rule_params = [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "enabled": r.enabled,
                "action": r.action,
                "protocol": r.protocol,
                "ip_version": r.ip_version,
                "index": r.index,
                "source_zone": r.source_zone,
                "dest_zone": r.dest_zone,
                "logging": r.logging,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "source_timestamp": r.source_timestamp.isoformat() if r.source_timestamp else None,
                "extraction_tier": r.extraction_tier,
                "extraction_method": r.extraction_method,
                "confidence": r.confidence,
                "extractor_version": r.extractor_version,
            }
            for r in rules
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(rule_params), self.batch_size):
                batch = rule_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (r:FirewallRule {rule_id: row.rule_id})
                SET r.name = row.name,
                    r.enabled = row.enabled,
                    r.action = row.action,
                    r.protocol = row.protocol,
                    r.ip_version = row.ip_version,
                    r.index = row.index,
                    r.source_zone = row.source_zone,
                    r.dest_zone = row.dest_zone,
                    r.logging = row.logging,
                    r.created_at = row.created_at,
                    r.updated_at = row.updated_at,
                    r.source_timestamp = row.source_timestamp,
                    r.extraction_tier = row.extraction_tier,
                    r.extraction_method = row.extraction_method,
                    r.confidence = row.confidence,
                    r.extractor_version = row.extractor_version
                RETURN count(r) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote FirewallRule batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(
            f"Wrote {total_written} FirewallRule node(s) in {batches_executed} batch(es)"
        )

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_traffic_rules(self, rules: list[TrafficRule]) -> dict[str, int]:
        """Write TrafficRule nodes to Neo4j using batched UNWIND.

        Creates or updates TrafficRule nodes with all properties.
        Uses MERGE on unique key (rule_id) for idempotency.

        Args:
            rules: List of TrafficRule entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total rules written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not rules:
            logger.info("No traffic rules to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare rule parameters (convert bandwidth_limit dict to JSON string)
        rule_params = [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "enabled": r.enabled,
                "action": r.action,
                "bandwidth_limit": json.dumps(r.bandwidth_limit) if r.bandwidth_limit else None,
                "matching_target": r.matching_target,
                "ip_addresses": r.ip_addresses,
                "domains": r.domains,
                "schedule": r.schedule,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "source_timestamp": r.source_timestamp.isoformat() if r.source_timestamp else None,
                "extraction_tier": r.extraction_tier,
                "extraction_method": r.extraction_method,
                "confidence": r.confidence,
                "extractor_version": r.extractor_version,
            }
            for r in rules
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(rule_params), self.batch_size):
                batch = rule_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (r:TrafficRule {rule_id: row.rule_id})
                SET r.name = row.name,
                    r.enabled = row.enabled,
                    r.action = row.action,
                    r.bandwidth_limit = row.bandwidth_limit,
                    r.matching_target = row.matching_target,
                    r.ip_addresses = row.ip_addresses,
                    r.domains = row.domains,
                    r.schedule = row.schedule,
                    r.created_at = row.created_at,
                    r.updated_at = row.updated_at,
                    r.source_timestamp = row.source_timestamp,
                    r.extraction_tier = row.extraction_tier,
                    r.extraction_method = row.extraction_method,
                    r.confidence = row.confidence,
                    r.extractor_version = row.extractor_version
                RETURN count(r) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote TrafficRule batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(
            f"Wrote {total_written} TrafficRule node(s) in {batches_executed} batch(es)"
        )

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_traffic_routes(self, routes: list[TrafficRoute]) -> dict[str, int]:
        """Write TrafficRoute nodes to Neo4j using batched UNWIND.

        Creates or updates TrafficRoute nodes with all properties.
        Uses MERGE on unique key (route_id) for idempotency.

        Args:
            routes: List of TrafficRoute entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total routes written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not routes:
            logger.info("No traffic routes to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare route parameters
        route_params = [
            {
                "route_id": r.route_id,
                "name": r.name,
                "enabled": r.enabled,
                "next_hop": r.next_hop,
                "matching_target": r.matching_target,
                "network_id": r.network_id,
                "ip_addresses": r.ip_addresses,
                "domains": r.domains,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "source_timestamp": r.source_timestamp.isoformat() if r.source_timestamp else None,
                "extraction_tier": r.extraction_tier,
                "extraction_method": r.extraction_method,
                "confidence": r.confidence,
                "extractor_version": r.extractor_version,
            }
            for r in routes
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(route_params), self.batch_size):
                batch = route_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (r:TrafficRoute {route_id: row.route_id})
                SET r.name = row.name,
                    r.enabled = row.enabled,
                    r.next_hop = row.next_hop,
                    r.matching_target = row.matching_target,
                    r.network_id = row.network_id,
                    r.ip_addresses = row.ip_addresses,
                    r.domains = row.domains,
                    r.created_at = row.created_at,
                    r.updated_at = row.updated_at,
                    r.source_timestamp = row.source_timestamp,
                    r.extraction_tier = row.extraction_tier,
                    r.extraction_method = row.extraction_method,
                    r.confidence = row.confidence,
                    r.extractor_version = row.extractor_version
                RETURN count(r) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote TrafficRoute batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(
            f"Wrote {total_written} TrafficRoute node(s) in {batches_executed} batch(es)"
        )

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_nat_rules(self, rules: list[NATRule]) -> dict[str, int]:
        """Write NATRule nodes to Neo4j using batched UNWIND.

        Creates or updates NATRule nodes with all properties.
        Uses MERGE on unique key (rule_id) for idempotency.

        Args:
            rules: List of NATRule entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total rules written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not rules:
            logger.info("No NAT rules to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare rule parameters
        rule_params = [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "enabled": r.enabled,
                "type": r.type,
                "source": r.source,
                "destination": r.destination,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "source_timestamp": r.source_timestamp.isoformat() if r.source_timestamp else None,
                "extraction_tier": r.extraction_tier,
                "extraction_method": r.extraction_method,
                "confidence": r.confidence,
                "extractor_version": r.extractor_version,
            }
            for r in rules
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(rule_params), self.batch_size):
                batch = rule_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (r:NATRule {rule_id: row.rule_id})
                SET r.name = row.name,
                    r.enabled = row.enabled,
                    r.type = row.type,
                    r.source = row.source,
                    r.destination = row.destination,
                    r.created_at = row.created_at,
                    r.updated_at = row.updated_at,
                    r.source_timestamp = row.source_timestamp,
                    r.extraction_tier = row.extraction_tier,
                    r.extraction_method = row.extraction_method,
                    r.confidence = row.confidence,
                    r.extractor_version = row.extractor_version
                RETURN count(r) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote NATRule batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} NATRule node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}


# Export public API
__all__ = ["UnifiWriter"]
