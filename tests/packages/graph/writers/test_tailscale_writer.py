"""Tests for TailscaleWriter following TDD red-green-refactor pattern.

Tests cover:
- Empty list handling
- Single entity write (device, network, ACL)
- Batch 2000 write
- Idempotent writes (same data written twice)
- Relationships between entities
"""

from datetime import UTC, datetime

import pytest

from packages.graph.client import Neo4jClient
from packages.graph.writers.tailscale_writer import TailscaleWriter
from packages.schemas.tailscale import TailscaleACL, TailscaleDevice, TailscaleNetwork


@pytest.fixture
def neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all Tailscale nodes after test
    with client.session() as session:
        session.run(
            "MATCH (n) WHERE n:TailscaleDevice OR n:TailscaleNetwork OR n:TailscaleACL "
            "DETACH DELETE n"
        )

    client.close()


@pytest.fixture
def tailscale_writer(neo4j_client: Neo4jClient) -> TailscaleWriter:
    """Create TailscaleWriter instance."""
    return TailscaleWriter(neo4j_client=neo4j_client, batch_size=2000)


@pytest.fixture
def sample_device() -> TailscaleDevice:
    """Create a sample TailscaleDevice entity."""
    return TailscaleDevice(
        device_id="ts-device-123",
        hostname="gateway.example.com",
        long_domain="gateway.example.com",
        os="linux",
        ipv4_address="100.64.1.5",
        ipv6_address="fd7a:115c:a1e0::1",
        endpoints=["192.168.1.100:41641", "203.0.113.50:41641"],
        key_expiry=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
        is_exit_node=True,
        subnet_routes=["10.0.0.0/24", "10.1.0.0/24"],
        ssh_enabled=True,
        tailnet_dns_name="gateway.tailnet-abc.ts.net",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 15, 9, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="tailscale_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_network() -> TailscaleNetwork:
    """Create a sample TailscaleNetwork entity."""
    return TailscaleNetwork(
        network_id="net-123",
        name="main-network",
        cidr="100.64.0.0/10",
        global_nameservers=["8.8.8.8", "1.1.1.1"],
        search_domains=["example.com", "internal.local"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 15, 9, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="tailscale_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_acl() -> TailscaleACL:
    """Create a sample TailscaleACL entity."""
    return TailscaleACL(
        rule_id="acl-rule-123",
        action="accept",
        source_tags=["tag:production"],
        destination_tags=["tag:database"],
        ports=["3306", "5432"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 15, 9, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="tailscale_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_devices_batch() -> list[TailscaleDevice]:
    """Create a batch of 2500 TailscaleDevice entities (exceeds batch_size)."""
    devices = []
    for i in range(2500):
        devices.append(
            TailscaleDevice(
                device_id=f"ts-device-{i}",
                hostname=f"device{i}.example.com",
                os="linux",
                ipv4_address=f"100.64.{i // 256}.{i % 256}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        )
    return devices


# TailscaleDevice Tests


def test_write_devices_empty_list(tailscale_writer: TailscaleWriter) -> None:
    """Test writing empty device list returns zero counts."""
    result = tailscale_writer.write_devices([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_devices_single_entity(
    tailscale_writer: TailscaleWriter, sample_device: TailscaleDevice, neo4j_client: Neo4jClient
) -> None:
    """Test writing a single TailscaleDevice entity."""
    result = tailscale_writer.write_devices([sample_device])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node was created in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (d:TailscaleDevice {device_id: $device_id}) RETURN d"
        record = session.run(query, {"device_id": sample_device.device_id}).single()

        assert record is not None
        node = record["d"]
        assert node["device_id"] == sample_device.device_id
        assert node["hostname"] == sample_device.hostname
        assert node["long_domain"] == sample_device.long_domain
        assert node["os"] == sample_device.os
        assert node["ipv4_address"] == sample_device.ipv4_address
        assert node["ipv6_address"] == sample_device.ipv6_address
        assert node["is_exit_node"] == sample_device.is_exit_node
        assert node["ssh_enabled"] == sample_device.ssh_enabled
        assert node["extraction_tier"] == sample_device.extraction_tier


def test_write_devices_batch_2000(
    tailscale_writer: TailscaleWriter,
    sample_devices_batch: list[TailscaleDevice],
    neo4j_client: Neo4jClient,
) -> None:
    """Test writing 2500 devices (requires 2 batches of 2000)."""
    result = tailscale_writer.write_devices(sample_devices_batch)

    assert result["total_written"] == 2500
    assert result["batches_executed"] == 2  # 2000 + 500

    # Verify all nodes were created
    with neo4j_client.session() as session:
        query = "MATCH (d:TailscaleDevice) RETURN count(d) AS count"
        record = session.run(query).single()
        assert record["count"] == 2500


def test_write_devices_idempotent(
    tailscale_writer: TailscaleWriter, sample_device: TailscaleDevice, neo4j_client: Neo4jClient
) -> None:
    """Test that writing same device twice is idempotent (updates, not duplicates)."""
    # Write first time
    result1 = tailscale_writer.write_devices([sample_device])
    assert result1["total_written"] == 1

    # Modify device slightly
    modified_device = sample_device.model_copy()
    modified_device.ssh_enabled = False  # Changed SSH setting
    modified_device.updated_at = datetime.now(UTC)

    # Write second time with same device_id (unique constraint)
    result2 = tailscale_writer.write_devices([modified_device])
    assert result2["total_written"] == 1

    # Verify only ONE node exists with UPDATED data
    with neo4j_client.session() as session:
        query = "MATCH (d:TailscaleDevice {device_id: $device_id}) RETURN d, count(d) AS count"
        record = session.run(query, {"device_id": sample_device.device_id}).single()

        assert record["count"] == 1  # Only one node
        node = record["d"]
        assert node["ssh_enabled"] is False  # Updated value


# TailscaleNetwork Tests


def test_write_networks_empty_list(tailscale_writer: TailscaleWriter) -> None:
    """Test writing empty network list returns zero counts."""
    result = tailscale_writer.write_networks([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_networks_single_entity(
    tailscale_writer: TailscaleWriter, sample_network: TailscaleNetwork, neo4j_client: Neo4jClient
) -> None:
    """Test writing a single TailscaleNetwork entity."""
    result = tailscale_writer.write_networks([sample_network])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node was created in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (n:TailscaleNetwork {network_id: $network_id}) RETURN n"
        record = session.run(query, {"network_id": sample_network.network_id}).single()

        assert record is not None
        node = record["n"]
        assert node["network_id"] == sample_network.network_id
        assert node["name"] == sample_network.name
        assert node["cidr"] == sample_network.cidr
        assert node["global_nameservers"] == sample_network.global_nameservers
        assert node["search_domains"] == sample_network.search_domains
        assert node["extraction_tier"] == sample_network.extraction_tier


def test_write_networks_idempotent(
    tailscale_writer: TailscaleWriter, sample_network: TailscaleNetwork, neo4j_client: Neo4jClient
) -> None:
    """Test that writing same network twice is idempotent."""
    # Write first time
    result1 = tailscale_writer.write_networks([sample_network])
    assert result1["total_written"] == 1

    # Modify network
    modified_network = sample_network.model_copy()
    modified_network.cidr = "100.64.0.0/16"  # Changed CIDR
    modified_network.updated_at = datetime.now(UTC)

    # Write second time
    result2 = tailscale_writer.write_networks([modified_network])
    assert result2["total_written"] == 1

    # Verify only ONE node exists with UPDATED data
    with neo4j_client.session() as session:
        query = "MATCH (n:TailscaleNetwork {network_id: $network_id}) RETURN n, count(n) AS count"
        record = session.run(query, {"network_id": sample_network.network_id}).single()

        assert record["count"] == 1
        node = record["n"]
        assert node["cidr"] == "100.64.0.0/16"  # Updated value


# TailscaleACL Tests


def test_write_acls_empty_list(tailscale_writer: TailscaleWriter) -> None:
    """Test writing empty ACL list returns zero counts."""
    result = tailscale_writer.write_acls([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_acls_single_entity(
    tailscale_writer: TailscaleWriter, sample_acl: TailscaleACL, neo4j_client: Neo4jClient
) -> None:
    """Test writing a single TailscaleACL entity."""
    result = tailscale_writer.write_acls([sample_acl])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node was created in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (a:TailscaleACL {rule_id: $rule_id}) RETURN a"
        record = session.run(query, {"rule_id": sample_acl.rule_id}).single()

        assert record is not None
        node = record["a"]
        assert node["rule_id"] == sample_acl.rule_id
        assert node["action"] == sample_acl.action
        assert node["source_tags"] == sample_acl.source_tags
        assert node["destination_tags"] == sample_acl.destination_tags
        assert node["ports"] == sample_acl.ports
        assert node["extraction_tier"] == sample_acl.extraction_tier


def test_write_acls_idempotent(
    tailscale_writer: TailscaleWriter, sample_acl: TailscaleACL, neo4j_client: Neo4jClient
) -> None:
    """Test that writing same ACL twice is idempotent."""
    # Write first time
    result1 = tailscale_writer.write_acls([sample_acl])
    assert result1["total_written"] == 1

    # Modify ACL
    modified_acl = sample_acl.model_copy()
    modified_acl.action = "deny"  # Changed action
    modified_acl.updated_at = datetime.now(UTC)

    # Write second time
    result2 = tailscale_writer.write_acls([modified_acl])
    assert result2["total_written"] == 1

    # Verify only ONE node exists with UPDATED data
    with neo4j_client.session() as session:
        query = "MATCH (a:TailscaleACL {rule_id: $rule_id}) RETURN a, count(a) AS count"
        record = session.run(query, {"rule_id": sample_acl.rule_id}).single()

        assert record["count"] == 1
        node = record["a"]
        assert node["action"] == "deny"  # Updated value


# Relationship Tests


def test_write_device_in_network_relationship(
    tailscale_writer: TailscaleWriter,
    sample_device: TailscaleDevice,
    sample_network: TailscaleNetwork,
    neo4j_client: Neo4jClient,
) -> None:
    """Test writing BELONGS_TO relationship between device and network."""
    # Write nodes first
    tailscale_writer.write_devices([sample_device])
    tailscale_writer.write_networks([sample_network])

    # Write relationship
    result = tailscale_writer.write_device_in_network(
        sample_device.device_id, sample_network.network_id
    )

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify relationship exists
    with neo4j_client.session() as session:
        query = """
        MATCH (d:TailscaleDevice {device_id: $device_id})-[r:BELONGS_TO]->
              (n:TailscaleNetwork {network_id: $network_id})
        RETURN count(r) AS count
        """
        record = session.run(
            query,
            {"device_id": sample_device.device_id, "network_id": sample_network.network_id},
        ).single()

        assert record["count"] == 1


def test_write_acl_applies_to_device_relationship(
    tailscale_writer: TailscaleWriter,
    sample_acl: TailscaleACL,
    sample_device: TailscaleDevice,
    neo4j_client: Neo4jClient,
) -> None:
    """Test writing APPLIES_TO relationship between ACL and device."""
    # Write nodes first
    tailscale_writer.write_acls([sample_acl])
    tailscale_writer.write_devices([sample_device])

    # Write relationship
    result = tailscale_writer.write_acl_applies_to_device(
        sample_acl.rule_id, sample_device.device_id
    )

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify relationship exists
    with neo4j_client.session() as session:
        query = """
        MATCH (a:TailscaleACL {rule_id: $rule_id})-[r:APPLIES_TO]->
              (d:TailscaleDevice {device_id: $device_id})
        RETURN count(r) AS count
        """
        record = session.run(
            query, {"rule_id": sample_acl.rule_id, "device_id": sample_device.device_id}
        ).single()

        assert record["count"] == 1


def test_write_batch_size_configuration(neo4j_client: Neo4jClient) -> None:
    """Test that batch_size parameter is respected."""
    small_batch_writer = TailscaleWriter(neo4j_client=neo4j_client, batch_size=100)

    devices = [
        TailscaleDevice(
            device_id=f"ts-device-{i}",
            hostname=f"device{i}.example.com",
            os="linux",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="test",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        for i in range(250)
    ]

    result = small_batch_writer.write_devices(devices)
    assert result["total_written"] == 250
    assert result["batches_executed"] == 3  # 100 + 100 + 50
