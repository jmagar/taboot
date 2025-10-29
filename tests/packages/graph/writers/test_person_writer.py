"""Tests for PersonWriter following TDD red-green-refactor pattern.

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
from packages.graph.writers.person_writer import PersonWriter
from packages.schemas.core.person import Person


@pytest.fixture
def neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all Person nodes after test
    with client.session() as session:
        session.run("MATCH (p:Person) DETACH DELETE p")

    client.close()


@pytest.fixture
def person_writer(neo4j_client: Neo4jClient) -> PersonWriter:
    """Create PersonWriter instance."""
    return PersonWriter(neo4j_client=neo4j_client, batch_size=2000)


@pytest.fixture
def sample_person() -> Person:
    """Create a sample Person entity."""
    return Person(
        name="John Doe",
        email="john.doe@example.com",
        role="Senior Engineer",
        bio="Passionate about open source and Python",
        github_username="johndoe",
        reddit_username="john_dev",
        youtube_channel="@johndoedev",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2020, 5, 10, 8, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_persons_batch() -> list[Person]:
    """Create a batch of 2500 Person entities (exceeds batch_size)."""
    persons = []
    for i in range(2500):
        persons.append(
            Person(
                name=f"Person {i}",
                email=f"person{i}@example.com",
                role=f"Role {i % 10}",
                bio=f"Bio for person {i}",
                github_username=f"person{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        )
    return persons


def test_write_persons_empty_list(person_writer: PersonWriter) -> None:
    """Test writing empty list returns zero counts."""
    result = person_writer.write_persons([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_persons_single_entity(
    person_writer: PersonWriter, sample_person: Person, neo4j_client: Neo4jClient
) -> None:
    """Test writing a single Person entity."""
    result = person_writer.write_persons([sample_person])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node was created in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (p:Person {email: $email}) RETURN p"
        record = session.run(query, {"email": sample_person.email}).single()

        assert record is not None
        node = record["p"]
        assert node["name"] == sample_person.name
        assert node["email"] == sample_person.email
        assert node["role"] == sample_person.role
        assert node["bio"] == sample_person.bio
        assert node["github_username"] == sample_person.github_username
        assert node["reddit_username"] == sample_person.reddit_username
        assert node["youtube_channel"] == sample_person.youtube_channel
        assert node["extraction_tier"] == sample_person.extraction_tier
        assert node["extraction_method"] == sample_person.extraction_method
        assert node["confidence"] == sample_person.confidence
        assert node["extractor_version"] == sample_person.extractor_version


def test_write_persons_batch_2000(
    person_writer: PersonWriter, sample_persons_batch: list[Person], neo4j_client: Neo4jClient
) -> None:
    """Test writing 2500 entities (requires 2 batches of 2000)."""
    result = person_writer.write_persons(sample_persons_batch)

    assert result["total_written"] == 2500
    assert result["batches_executed"] == 2  # 2000 + 500

    # Verify all nodes were created
    with neo4j_client.session() as session:
        query = "MATCH (p:Person) RETURN count(p) AS count"
        record = session.run(query).single()
        assert record["count"] == 2500


def test_write_persons_idempotent(
    person_writer: PersonWriter, sample_person: Person, neo4j_client: Neo4jClient
) -> None:
    """Test that writing same data twice is idempotent (updates, not duplicates)."""
    # Write first time
    result1 = person_writer.write_persons([sample_person])
    assert result1["total_written"] == 1

    # Modify person slightly
    modified_person = sample_person.model_copy()
    modified_person.role = "Staff Engineer"  # Changed role
    modified_person.updated_at = datetime.now(UTC)

    # Write second time with same email (unique constraint)
    result2 = person_writer.write_persons([modified_person])
    assert result2["total_written"] == 1

    # Verify only ONE node exists with UPDATED data
    with neo4j_client.session() as session:
        query = "MATCH (p:Person {email: $email}) RETURN p, count(p) AS count"
        record = session.run(query, {"email": sample_person.email}).single()

        assert record["count"] == 1  # Only one node
        node = record["p"]
        assert node["role"] == "Staff Engineer"  # Updated value


def test_write_persons_constraint_violation_duplicate_email(
    person_writer: PersonWriter, sample_person: Person
) -> None:
    """Test that duplicate emails within same batch are handled correctly.

    Note: Neo4j MERGE handles this gracefully - last value wins.
    This test verifies the writer doesn't crash on duplicate keys in batch.
    """
    # Create two persons with same email
    person1 = sample_person
    person2 = sample_person.model_copy()
    person2.name = "Jane Doe"  # Different name, same email

    # Should succeed - MERGE will update the same node twice
    result = person_writer.write_persons([person1, person2])
    assert result["total_written"] == 2  # Both writes processed
    assert result["batches_executed"] == 1


def test_write_persons_invalid_email_caught_by_pydantic(sample_person: Person) -> None:
    """Test that invalid emails are caught by Pydantic validation."""
    with pytest.raises(ValueError, match="Invalid email format"):
        Person(
            name="Invalid Person",
            email="not-an-email",  # Invalid email
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="test",
            confidence=1.0,
            extractor_version="1.0.0",
        )


def test_write_persons_all_fields_optional_except_required(neo4j_client: Neo4jClient) -> None:
    """Test that Person entities can be created with minimal fields."""
    writer = PersonWriter(neo4j_client=neo4j_client)

    minimal_person = Person(
        name="Minimal Person",
        email="minimal@example.com",
        # All optional fields omitted
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="test",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = writer.write_persons([minimal_person])
    assert result["total_written"] == 1

    # Verify node was created with null optional fields
    with neo4j_client.session() as session:
        query = "MATCH (p:Person {email: $email}) RETURN p"
        record = session.run(query, {"email": "minimal@example.com"}).single()

        assert record is not None
        node = record["p"]
        assert node["name"] == "Minimal Person"
        assert node["email"] == "minimal@example.com"
        assert node.get("role") is None
        assert node.get("bio") is None
        assert node.get("github_username") is None


def test_write_persons_batch_size_configuration(neo4j_client: Neo4jClient) -> None:
    """Test that batch_size parameter is respected."""
    small_batch_writer = PersonWriter(neo4j_client=neo4j_client, batch_size=100)

    persons = [
        Person(
            name=f"Person {i}",
            email=f"batch{i}@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="test",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        for i in range(250)
    ]

    result = small_batch_writer.write_persons(persons)
    assert result["total_written"] == 250
    assert result["batches_executed"] == 3  # 100 + 100 + 50
