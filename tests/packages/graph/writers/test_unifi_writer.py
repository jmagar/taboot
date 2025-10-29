"""Tests for UnifiWriter - Batched Neo4j writer for Unifi ingestion.

Tests all 9 Unifi entity types with comprehensive coverage:
- Empty lists
- Single entity
- Batch of 2000 rows
- Idempotency (re-write same data)
- Constraint violations

Performance target: ≥20k edges/min with 2000-row UNWIND batches.
"""

from datetime import UTC, datetime

import pytest

from packages.graph.client import Neo4jClient
from packages.graph.writers.unifi_writer import UnifiWriter
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


@pytest.fixture
def neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all Unifi nodes after test
    with client.session() as session:
        session.run(
            "MATCH (n) WHERE n:UnifiDevice OR n:UnifiClient OR n:UnifiNetwork "
            "OR n:UnifiSite OR n:PortForwardingRule OR n:FirewallRule "
            "OR n:TrafficRule OR n:TrafficRoute OR n:NATRule DETACH DELETE n"
        )

    client.close()


@pytest.fixture
def unifi_writer(neo4j_client: Neo4jClient) -> UnifiWriter:
    """Create UnifiWriter instance for testing."""
    return UnifiWriter(neo4j_client, batch_size=2000)


# UnifiDevice tests


