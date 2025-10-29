"""Tests for EventWriter following TDD red-green-refactor pattern.

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
from packages.graph.writers.event_writer import EventWriter
from packages.schemas.core.event import Event


@pytest.fixture
def neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all Event nodes after test
    with client.session() as session:
        session.run("MATCH (e:Event) DETACH DELETE e")

    client.close()


@pytest.fixture
def event_writer(neo4j_client: Neo4jClient) -> EventWriter:
    """Create EventWriter instance."""
    return EventWriter(neo4j_client=neo4j_client, batch_size=2000)


@pytest.fixture
def sample_event() -> Event:
    """Create a sample Event entity."""
    return Event(
        name="Product Launch",
        start_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        end_time=datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC),
        location="Conference Room A",
        event_type="meeting",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 15, 9, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="gmail_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_events_batch() -> list[Event]:
    """Create a batch of 2500 Event entities (exceeds batch_size)."""
    events = []
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    for i in range(2500):
        # Calculate day offset safely (1-28 to avoid month boundary issues)
        day_offset = (i % 28) + 1
        start_time = datetime(2024, 1, day_offset, 10, 0, 0, tzinfo=UTC)
        end_time = datetime(2024, 1, day_offset, 11, 0, 0, tzinfo=UTC)
        events.append(
            Event(
                name=f"Event {i}",
                start_time=start_time,
                end_time=end_time,
                location=f"Location {i % 10}",
                event_type=["meeting", "release", "commit", "deadline"][i % 4],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        )
    return events


def test_write_events_empty_list(event_writer: EventWriter) -> None:
    """Test writing empty list returns zero counts."""
    result = event_writer.write_events([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_events_single_entity(
    event_writer: EventWriter, sample_event: Event, neo4j_client: Neo4jClient
) -> None:
    """Test writing a single Event entity."""
    result = event_writer.write_events([sample_event])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node was created in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (e:Event {name: $name}) RETURN e"
        record = session.run(query, {"name": sample_event.name}).single()

        assert record is not None
        node = record["e"]
        assert node["name"] == sample_event.name
        assert node["start_time"] == sample_event.start_time.isoformat()
        assert node["end_time"] == sample_event.end_time.isoformat()
        assert node["location"] == sample_event.location
        assert node["event_type"] == sample_event.event_type
        assert node["extraction_tier"] == sample_event.extraction_tier
        assert node["extraction_method"] == sample_event.extraction_method
        assert node["confidence"] == sample_event.confidence
        assert node["extractor_version"] == sample_event.extractor_version


def test_write_events_batch_2000(
    event_writer: EventWriter, sample_events_batch: list[Event], neo4j_client: Neo4jClient
) -> None:
    """Test writing 2500 entities (requires 2 batches of 2000)."""
    result = event_writer.write_events(sample_events_batch)

    assert result["total_written"] == 2500
    assert result["batches_executed"] == 2  # 2000 + 500

    # Verify all nodes were created
    with neo4j_client.session() as session:
        query = "MATCH (e:Event) RETURN count(e) AS count"
        record = session.run(query).single()
        assert record["count"] == 2500


def test_write_events_idempotent(
    event_writer: EventWriter, sample_event: Event, neo4j_client: Neo4jClient
) -> None:
    """Test that writing same data twice is idempotent (updates, not duplicates)."""
    # Write first time
    result1 = event_writer.write_events([sample_event])
    assert result1["total_written"] == 1

    # Modify event slightly
    modified_event = sample_event.model_copy()
    modified_event.event_type = "launch"  # Changed type
    modified_event.updated_at = datetime.now(UTC)

    # Write second time with same name (unique constraint)
    result2 = event_writer.write_events([modified_event])
    assert result2["total_written"] == 1

    # Verify only ONE node exists with UPDATED data
    with neo4j_client.session() as session:
        query = "MATCH (e:Event {name: $name}) RETURN e, count(e) AS count"
        record = session.run(query, {"name": sample_event.name}).single()

        assert record["count"] == 1  # Only one node
        node = record["e"]
        assert node["event_type"] == "launch"  # Updated value


def test_write_events_constraint_violation_duplicate_name(
    event_writer: EventWriter, sample_event: Event
) -> None:
    """Test that duplicate names within same batch are handled correctly.

    Note: Neo4j MERGE handles this gracefully - last value wins.
    This test verifies the writer doesn't crash on duplicate keys in batch.
    """
    # Create two events with same name
    event1 = sample_event
    event2 = sample_event.model_copy()
    event2.location = "Different Location"  # Different location, same name

    # Should succeed - MERGE will update the same node twice
    result = event_writer.write_events([event1, event2])
    assert result["total_written"] == 2  # Both writes processed
    assert result["batches_executed"] == 1


def test_write_events_minimal_fields(neo4j_client: Neo4jClient) -> None:
    """Test that Event entities can be created with minimal fields."""
    writer = EventWriter(neo4j_client=neo4j_client)

    minimal_event = Event(
        name="Minimal Event",
        # All optional fields omitted
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="test",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = writer.write_events([minimal_event])
    assert result["total_written"] == 1

    # Verify node was created with null optional fields
    with neo4j_client.session() as session:
        query = "MATCH (e:Event {name: $name}) RETURN e"
        record = session.run(query, {"name": "Minimal Event"}).single()

        assert record is not None
        node = record["e"]
        assert node["name"] == "Minimal Event"
        assert node.get("start_time") is None
        assert node.get("end_time") is None
        assert node.get("location") is None
        assert node.get("event_type") is None


def test_write_events_batch_size_configuration(neo4j_client: Neo4jClient) -> None:
    """Test that batch_size parameter is respected."""
    small_batch_writer = EventWriter(neo4j_client=neo4j_client, batch_size=100)

    events = [
        Event(
            name=f"Event {i}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="test",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        for i in range(250)
    ]

    result = small_batch_writer.write_events(events)
    assert result["total_written"] == 250
    assert result["batches_executed"] == 3  # 100 + 100 + 50
