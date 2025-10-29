"""Tests for DocumentWriter following TDD red-green-refactor pattern.

Tests cover:
- Empty list handling
- Single entity write
- Batch 2000 write
- Idempotent writes (same data written twice)
- MENTIONS relationship creation
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from packages.graph.client import Neo4jClient
from packages.graph.writers.document_writer import DocumentWriter
from packages.schemas.relationships.mentions import MentionsRelationship
from packages.schemas.web.document import Document


@pytest.fixture
def neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()

    # Cleanup BEFORE test: Delete all nodes to ensure clean state
    with client.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    yield client

    # Cleanup AFTER test: Delete all nodes
    with client.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    client.close()


@pytest.fixture
def document_writer(neo4j_client: Neo4jClient) -> DocumentWriter:
    """Create DocumentWriter instance."""
    return DocumentWriter(neo4j_client=neo4j_client, batch_size=2000)


@pytest.fixture
def sample_document() -> Document:
    """Create a sample Document entity."""
    return Document(
        doc_id="doc_12345",
        source_url="https://docs.anthropic.com/claude",
        source_type="web",
        content_hash="sha256:abc123def456789",
        ingested_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        extraction_state="completed",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="firecrawl",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_documents_batch() -> list[Document]:
    """Create a batch of 2500 Document entities (exceeds batch_size)."""
    documents = []
    for i in range(2500):
        documents.append(
            Document(
                doc_id=f"doc_{i}",
                source_url=f"https://example.com/page{i}",
                source_type="web",
                content_hash=f"hash_{i}",
                ingested_at=datetime.now(UTC),
                extraction_state="pending",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="firecrawl",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        )
    return documents


def test_write_documents_empty_list(document_writer: DocumentWriter) -> None:
    """Test writing empty list returns zero counts."""
    result = document_writer.write_documents([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_documents_single_entity(
    document_writer: DocumentWriter, sample_document: Document, neo4j_client: Neo4jClient
) -> None:
    """Test writing a single Document entity."""
    result = document_writer.write_documents([sample_document])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node was created in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (d:Document {doc_id: $doc_id}) RETURN d"
        record = session.run(query, {"doc_id": sample_document.doc_id}).single()

        assert record is not None
        node = record["d"]
        assert node["doc_id"] == sample_document.doc_id
        assert node["source_url"] == sample_document.source_url
        assert node["source_type"] == sample_document.source_type
        assert node["content_hash"] == sample_document.content_hash
        assert node["extraction_state"] == sample_document.extraction_state
        assert node["extraction_tier"] == sample_document.extraction_tier
        assert node["extraction_method"] == sample_document.extraction_method
        assert node["confidence"] == sample_document.confidence
        assert node["extractor_version"] == sample_document.extractor_version


def test_write_documents_batch_2000(
    document_writer: DocumentWriter,
    sample_documents_batch: list[Document],
    neo4j_client: Neo4jClient,
) -> None:
    """Test writing 2500 entities (requires 2 batches of 2000)."""
    result = document_writer.write_documents(sample_documents_batch)

    assert result["total_written"] == 2500
    assert result["batches_executed"] == 2  # 2000 + 500

    # Verify all nodes were created
    with neo4j_client.session() as session:
        query = "MATCH (d:Document) RETURN count(d) AS count"
        record = session.run(query).single()
        assert record["count"] == 2500


def test_write_documents_idempotent(
    document_writer: DocumentWriter, sample_document: Document, neo4j_client: Neo4jClient
) -> None:
    """Test that writing same data twice is idempotent (updates, not duplicates)."""
    # Write first time
    result1 = document_writer.write_documents([sample_document])
    assert result1["total_written"] == 1

    # Modify document slightly
    modified_document = sample_document.model_copy()
    modified_document.extraction_state = "processing"  # Changed state
    modified_document.updated_at = datetime.now(UTC)

    # Write second time with same doc_id (unique constraint)
    result2 = document_writer.write_documents([modified_document])
    assert result2["total_written"] == 1

    # Verify only ONE node exists with UPDATED data
    with neo4j_client.session() as session:
        query = "MATCH (d:Document {doc_id: $doc_id}) RETURN d, count(d) AS count"
        record = session.run(query, {"doc_id": sample_document.doc_id}).single()

        assert record["count"] == 1  # Only one node
        node = record["d"]
        assert node["extraction_state"] == "processing"  # Updated value


def test_write_mentions_relationships_empty_list(document_writer: DocumentWriter) -> None:
    """Test writing empty list returns zero counts."""
    result = document_writer.write_mentions_relationships([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_mentions_relationships_single(
    document_writer: DocumentWriter, sample_document: Document, neo4j_client: Neo4jClient
) -> None:
    """Test writing a single MENTIONS relationship."""
    # First create the document and a Person node
    document_writer.write_documents([sample_document])

    # Create a target entity (Person for testing)
    with neo4j_client.session() as session:
        session.run(
            """
            CREATE (p:Person {email: 'john@example.com', name: 'John Doe'})
            """
        )

    # Create MENTIONS relationship
    mention = MentionsRelationship(
        span="John Doe works at Acme Corp",
        section="Introduction",
        chunk_id=uuid4(),
        created_at=datetime.now(UTC),
        source="job_12345",
        confidence=0.95,
        extractor_version="1.0.0",
    )

    result = document_writer.write_mentions_relationships(
        [
            {
                "doc_id": sample_document.doc_id,
                "entity_type": "Person",
                "entity_key": "email",
                "entity_value": "john@example.com",
                "relationship": mention,
            }
        ]
    )

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify relationship was created
    with neo4j_client.session() as session:
        query = """
        MATCH (d:Document {doc_id: $doc_id})-[r:MENTIONS]->(p:Person)
        RETURN r, p
        """
        record = session.run(query, {"doc_id": sample_document.doc_id}).single()

        assert record is not None
        rel = record["r"]
        assert rel["span"] == mention.span
        assert rel["section"] == mention.section
        assert rel["chunk_id"] == str(mention.chunk_id)
        assert rel["confidence"] == mention.confidence


def test_write_mentions_relationships_batch_2000(
    document_writer: DocumentWriter, sample_document: Document, neo4j_client: Neo4jClient
) -> None:
    """Test writing 2500 MENTIONS relationships (requires 2 batches)."""
    # Create document and 2500 Person nodes
    document_writer.write_documents([sample_document])

    with neo4j_client.session() as session:
        session.run(
            """
            UNWIND range(0, 2499) AS i
            CREATE (p:Person {email: 'person' + i + '@example.com', name: 'Person ' + i})
            """
        )

    # Create 2500 MENTIONS relationships
    mentions = []
    for i in range(2500):
        mention = MentionsRelationship(
            span=f"Person {i} mentioned",
            section="Content",
            chunk_id=uuid4(),
            created_at=datetime.now(UTC),
            source="job_12345",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        mentions.append(
            {
                "doc_id": sample_document.doc_id,
                "entity_type": "Person",
                "entity_key": "email",
                "entity_value": f"person{i}@example.com",
                "relationship": mention,
            }
        )

    result = document_writer.write_mentions_relationships(mentions)

    assert result["total_written"] == 2500
    assert result["batches_executed"] == 2  # 2000 + 500

    # Verify all relationships were created
    with neo4j_client.session() as session:
        query = """
        MATCH (d:Document {doc_id: $doc_id})-[r:MENTIONS]->()
        RETURN count(r) AS count
        """
        record = session.run(query, {"doc_id": sample_document.doc_id}).single()
        assert record["count"] == 2500


def test_write_mentions_relationships_idempotent(
    document_writer: DocumentWriter, sample_document: Document, neo4j_client: Neo4jClient
) -> None:
    """Test that writing same relationship twice is idempotent."""
    # Create document and person
    document_writer.write_documents([sample_document])

    with neo4j_client.session() as session:
        session.run(
            """
            CREATE (p:Person {email: 'john@example.com', name: 'John Doe'})
            """
        )

    mention = MentionsRelationship(
        span="John Doe mentioned",
        section="Introduction",
        chunk_id=uuid4(),
        created_at=datetime.now(UTC),
        source="job_12345",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    relationship_data = {
        "doc_id": sample_document.doc_id,
        "entity_type": "Person",
        "entity_key": "email",
        "entity_value": "john@example.com",
        "relationship": mention,
    }

    # Write first time
    result1 = document_writer.write_mentions_relationships([relationship_data])
    assert result1["total_written"] == 1

    # Write second time with same data
    result2 = document_writer.write_mentions_relationships([relationship_data])
    assert result2["total_written"] == 1

    # Verify only ONE relationship exists
    with neo4j_client.session() as session:
        query = """
        MATCH (d:Document {doc_id: $doc_id})-[r:MENTIONS]->(p:Person)
        RETURN count(r) AS count
        """
        record = session.run(query, {"doc_id": sample_document.doc_id}).single()
        assert record["count"] == 1  # Only one relationship


def test_write_documents_batch_size_configuration(neo4j_client: Neo4jClient) -> None:
    """Test that batch_size parameter is respected."""
    small_batch_writer = DocumentWriter(neo4j_client=neo4j_client, batch_size=100)

    documents = [
        Document(
            doc_id=f"doc_batch_{i}",
            source_url=f"https://example.com/batch{i}",
            source_type="web",
            content_hash=f"hash_{i}",
            ingested_at=datetime.now(UTC),
            extraction_state="pending",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="test",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        for i in range(250)
    ]

    result = small_batch_writer.write_documents(documents)
    assert result["total_written"] == 250
    assert result["batches_executed"] == 3  # 100 + 100 + 50