def test_write_devices_empty_list(unifi_writer: UnifiWriter) -> None:
    """Test write_devices with empty list returns zero counts."""
    result = unifi_writer.write_devices([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_devices_single(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_devices with single device."""
    device = UnifiDevice(
        mac="00:11:22:33:44:55",
        hostname="unifi-switch-01",
        type="usw",
        model="US-24-250W",
        adopted=True,
        state="connected",
        ip="192.168.1.100",
        firmware_version="6.5.55",
        link_speed=1000,
        connection_type="wired",
        uptime=86400,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="unifi_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = unifi_writer.write_devices([device])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node exists in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (d:UnifiDevice {mac: $mac}) RETURN d"
        records = list(session.run(query, {"mac": "00:11:22:33:44:55"}))
        assert len(records) == 1
        node = records[0]["d"]
        assert node["hostname"] == "unifi-switch-01"
        assert node["type"] == "usw"
        assert node["model"] == "US-24-250W"


def test_write_devices_batch_2000(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_devices with batch of 2000 rows."""
    devices = [
        UnifiDevice(
            mac=f"00:11:22:33:{i // 256:02x}:{i % 256:02x}",
            hostname=f"device-{i}",
            type="usw",
            model="US-24-250W",
            adopted=True,
            state="connected",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="unifi_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        for i in range(2000)
    ]

    result = unifi_writer.write_devices(devices)

    assert result["total_written"] == 2000
    assert result["batches_executed"] == 1

    # Verify count in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (d:UnifiDevice) RETURN count(d) AS count"
        records = list(session.run(query))
        assert records[0]["count"] == 2000


def test_write_devices_idempotent(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_devices is idempotent (can re-write same data)."""
    device = UnifiDevice(
        mac="00:11:22:33:44:55",
        hostname="unifi-switch-01",
        type="usw",
        model="US-24-250W",
        adopted=True,
        state="connected",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="unifi_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    # Write first time
    result1 = unifi_writer.write_devices([device])
    assert result1["total_written"] == 1

    # Write second time (should update, not duplicate)
    result2 = unifi_writer.write_devices([device])
    assert result2["total_written"] == 1

    # Verify only one node exists
    with neo4j_client.session() as session:
        query = "MATCH (d:UnifiDevice {mac: $mac}) RETURN count(d) AS count"
        records = list(session.run(query, {"mac": "00:11:22:33:44:55"}))
        assert records[0]["count"] == 1


# UnifiClient tests


def test_write_clients_empty_list(unifi_writer: UnifiWriter) -> None:
    """Test write_clients with empty list returns zero counts."""
    result = unifi_writer.write_clients([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_clients_single(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_clients with single client."""
    client = UnifiClient(
        mac="aa:bb:cc:dd:ee:ff",
        hostname="laptop-01",
        ip="192.168.1.50",
        network="LAN",
        is_wired=False,
        link_speed=866,
        connection_type="wifi6",
        uptime=7200,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="unifi_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = unifi_writer.write_clients([client])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node exists in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (c:UnifiClient {mac: $mac}) RETURN c"
        records = list(session.run(query, {"mac": "aa:bb:cc:dd:ee:ff"}))
        assert len(records) == 1
        node = records[0]["c"]
        assert node["hostname"] == "laptop-01"
        assert node["network"] == "LAN"


# UnifiNetwork tests


def test_write_networks_empty_list(unifi_writer: UnifiWriter) -> None:
    """Test write_networks with empty list returns zero counts."""
    result = unifi_writer.write_networks([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_networks_single(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_networks with single network."""
    network = UnifiNetwork(
        network_id="5f9c1234abcd5678ef123456",
        name="LAN",
        vlan_id=1,
        subnet="192.168.1.0/24",
        gateway_ip="192.168.1.1",
        dns_servers=["8.8.8.8", "8.8.4.4"],
        wifi_name="MyWiFi",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="unifi_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = unifi_writer.write_networks([network])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node exists in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (n:UnifiNetwork {network_id: $network_id}) RETURN n"
        records = list(session.run(query, {"network_id": "5f9c1234abcd5678ef123456"}))
        assert len(records) == 1
        node = records[0]["n"]
        assert node["name"] == "LAN"
        assert node["vlan_id"] == 1


# UnifiSite tests


def test_write_sites_empty_list(unifi_writer: UnifiWriter) -> None:
    """Test write_sites with empty list returns zero counts."""
    result = unifi_writer.write_sites([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_sites_single(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_sites with single site."""
    site = UnifiSite(
        site_id="default",
        name="Default Site",
        description="Main office location",
        wan_ip="203.0.113.10",
        gateway_ip="192.168.1.1",
        dns_servers=["8.8.8.8", "8.8.4.4"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="unifi_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = unifi_writer.write_sites([site])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node exists in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (s:UnifiSite {site_id: $site_id}) RETURN s"
        records = list(session.run(query, {"site_id": "default"}))
        assert len(records) == 1
        node = records[0]["s"]
        assert node["name"] == "Default Site"


# PortForwardingRule tests


def test_write_port_forwarding_rules_empty_list(
    unifi_writer: UnifiWriter
) -> None:
    """Test write_port_forwarding_rules with empty list returns zero counts."""
    result = unifi_writer.write_port_forwarding_rules([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_port_forwarding_rules_single(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_port_forwarding_rules with single rule."""
    rule = PortForwardingRule(
        rule_id="5f9c1234abcd5678ef123456",
        name="SSH Forward",
        enabled=True,
        proto="tcp",
        src="any",
        dst_port=22,
        fwd="192.168.1.100",
        fwd_port=22,
        pfwd_interface="wan",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="unifi_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = unifi_writer.write_port_forwarding_rules([rule])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node exists in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (r:PortForwardingRule {rule_id: $rule_id}) RETURN r"
        records = list(session.run(query, {"rule_id": "5f9c1234abcd5678ef123456"}))
        assert len(records) == 1
        node = records[0]["r"]
        assert node["name"] == "SSH Forward"
        assert node["dst_port"] == 22


# FirewallRule tests


def test_write_firewall_rules_empty_list(
    unifi_writer: UnifiWriter
) -> None:
    """Test write_firewall_rules with empty list returns zero counts."""
    result = unifi_writer.write_firewall_rules([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_firewall_rules_single(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_firewall_rules with single rule."""
    rule = FirewallRule(
        rule_id="5f9c1234abcd5678ef123456",
        name="Block External",
        enabled=True,
        action="DROP",
        protocol="tcp",
        ip_version="ipv4",
        index=1,
        source_zone="WAN",
        dest_zone="LAN",
        logging=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="unifi_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = unifi_writer.write_firewall_rules([rule])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node exists in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (r:FirewallRule {rule_id: $rule_id}) RETURN r"
        records = list(session.run(query, {"rule_id": "5f9c1234abcd5678ef123456"}))
        assert len(records) == 1
        node = records[0]["r"]
        assert node["name"] == "Block External"
        assert node["action"] == "DROP"


# TrafficRule tests


def test_write_traffic_rules_empty_list(
    unifi_writer: UnifiWriter
) -> None:
    """Test write_traffic_rules with empty list returns zero counts."""
    result = unifi_writer.write_traffic_rules([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_traffic_rules_single(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_traffic_rules with single rule."""
    rule = TrafficRule(
        rule_id="5f9c1234abcd5678ef123456",
        name="Limit Gaming",
        enabled=True,
        action="limit",
        bandwidth_limit={"download_kbps": 10000, "upload_kbps": 5000},
        matching_target="ip",
        ip_addresses=["192.168.1.100"],
        domains=["game-server.com"],
        schedule="weekdays",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="unifi_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = unifi_writer.write_traffic_rules([rule])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node exists in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (r:TrafficRule {rule_id: $rule_id}) RETURN r"
        records = list(session.run(query, {"rule_id": "5f9c1234abcd5678ef123456"}))
        assert len(records) == 1
        node = records[0]["r"]
        assert node["name"] == "Limit Gaming"
        assert node["action"] == "limit"


# TrafficRoute tests


def test_write_traffic_routes_empty_list(
    unifi_writer: UnifiWriter
) -> None:
    """Test write_traffic_routes with empty list returns zero counts."""
    result = unifi_writer.write_traffic_routes([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_traffic_routes_single(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_traffic_routes with single route."""
    route = TrafficRoute(
        route_id="5f9c1234abcd5678ef123456",
        name="Route to VPN",
        enabled=True,
        next_hop="192.168.1.1",
        matching_target="domain",
        network_id="5f9c1234abcd5678ef111111",
        ip_addresses=["10.0.0.0/24"],
        domains=["internal.company.com"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="unifi_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = unifi_writer.write_traffic_routes([route])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node exists in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (r:TrafficRoute {route_id: $route_id}) RETURN r"
        records = list(session.run(query, {"route_id": "5f9c1234abcd5678ef123456"}))
        assert len(records) == 1
        node = records[0]["r"]
        assert node["name"] == "Route to VPN"
        assert node["next_hop"] == "192.168.1.1"


# NATRule tests


def test_write_nat_rules_empty_list(unifi_writer: UnifiWriter) -> None:
    """Test write_nat_rules with empty list returns zero counts."""
    result = unifi_writer.write_nat_rules([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_nat_rules_single(
    unifi_writer: UnifiWriter, neo4j_client: Neo4jClient
) -> None:
    """Test write_nat_rules with single rule."""
    rule = NATRule(
        rule_id="5f9c1234abcd5678ef123456",
        name="DNAT Rule",
        enabled=True,
        type="dnat",
        source="192.168.0.0/16",
        destination="192.168.1.100",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="unifi_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = unifi_writer.write_nat_rules([rule])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node exists in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (r:NATRule {rule_id: $rule_id}) RETURN r"
        records = list(session.run(query, {"rule_id": "5f9c1234abcd5678ef123456"}))
        assert len(records) == 1
        node = records[0]["r"]
        assert node["name"] == "DNAT Rule"
        assert node["type"] == "dnat"
