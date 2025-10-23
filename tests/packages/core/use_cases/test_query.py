"""Tests for query orchestration use-case."""

import pytest
from packages.core.use_cases.query import execute_query


@pytest.mark.unit
def test_execute_query_validates_inputs():
    """Test query validation."""
    # Empty query should raise error
    with pytest.raises(ValueError, match="[Qq]uery cannot be empty"):
        execute_query(
            query="",
            qdrant_url="http://localhost:6333",
            neo4j_uri="bolt://localhost:7687",
            neo4j_username="neo4j",
            neo4j_password="test"
        )


@pytest.mark.integration
@pytest.mark.slow
def test_execute_query_with_real_services(qdrant_client, neo4j_client):
    """Test query execution against real services."""
    result = execute_query(
        query="Which services expose port 8080?",
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_documents",
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="changeme",
        ollama_base_url="http://localhost:11434",
        top_k=10
    )

    assert result is not None
    assert "answer" in result
    assert "latency_ms" in result
    assert result["latency_ms"] > 0


@pytest.mark.unit
def test_execute_query_with_filters():
    """Test query with source type and date filters."""
    from datetime import datetime, UTC

    # Should not raise error
    result = execute_query(
        query="test question",
        qdrant_url="http://localhost:6333",
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="test",
        source_types=["web", "docker_compose"],
        after=datetime(2025, 10, 1, tzinfo=UTC),
        dry_run=True  # Don't actually query
    )

    # Dry run should return None or placeholder
    assert result is None or isinstance(result, dict)
