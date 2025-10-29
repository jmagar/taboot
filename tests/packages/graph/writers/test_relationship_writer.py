"""Tests for RelationshipWriter following TDD red-green-refactor pattern.

Tests cover:
- Empty list handling
- All 10 core relationship types
- Batch 2000 write
- Idempotent writes
- Multiple relationship types in single batch
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from packages.graph.client import Neo4jClient
from packages.graph.writers.relationship_writer import RelationshipWriter
from packages.schemas.relationships import (
    BelongsToRelationship,
    ContributesToRelationship,
    CreatedRelationship,
    DependsOnRelationship,
    InThreadRelationship,
    LocatedInRelationship,
    MentionsRelationship,
    RoutesToRelationship,
    SentRelationship,
    WorksAtRelationship,
)


@pytest.fixture
def neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all nodes after test
    with client.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    client.close()


@pytest.fixture
def relationship_writer(neo4j_client: Neo4jClient) -> RelationshipWriter:
    """Create RelationshipWriter instance."""
    return RelationshipWriter(neo4j_client=neo4j_client, batch_size=2000)


@pytest.fixture
def setup_test_nodes(neo4j_client: Neo4jClient) -> None:
    """Create test nodes for relationship tests."""
    with neo4j_client.session() as session:
        # Create Person nodes
        session.run(
            """
            CREATE (p1:Person {email: 'john@example.com', name: 'John Doe'})
            CREATE (p2:Person {email: 'jane@example.com', name: 'Jane Smith'})
            """
        )

        # Create Organization nodes
        session.run(
            """
            CREATE (o1:Organization {name: 'Acme Corp'})
            CREATE (o2:Organization {name: 'Tech Inc'})
            """
        )

        # Create Document nodes
        session.run(
            """
            CREATE (d1:Document {doc_id: 'doc_123'})
            """
        )

        # Create Email nodes
        session.run(
            """
            CREATE (e1:Email {message_id: 'msg_123'})
            CREATE (e2:Email {message_id: 'msg_456'})
            """
        )

        # Create Thread nodes
        session.run(
            """
            CREATE (t1:Thread {thread_id: 'thread_123'})
            """
        )

        # Create Place nodes
        session.run(
            """
            CREATE (pl1:Place {name: 'San Francisco'})
            """
        )

        # Create Repository nodes
        session.run(
            """
            CREATE (r1:Repository {full_name: 'owner/repo'})
            """
        )


def test_write_relationships_empty_list(relationship_writer: RelationshipWriter) -> None:
    """Test writing empty list returns zero counts."""
    result = relationship_writer.write_relationships([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_works_at_relationship(
    relationship_writer: RelationshipWriter, setup_test_nodes: None, neo4j_client: Neo4jClient
) -> None:
    """Test writing WORKS_AT relationship."""
    rel = WorksAtRelationship(
        role="Senior Engineer",
        start_date=datetime(2020, 1, 1, tzinfo=UTC),
        end_date=None,
        created_at=datetime.now(UTC),
        source="github_reader",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationships = [
        {
            "rel_type": "WORKS_AT",
            "source_label": "Person",
            "source_key": "email",
            "source_value": "john@example.com",
            "target_label": "Organization",
            "target_key": "name",
            "target_value": "Acme Corp",
            "relationship": rel,
        }
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify relationship was created
    with neo4j_client.session() as session:
        query = """
        MATCH (p:Person {email: 'john@example.com'})-[r:WORKS_AT]->(o:Organization {name: 'Acme Corp'})
        RETURN r
        """
        record = session.run(query).single()

        assert record is not None
        relationship = record["r"]
        assert relationship["role"] == "Senior Engineer"
        assert relationship["confidence"] == 1.0


def test_write_mentions_relationship(
    relationship_writer: RelationshipWriter, setup_test_nodes: None, neo4j_client: Neo4jClient
) -> None:
    """Test writing MENTIONS relationship."""
    rel = MentionsRelationship(
        span="John Doe mentioned in document",
        section="Introduction",
        chunk_id=uuid4(),
        created_at=datetime.now(UTC),
        source="job_123",
        confidence=0.95,
        extractor_version="1.0.0",
    )

    relationships = [
        {
            "rel_type": "MENTIONS",
            "source_label": "Document",
            "source_key": "doc_id",
            "source_value": "doc_123",
            "target_label": "Person",
            "target_key": "email",
            "target_value": "john@example.com",
            "relationship": rel,
        }
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify relationship was created
    with neo4j_client.session() as session:
        query = """
        MATCH (d:Document {doc_id: 'doc_123'})-[r:MENTIONS]->(p:Person)
        RETURN r
        """
        record = session.run(query).single()

        assert record is not None
        relationship = record["r"]
        assert relationship["span"] == "John Doe mentioned in document"
        assert relationship["section"] == "Introduction"


def test_write_routes_to_relationship(
    relationship_writer: RelationshipWriter, neo4j_client: Neo4jClient
) -> None:
    """Test writing ROUTES_TO relationship."""
    # Create Proxy and Service nodes
    with neo4j_client.session() as session:
        session.run(
            """
            CREATE (pr:Proxy {name: 'nginx-proxy'})
            CREATE (s:Service {name: 'web-service'})
            """
        )

    rel = RoutesToRelationship(
        host="example.com",
        path="/api",
        tls=True,
        auth_enabled=True,
        created_at=datetime.now(UTC),
        source="swag_reader",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationships = [
        {
            "rel_type": "ROUTES_TO",
            "source_label": "Proxy",
            "source_key": "name",
            "source_value": "nginx-proxy",
            "target_label": "Service",
            "target_key": "name",
            "target_value": "web-service",
            "relationship": rel,
        }
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 1

    # Verify relationship
    with neo4j_client.session() as session:
        query = """
        MATCH (pr:Proxy)-[r:ROUTES_TO]->(s:Service)
        RETURN r
        """
        record = session.run(query).single()

        assert record is not None
        relationship = record["r"]
        assert relationship["host"] == "example.com"
        assert relationship["tls"] is True


def test_write_depends_on_relationship(
    relationship_writer: RelationshipWriter, neo4j_client: Neo4jClient
) -> None:
    """Test writing DEPENDS_ON relationship."""
    # Create Service nodes
    with neo4j_client.session() as session:
        session.run(
            """
            CREATE (s1:Service {name: 'web-app'})
            CREATE (s2:Service {name: 'database'})
            """
        )

    rel = DependsOnRelationship(
        condition="service_healthy",
        created_at=datetime.now(UTC),
        source="docker_compose_reader",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationships = [
        {
            "rel_type": "DEPENDS_ON",
            "source_label": "Service",
            "source_key": "name",
            "source_value": "web-app",
            "target_label": "Service",
            "target_key": "name",
            "target_value": "database",
            "relationship": rel,
        }
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 1


def test_write_sent_relationship(
    relationship_writer: RelationshipWriter, setup_test_nodes: None, neo4j_client: Neo4jClient
) -> None:
    """Test writing SENT relationship."""
    rel = SentRelationship(
        sent_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        created_at=datetime.now(UTC),
        source="gmail_reader",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationships = [
        {
            "rel_type": "SENT",
            "source_label": "Person",
            "source_key": "email",
            "source_value": "john@example.com",
            "target_label": "Email",
            "target_key": "message_id",
            "target_value": "msg_123",
            "relationship": rel,
        }
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 1


def test_write_contributes_to_relationship(
    relationship_writer: RelationshipWriter, setup_test_nodes: None, neo4j_client: Neo4jClient
) -> None:
    """Test writing CONTRIBUTES_TO relationship."""
    rel = ContributesToRelationship(
        commit_count=150,
        first_commit_at=datetime(2020, 1, 1, tzinfo=UTC),
        last_commit_at=datetime(2024, 1, 1, tzinfo=UTC),
        created_at=datetime.now(UTC),
        source="github_reader",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationships = [
        {
            "rel_type": "CONTRIBUTES_TO",
            "source_label": "Person",
            "source_key": "email",
            "source_value": "john@example.com",
            "target_label": "Repository",
            "target_key": "full_name",
            "target_value": "owner/repo",
            "relationship": rel,
        }
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 1


def test_write_created_relationship(
    relationship_writer: RelationshipWriter, setup_test_nodes: None, neo4j_client: Neo4jClient
) -> None:
    """Test writing CREATED relationship."""
    rel = CreatedRelationship(
        created_at=datetime.now(UTC),
        source="github_reader",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationships = [
        {
            "rel_type": "CREATED",
            "source_label": "Person",
            "source_key": "email",
            "source_value": "john@example.com",
            "target_label": "Repository",
            "target_key": "full_name",
            "target_value": "owner/repo",
            "relationship": rel,
        }
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 1


def test_write_belongs_to_relationship(
    relationship_writer: RelationshipWriter, setup_test_nodes: None, neo4j_client: Neo4jClient
) -> None:
    """Test writing BELONGS_TO relationship."""
    rel = BelongsToRelationship(
        created_at=datetime.now(UTC),
        source="github_reader",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationships = [
        {
            "rel_type": "BELONGS_TO",
            "source_label": "Repository",
            "source_key": "full_name",
            "source_value": "owner/repo",
            "target_label": "Organization",
            "target_key": "name",
            "target_value": "Acme Corp",
            "relationship": rel,
        }
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 1


def test_write_in_thread_relationship(
    relationship_writer: RelationshipWriter, setup_test_nodes: None, neo4j_client: Neo4jClient
) -> None:
    """Test writing IN_THREAD relationship."""
    rel = InThreadRelationship(
        created_at=datetime.now(UTC),
        source="gmail_reader",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationships = [
        {
            "rel_type": "IN_THREAD",
            "source_label": "Email",
            "source_key": "message_id",
            "source_value": "msg_123",
            "target_label": "Thread",
            "target_key": "thread_id",
            "target_value": "thread_123",
            "relationship": rel,
        }
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 1


def test_write_located_in_relationship(
    relationship_writer: RelationshipWriter, setup_test_nodes: None, neo4j_client: Neo4jClient
) -> None:
    """Test writing LOCATED_IN relationship."""
    rel = LocatedInRelationship(
        created_at=datetime.now(UTC),
        source="github_reader",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationships = [
        {
            "rel_type": "LOCATED_IN",
            "source_label": "Organization",
            "source_key": "name",
            "source_value": "Acme Corp",
            "target_label": "Place",
            "target_key": "name",
            "target_value": "San Francisco",
            "relationship": rel,
        }
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 1


def test_write_relationships_batch_2000(
    relationship_writer: RelationshipWriter, neo4j_client: Neo4jClient
) -> None:
    """Test writing 2500 relationships (requires 2 batches)."""
    # Create 2500 Person and Organization nodes
    with neo4j_client.session() as session:
        session.run(
            """
            UNWIND range(0, 2499) AS i
            CREATE (p:Person {email: 'person' + i + '@example.com'})
            CREATE (o:Organization {name: 'Org ' + i})
            """
        )

    # Create 2500 WORKS_AT relationships
    relationships = []
    for i in range(2500):
        rel = WorksAtRelationship(
            role=f"Role {i}",
            created_at=datetime.now(UTC),
            source="test",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        relationships.append(
            {
                "rel_type": "WORKS_AT",
                "source_label": "Person",
                "source_key": "email",
                "source_value": f"person{i}@example.com",
                "target_label": "Organization",
                "target_key": "name",
                "target_value": f"Org {i}",
                "relationship": rel,
            }
        )

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 2500
    assert result["batches_executed"] == 2  # 2000 + 500

    # Verify all relationships were created
    with neo4j_client.session() as session:
        query = "MATCH ()-[r:WORKS_AT]->() RETURN count(r) AS count"
        record = session.run(query).single()
        assert record["count"] == 2500


def test_write_relationships_idempotent(
    relationship_writer: RelationshipWriter, setup_test_nodes: None, neo4j_client: Neo4jClient
) -> None:
    """Test that writing same relationship twice is idempotent."""
    rel = WorksAtRelationship(
        role="Engineer",
        created_at=datetime.now(UTC),
        source="test",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationship_data = {
        "rel_type": "WORKS_AT",
        "source_label": "Person",
        "source_key": "email",
        "source_value": "john@example.com",
        "target_label": "Organization",
        "target_key": "name",
        "target_value": "Acme Corp",
        "relationship": rel,
    }

    # Write first time
    result1 = relationship_writer.write_relationships([relationship_data])
    assert result1["total_written"] == 1

    # Write second time with same data
    result2 = relationship_writer.write_relationships([relationship_data])
    assert result2["total_written"] == 1

    # Verify only ONE relationship exists
    with neo4j_client.session() as session:
        query = """
        MATCH (p:Person {email: 'john@example.com'})-[r:WORKS_AT]->(o:Organization)
        RETURN count(r) AS count
        """
        record = session.run(query).single()
        assert record["count"] == 1


def test_write_mixed_relationship_types(
    relationship_writer: RelationshipWriter, setup_test_nodes: None, neo4j_client: Neo4jClient
) -> None:
    """Test writing multiple relationship types in single batch."""
    relationships = [
        {
            "rel_type": "WORKS_AT",
            "source_label": "Person",
            "source_key": "email",
            "source_value": "john@example.com",
            "target_label": "Organization",
            "target_key": "name",
            "target_value": "Acme Corp",
            "relationship": WorksAtRelationship(
                role="Engineer",
                created_at=datetime.now(UTC),
                source="test",
                confidence=1.0,
                extractor_version="1.0.0",
            ),
        },
        {
            "rel_type": "SENT",
            "source_label": "Person",
            "source_key": "email",
            "source_value": "jane@example.com",
            "target_label": "Email",
            "target_key": "message_id",
            "target_value": "msg_123",
            "relationship": SentRelationship(
                sent_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
                source="test",
                confidence=1.0,
                extractor_version="1.0.0",
            ),
        },
    ]

    result = relationship_writer.write_relationships(relationships)

    assert result["total_written"] == 2
    assert result["batches_executed"] == 1

    # Verify both relationships were created
    with neo4j_client.session() as session:
        works_at = session.run("MATCH ()-[r:WORKS_AT]->() RETURN count(r) AS count").single()
        sent = session.run("MATCH ()-[r:SENT]->() RETURN count(r) AS count").single()

        assert works_at["count"] == 1
        assert sent["count"] == 1


def test_write_relationships_batch_size_configuration(neo4j_client: Neo4jClient) -> None:
    """Test that batch_size parameter is respected."""
    small_batch_writer = RelationshipWriter(neo4j_client=neo4j_client, batch_size=100)

    # Create 250 Person and Organization nodes
    with neo4j_client.session() as session:
        session.run(
            """
            UNWIND range(0, 249) AS i
            CREATE (p:Person {email: 'test' + i + '@example.com'})
            CREATE (o:Organization {name: 'TestOrg ' + i})
            """
        )

    relationships = []
    for i in range(250):
        rel = WorksAtRelationship(
            role="Test",
            created_at=datetime.now(UTC),
            source="test",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        relationships.append(
            {
                "rel_type": "WORKS_AT",
                "source_label": "Person",
                "source_key": "email",
                "source_value": f"test{i}@example.com",
                "target_label": "Organization",
                "target_key": "name",
                "target_value": f"TestOrg {i}",
                "relationship": rel,
            }
        )

    result = small_batch_writer.write_relationships(relationships)
    assert result["total_written"] == 250
    assert result["batches_executed"] == 3  # 100 + 100 + 50
