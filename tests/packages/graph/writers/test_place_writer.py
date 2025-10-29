"""Tests for PlaceWriter following TDD red-green-refactor pattern.

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
from packages.graph.writers.place_writer import PlaceWriter
from packages.schemas.core.place import Place


@pytest.fixture
def neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all Place nodes after test
    with client.session() as session:
        session.run("MATCH (p:Place) DETACH DELETE p")

    client.close()


@pytest.fixture
def place_writer(neo4j_client: Neo4jClient) -> PlaceWriter:
    """Create PlaceWriter instance."""
    return PlaceWriter(neo4j_client=neo4j_client, batch_size=2000)


@pytest.fixture
def sample_place() -> Place:
    """Create a sample Place entity."""
    return Place(
        name="San Francisco Office",
        address="123 Market St, San Francisco, CA 94105",
        coordinates="37.7749,-122.4194",
        place_type="office",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2020, 5, 10, 8, 0, 0, tzinfo=UTC),
        extraction_tier="B",
        extraction_method="spacy_ner",
        confidence=0.85,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_places_batch() -> list[Place]:
    """Create a batch of 2500 Place entities (exceeds batch_size)."""
    places = []
    for i in range(2500):
        places.append(
            Place(
                name=f"Place {i}",
                address=f"{i} Main St, City {i % 100}",
                coordinates=f"{37.0 + i * 0.001},{-122.0 + i * 0.001}",
                place_type=["office", "datacenter", "network", "city"][i % 4],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        )
    return places


def test_write_places_empty_list(place_writer: PlaceWriter) -> None:
    """Test writing empty list returns zero counts."""
    result = place_writer.write_places([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_places_single_entity(
    place_writer: PlaceWriter, sample_place: Place, neo4j_client: Neo4jClient
) -> None:
    """Test writing a single Place entity."""
    result = place_writer.write_places([sample_place])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node was created in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (p:Place {name: $name}) RETURN p"
        record = session.run(query, {"name": sample_place.name}).single()

        assert record is not None
        node = record["p"]
        assert node["name"] == sample_place.name
        assert node["address"] == sample_place.address
        assert node["coordinates"] == sample_place.coordinates
        assert node["place_type"] == sample_place.place_type
        assert node["extraction_tier"] == sample_place.extraction_tier
        assert node["extraction_method"] == sample_place.extraction_method
        assert node["confidence"] == sample_place.confidence
        assert node["extractor_version"] == sample_place.extractor_version


def test_write_places_batch_2000(
    place_writer: PlaceWriter, sample_places_batch: list[Place], neo4j_client: Neo4jClient
) -> None:
    """Test writing 2500 entities (requires 2 batches of 2000)."""
    result = place_writer.write_places(sample_places_batch)

    assert result["total_written"] == 2500
    assert result["batches_executed"] == 2  # 2000 + 500

    # Verify all nodes were created
    with neo4j_client.session() as session:
        query = "MATCH (p:Place) RETURN count(p) AS count"
        record = session.run(query).single()
        assert record["count"] == 2500


def test_write_places_idempotent(
    place_writer: PlaceWriter, sample_place: Place, neo4j_client: Neo4jClient
) -> None:
    """Test that writing same data twice is idempotent (updates, not duplicates)."""
    # Write first time
    result1 = place_writer.write_places([sample_place])
    assert result1["total_written"] == 1

    # Modify place slightly
    modified_place = sample_place.model_copy()
    modified_place.place_type = "headquarters"  # Changed type
    modified_place.updated_at = datetime.now(UTC)

    # Write second time with same name (unique constraint)
    result2 = place_writer.write_places([modified_place])
    assert result2["total_written"] == 1

    # Verify only ONE node exists with UPDATED data
    with neo4j_client.session() as session:
        query = "MATCH (p:Place {name: $name}) RETURN p, count(p) AS count"
        record = session.run(query, {"name": sample_place.name}).single()

        assert record["count"] == 1  # Only one node
        node = record["p"]
        assert node["place_type"] == "headquarters"  # Updated value


def test_write_places_constraint_violation_duplicate_name(
    place_writer: PlaceWriter, sample_place: Place
) -> None:
    """Test that duplicate names within same batch are handled correctly.

    Note: Neo4j MERGE handles this gracefully - last value wins.
    This test verifies the writer doesn't crash on duplicate keys in batch.
    """
    # Create two places with same name
    place1 = sample_place
    place2 = sample_place.model_copy()
    place2.address = "456 Other St"  # Different address, same name

    # Should succeed - MERGE will update the same node twice
    result = place_writer.write_places([place1, place2])
    assert result["total_written"] == 2  # Both writes processed
    assert result["batches_executed"] == 1


def test_write_places_minimal_fields(neo4j_client: Neo4jClient) -> None:
    """Test that Place entities can be created with minimal fields."""
    writer = PlaceWriter(neo4j_client=neo4j_client)

    minimal_place = Place(
        name="Minimal Place",
        # All optional fields omitted
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="test",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = writer.write_places([minimal_place])
    assert result["total_written"] == 1

    # Verify node was created with null optional fields
    with neo4j_client.session() as session:
        query = "MATCH (p:Place {name: $name}) RETURN p"
        record = session.run(query, {"name": "Minimal Place"}).single()

        assert record is not None
        node = record["p"]
        assert node["name"] == "Minimal Place"
        assert node.get("address") is None
        assert node.get("coordinates") is None
        assert node.get("place_type") is None


def test_write_places_batch_size_configuration(neo4j_client: Neo4jClient) -> None:
    """Test that batch_size parameter is respected."""
    small_batch_writer = PlaceWriter(neo4j_client=neo4j_client, batch_size=100)

    places = [
        Place(
            name=f"Place {i}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="test",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        for i in range(250)
    ]

    result = small_batch_writer.write_places(places)
    assert result["total_written"] == 250
    assert result["batches_executed"] == 3  # 100 + 100 + 50
