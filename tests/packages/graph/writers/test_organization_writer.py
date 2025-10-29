"""Tests for OrganizationWriter following TDD red-green-refactor pattern.

Tests cover:
- Empty list handling
- Single entity write
- Batch 2000 write
- Idempotent writes (same data written twice)
- Constraint violations
"""

from datetime import UTC, datetime

import pytest

from packages.graph.client import Neo4jClient
from packages.graph.writers.organization_writer import OrganizationWriter
from packages.schemas.core.organization import Organization


@pytest.fixture
def neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all Organization nodes after test
    with client.session() as session:
        session.run("MATCH (o:Organization) DETACH DELETE o")

    client.close()


@pytest.fixture
def organization_writer(neo4j_client: Neo4jClient) -> OrganizationWriter:
    """Create OrganizationWriter instance."""
    return OrganizationWriter(neo4j_client=neo4j_client, batch_size=2000)


@pytest.fixture
def sample_organization() -> Organization:
    """Create a sample Organization entity."""
    return Organization(
        name="Acme Corp",
        industry="Technology",
        size="100-500",
        website="https://acme.com",
        description="Leading technology company focused on AI",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2020, 5, 10, 8, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_organizations_batch() -> list[Organization]:
    """Create a batch of 2500 Organization entities (exceeds batch_size)."""
    organizations = []
    for i in range(2500):
        organizations.append(
            Organization(
                name=f"Organization {i}",
                industry=f"Industry {i % 10}",
                size="100-500",
                website=f"https://org{i}.com",
                description=f"Description for organization {i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        )
    return organizations


def test_write_organizations_empty_list(organization_writer: OrganizationWriter) -> None:
    """Test writing empty list returns zero counts."""
    result = organization_writer.write_organizations([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_organizations_single_entity(
    organization_writer: OrganizationWriter,
    sample_organization: Organization,
    neo4j_client: Neo4jClient,
) -> None:
    """Test writing a single Organization entity."""
    result = organization_writer.write_organizations([sample_organization])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node was created in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (o:Organization {name: $name}) RETURN o"
        record = session.run(query, {"name": sample_organization.name}).single()

        assert record is not None
        node = record["o"]
        assert node["name"] == sample_organization.name
        assert node["industry"] == sample_organization.industry
        assert node["size"] == sample_organization.size
        assert node["website"] == sample_organization.website
        assert node["description"] == sample_organization.description
        assert node["extraction_tier"] == sample_organization.extraction_tier
        assert node["extraction_method"] == sample_organization.extraction_method
        assert node["confidence"] == sample_organization.confidence
        assert node["extractor_version"] == sample_organization.extractor_version


def test_write_organizations_batch_2000(
    organization_writer: OrganizationWriter,
    sample_organizations_batch: list[Organization],
    neo4j_client: Neo4jClient,
) -> None:
    """Test writing 2500 entities (requires 2 batches of 2000)."""
    result = organization_writer.write_organizations(sample_organizations_batch)

    assert result["total_written"] == 2500
    assert result["batches_executed"] == 2  # 2000 + 500

    # Verify all nodes were created
    with neo4j_client.session() as session:
        query = "MATCH (o:Organization) RETURN count(o) AS count"
        record = session.run(query).single()
        assert record["count"] == 2500


def test_write_organizations_idempotent(
    organization_writer: OrganizationWriter,
    sample_organization: Organization,
    neo4j_client: Neo4jClient,
) -> None:
    """Test that writing same data twice is idempotent (updates, not duplicates)."""
    # Write first time
    result1 = organization_writer.write_organizations([sample_organization])
    assert result1["total_written"] == 1

    # Modify organization slightly
    modified_org = sample_organization.model_copy()
    modified_org.industry = "Artificial Intelligence"  # Changed industry
    modified_org.updated_at = datetime.now(UTC)

    # Write second time with same name (unique constraint)
    result2 = organization_writer.write_organizations([modified_org])
    assert result2["total_written"] == 1

    # Verify only ONE node exists with UPDATED data
    with neo4j_client.session() as session:
        query = "MATCH (o:Organization {name: $name}) RETURN o, count(o) AS count"
        record = session.run(query, {"name": sample_organization.name}).single()

        assert record["count"] == 1  # Only one node
        node = record["o"]
        assert node["industry"] == "Artificial Intelligence"  # Updated value


def test_write_organizations_constraint_violation_duplicate_name(
    organization_writer: OrganizationWriter, sample_organization: Organization
) -> None:
    """Test that duplicate names within same batch are handled correctly.

    Note: Neo4j MERGE handles this gracefully - last value wins.
    This test verifies the writer doesn't crash on duplicate keys in batch.
    """
    # Create two organizations with same name
    org1 = sample_organization
    org2 = sample_organization.model_copy()
    org2.industry = "Finance"  # Different industry, same name

    # Should succeed - MERGE will update the same node twice
    result = organization_writer.write_organizations([org1, org2])
    assert result["total_written"] == 2  # Both writes processed
    assert result["batches_executed"] == 1


def test_write_organizations_all_fields_optional_except_required(
    neo4j_client: Neo4jClient,
) -> None:
    """Test that Organization entities can be created with minimal fields."""
    writer = OrganizationWriter(neo4j_client=neo4j_client)

    minimal_org = Organization(
        name="Minimal Corp",
        # All optional fields omitted
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="test",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = writer.write_organizations([minimal_org])
    assert result["total_written"] == 1

    # Verify node was created with null optional fields
    with neo4j_client.session() as session:
        query = "MATCH (o:Organization {name: $name}) RETURN o"
        record = session.run(query, {"name": "Minimal Corp"}).single()

        assert record is not None
        node = record["o"]
        assert node["name"] == "Minimal Corp"
        assert node.get("industry") is None
        assert node.get("size") is None
        assert node.get("website") is None
        assert node.get("description") is None


def test_write_organizations_batch_size_configuration(neo4j_client: Neo4jClient) -> None:
    """Test that batch_size parameter is respected."""
    small_batch_writer = OrganizationWriter(neo4j_client=neo4j_client, batch_size=100)

    orgs = [
        Organization(
            name=f"Organization {i}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="test",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        for i in range(250)
    ]

    result = small_batch_writer.write_organizations(orgs)
    assert result["total_written"] == 250
    assert result["batches_executed"] == 3  # 100 + 100 + 50
