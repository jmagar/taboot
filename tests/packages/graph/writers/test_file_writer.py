"""Tests for FileWriter following TDD red-green-refactor pattern.

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
from packages.graph.writers.file_writer import FileWriter
from packages.schemas.core.file import File


@pytest.fixture
def neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all File nodes after test
    with client.session() as session:
        session.run("MATCH (f:File) DETACH DELETE f")

    client.close()


@pytest.fixture
def file_writer(neo4j_client: Neo4jClient) -> FileWriter:
    """Create FileWriter instance."""
    return FileWriter(neo4j_client=neo4j_client, batch_size=2000)


@pytest.fixture
def sample_file() -> File:
    """Create a sample File entity."""
    return File(
        name="README.md",
        file_id="file_12345",
        source="github",
        mime_type="text/markdown",
        size_bytes=1024,
        url="https://github.com/org/repo/blob/main/README.md",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 10, 8, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_files_batch() -> list[File]:
    """Create a batch of 2500 File entities (exceeds batch_size)."""
    files = []
    for i in range(2500):
        files.append(
            File(
                name=f"file_{i}.txt",
                file_id=f"file_{i}",
                source=["github", "gmail", "youtube", "filesystem"][i % 4],
                mime_type=["text/plain", "application/pdf", "video/mp4", "image/png"][i % 4],
                size_bytes=1024 * (i + 1),
                url=f"https://example.com/files/file_{i}.txt",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        )
    return files


def test_write_files_empty_list(file_writer: FileWriter) -> None:
    """Test writing empty list returns zero counts."""
    result = file_writer.write_files([])

    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_files_single_entity(
    file_writer: FileWriter, sample_file: File, neo4j_client: Neo4jClient
) -> None:
    """Test writing a single File entity."""
    result = file_writer.write_files([sample_file])

    assert result["total_written"] == 1
    assert result["batches_executed"] == 1

    # Verify node was created in Neo4j
    with neo4j_client.session() as session:
        query = "MATCH (f:File {file_id: $file_id}) RETURN f"
        record = session.run(query, {"file_id": sample_file.file_id}).single()

        assert record is not None
        node = record["f"]
        assert node["name"] == sample_file.name
        assert node["file_id"] == sample_file.file_id
        assert node["source"] == sample_file.source
        assert node["mime_type"] == sample_file.mime_type
        assert node["size_bytes"] == sample_file.size_bytes
        assert node["url"] == sample_file.url
        assert node["extraction_tier"] == sample_file.extraction_tier
        assert node["extraction_method"] == sample_file.extraction_method
        assert node["confidence"] == sample_file.confidence
        assert node["extractor_version"] == sample_file.extractor_version


def test_write_files_batch_2000(
    file_writer: FileWriter, sample_files_batch: list[File], neo4j_client: Neo4jClient
) -> None:
    """Test writing 2500 entities (requires 2 batches of 2000)."""
    result = file_writer.write_files(sample_files_batch)

    assert result["total_written"] == 2500
    assert result["batches_executed"] == 2  # 2000 + 500

    # Verify all nodes were created
    with neo4j_client.session() as session:
        query = "MATCH (f:File) RETURN count(f) AS count"
        record = session.run(query).single()
        assert record["count"] == 2500


def test_write_files_idempotent(
    file_writer: FileWriter, sample_file: File, neo4j_client: Neo4jClient
) -> None:
    """Test that writing same data twice is idempotent (updates, not duplicates)."""
    # Write first time
    result1 = file_writer.write_files([sample_file])
    assert result1["total_written"] == 1

    # Modify file slightly
    modified_file = sample_file.model_copy()
    modified_file.size_bytes = 2048  # Changed size
    modified_file.updated_at = datetime.now(UTC)

    # Write second time with same file_id (unique constraint)
    result2 = file_writer.write_files([modified_file])
    assert result2["total_written"] == 1

    # Verify only ONE node exists with UPDATED data
    with neo4j_client.session() as session:
        query = "MATCH (f:File {file_id: $file_id}) RETURN f, count(f) AS count"
        record = session.run(query, {"file_id": sample_file.file_id}).single()

        assert record["count"] == 1  # Only one node
        node = record["f"]
        assert node["size_bytes"] == 2048  # Updated value


def test_write_files_constraint_violation_duplicate_file_id(
    file_writer: FileWriter, sample_file: File
) -> None:
    """Test that duplicate file_ids within same batch are handled correctly.

    Note: Neo4j MERGE handles this gracefully - last value wins.
    This test verifies the writer doesn't crash on duplicate keys in batch.
    """
    # Create two files with same file_id
    file1 = sample_file
    file2 = sample_file.model_copy()
    file2.name = "DIFFERENT.md"  # Different name, same file_id

    # Should succeed - MERGE will update the same node twice
    result = file_writer.write_files([file1, file2])
    assert result["total_written"] == 2  # Both writes processed
    assert result["batches_executed"] == 1


def test_write_files_minimal_fields(neo4j_client: Neo4jClient) -> None:
    """Test that File entities can be created with minimal fields."""
    writer = FileWriter(neo4j_client=neo4j_client)

    minimal_file = File(
        name="minimal.txt",
        file_id="minimal_123",
        source="filesystem",
        # All optional fields omitted
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="test",
        confidence=1.0,
        extractor_version="1.0.0",
    )

    result = writer.write_files([minimal_file])
    assert result["total_written"] == 1

    # Verify node was created with null optional fields
    with neo4j_client.session() as session:
        query = "MATCH (f:File {file_id: $file_id}) RETURN f"
        record = session.run(query, {"file_id": "minimal_123"}).single()

        assert record is not None
        node = record["f"]
        assert node["name"] == "minimal.txt"
        assert node["file_id"] == "minimal_123"
        assert node["source"] == "filesystem"
        assert node.get("mime_type") is None
        assert node.get("size_bytes") is None
        assert node.get("url") is None


def test_write_files_batch_size_configuration(neo4j_client: Neo4jClient) -> None:
    """Test that batch_size parameter is respected."""
    small_batch_writer = FileWriter(neo4j_client=neo4j_client, batch_size=100)

    files = [
        File(
            name=f"file_{i}.txt",
            file_id=f"batch_file_{i}",
            source="test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="test",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        for i in range(250)
    ]

    result = small_batch_writer.write_files(files)
    assert result["total_written"] == 250
    assert result["batches_executed"] == 3  # 100 + 100 + 50
