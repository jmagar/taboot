"""Phase 1 validation script - validates all entities and relationships."""

from datetime import UTC, datetime
from uuid import uuid4

from packages.schemas.core import Event, File, Organization, Person, Place
from packages.schemas.relationships import (
    BaseRelationship,
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


def test_entities() -> int:
    """Test all 5 core entities."""
    print("\n=== Testing Core Entities ===")
    tests_passed = 0
    now = datetime.now(UTC)

    # Test Person
    try:
        person = Person(
            name="John Doe",
            email="john@example.com",
            role="Senior Engineer",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        assert person.name == "John Doe"
        assert person.email == "john@example.com"
        assert person.confidence == 1.0
        print("✓ Person entity validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Person entity failed: {e}")

    # Test Organization
    try:
        org = Organization(
            name="Acme Corp",
            industry="Technology",
            size="100-500",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        assert org.name == "Acme Corp"
        assert org.industry == "Technology"
        print("✓ Organization entity validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Organization entity failed: {e}")

    # Test Place
    try:
        place = Place(
            name="San Francisco Office",
            place_type="office",
            address="123 Market St",
            created_at=now,
            updated_at=now,
            extraction_tier="B",
            extraction_method="spacy_ner",
            confidence=0.85,
            extractor_version="1.0.0",
        )
        assert place.name == "San Francisco Office"
        assert place.place_type == "office"
        print("✓ Place entity validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Place entity failed: {e}")

    # Test Event
    try:
        event = Event(
            name="Product Launch",
            event_type="meeting",
            start_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC),
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="gmail_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        assert event.name == "Product Launch"
        assert event.event_type == "meeting"
        assert event.end_time > event.start_time
        print("✓ Event entity validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Event entity failed: {e}")

    # Test File
    try:
        file = File(
            name="README.md",
            file_id="file_123",
            source="github",
            mime_type="text/markdown",
            size_bytes=1024,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        assert file.name == "README.md"
        assert file.file_id == "file_123"
        assert file.size_bytes == 1024
        print("✓ File entity validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ File entity failed: {e}")

    return tests_passed


def test_base_relationship() -> int:
    """Test BaseRelationship."""
    print("\n=== Testing BaseRelationship ===")
    tests_passed = 0
    now = datetime.now(UTC)

    try:
        rel = BaseRelationship(
            created_at=now,
            source="job_123",
            confidence=0.95,
            extractor_version="1.0.0",
        )
        assert rel.confidence == 0.95
        assert rel.source == "job_123"
        print("✓ BaseRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ BaseRelationship failed: {e}")

    return tests_passed


def test_relationships() -> int:
    """Test all 10 relationship types."""
    print("\n=== Testing Relationship Types ===")
    tests_passed = 0
    now = datetime.now(UTC)

    # Test MentionsRelationship
    try:
        rel = MentionsRelationship(
            span="John Doe at Acme Corp",
            section="Introduction",
            chunk_id=uuid4(),
            created_at=now,
            source="job_123",
            extractor_version="1.0.0",
        )
        assert rel.span == "John Doe at Acme Corp"
        assert rel.section == "Introduction"
        print("✓ MentionsRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ MentionsRelationship failed: {e}")

    # Test WorksAtRelationship
    try:
        rel = WorksAtRelationship(
            role="Senior Engineer",
            start_date=datetime(2020, 1, 1, tzinfo=UTC),
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )
        assert rel.role == "Senior Engineer"
        print("✓ WorksAtRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ WorksAtRelationship failed: {e}")

    # Test RoutesToRelationship
    try:
        rel = RoutesToRelationship(
            host="example.com",
            path="/api",
            tls=True,
            auth_enabled=True,
            created_at=now,
            source="swag_reader",
            extractor_version="1.0.0",
        )
        assert rel.host == "example.com"
        assert rel.tls is True
        print("✓ RoutesToRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ RoutesToRelationship failed: {e}")

    # Test DependsOnRelationship
    try:
        rel = DependsOnRelationship(
            condition="service_healthy",
            created_at=now,
            source="docker_compose_reader",
            extractor_version="1.0.0",
        )
        assert rel.condition == "service_healthy"
        print("✓ DependsOnRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ DependsOnRelationship failed: {e}")

    # Test SentRelationship
    try:
        rel = SentRelationship(
            sent_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            created_at=now,
            source="gmail_reader",
            extractor_version="1.0.0",
        )
        assert rel.sent_at.year == 2024
        print("✓ SentRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ SentRelationship failed: {e}")

    # Test ContributesToRelationship
    try:
        rel = ContributesToRelationship(
            commit_count=150,
            first_commit_at=datetime(2020, 1, 1, tzinfo=UTC),
            last_commit_at=datetime(2024, 1, 15, tzinfo=UTC),
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )
        assert rel.commit_count == 150
        print("✓ ContributesToRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ ContributesToRelationship failed: {e}")

    # Test CreatedRelationship
    try:
        rel = CreatedRelationship(
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )
        assert rel.confidence == 1.0  # Default
        print("✓ CreatedRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ CreatedRelationship failed: {e}")

    # Test BelongsToRelationship
    try:
        rel = BelongsToRelationship(
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )
        assert rel.confidence == 1.0  # Default
        print("✓ BelongsToRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ BelongsToRelationship failed: {e}")

    # Test InThreadRelationship
    try:
        rel = InThreadRelationship(
            created_at=now,
            source="gmail_reader",
            extractor_version="1.0.0",
        )
        assert rel.confidence == 1.0  # Default
        print("✓ InThreadRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ InThreadRelationship failed: {e}")

    # Test LocatedInRelationship
    try:
        rel = LocatedInRelationship(
            created_at=now,
            source="tailscale_reader",
            extractor_version="1.0.0",
        )
        assert rel.confidence == 1.0  # Default
        print("✓ LocatedInRelationship validated")
        tests_passed += 1
    except Exception as e:
        print(f"✗ LocatedInRelationship failed: {e}")

    return tests_passed


def main() -> None:
    """Run all validation tests."""
    print("=" * 60)
    print("PHASE 1 VALIDATION - Neo4j Schema Refactor")
    print("=" * 60)

    entity_tests = test_entities()
    base_rel_tests = test_base_relationship()
    relationship_tests = test_relationships()

    total_tests = entity_tests + base_rel_tests + relationship_tests
    expected_tests = 16  # 5 entities + 1 base rel + 10 relationships

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Core Entities:     {entity_tests}/5 passed")
    print(f"BaseRelationship:  {base_rel_tests}/1 passed")
    print(f"Relationships:     {relationship_tests}/10 passed")
    print(f"\nTotal:             {total_tests}/{expected_tests} passed")

    if total_tests == expected_tests:
        print("\n✓✓✓ PHASE 1 COMPLETE - ALL TESTS PASSED ✓✓✓")
        print("\nImplemented:")
        print("  • 5 core entities (Person, Organization, Place, Event, File)")
        print("  • BaseRelationship with temporal tracking")
        print("  • 10 relationship types with Pydantic schemas")
        print("  • Neo4j constraints updated")
        print("\nReady for Phase 2: Reader-specific entities")
    else:
        print(f"\n✗ {expected_tests - total_tests} tests failed")
        exit(1)


if __name__ == "__main__":
    main()
