"""End-to-end integration test for query workflow."""

import os
from datetime import UTC, datetime

import pytest

from packages.core.use_cases.query import execute_query
from packages.graph.client import Neo4jClient
from packages.vector.qdrant_client import QdrantClient as QdrantClientWrapper


@pytest.mark.integration
@pytest.mark.slow
def test_query_e2e_workflow() -> None:
    """
    Test complete query workflow end-to-end:
    1. Verify services healthy
    2. Execute query
    3. Validate response format
    4. Check latency targets
    """
    # Config from environment (use host ports from docker-compose.yaml)
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:7000")
    qdrant_collection = os.getenv("QDRANT_COLLECTION", "documents")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "AVqx64QRKmogToi2CykgYqA2ZkbbAGja")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Step 1: Verify services healthy
    qdrant_client = QdrantClientWrapper(url=qdrant_url)
    assert qdrant_client.is_healthy(), "Qdrant not healthy"

    neo4j_client = Neo4jClient(uri=neo4j_uri, username=neo4j_user, password=neo4j_password)
    assert neo4j_client.is_healthy(), "Neo4j not healthy"

    # Step 2: Execute query
    result = execute_query(
        query="Which services expose port 8080?",
        qdrant_url=qdrant_url,
        qdrant_collection=qdrant_collection,
        neo4j_uri=neo4j_uri,
        neo4j_username=neo4j_user,
        neo4j_password=neo4j_password,
        ollama_base_url=ollama_url,
        top_k=20,
        rerank_top_n=5,
    )

    # Step 3: Validate response format
    assert result is not None
    assert "answer" in result
    assert "sources" in result
    assert "latency_ms" in result
    assert "latency_breakdown" in result
    assert "vector_count" in result
    assert "graph_count" in result

    # Step 4: Validate answer structure
    answer = result["answer"]
    assert isinstance(answer, str)
    assert len(answer) > 0

    # Step 5: Check latency targets (<5s median)
    latency_ms = result["latency_ms"]
    assert latency_ms < 10000, f"Query latency {latency_ms}ms exceeds 10s threshold"

    # Breakdown should have retrieval and synthesis
    breakdown = result["latency_breakdown"]
    assert "retrieval_ms" in breakdown
    assert "synthesis_ms" in breakdown

    # Step 6: Validate sources
    sources = result["sources"]
    assert isinstance(sources, list)

    # Cleanup
    qdrant_client.close()
    neo4j_client.close()


@pytest.mark.integration
@pytest.mark.slow
def test_query_with_source_filters() -> None:
    """Test query with source type filters."""
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:7000")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "AVqx64QRKmogToi2CykgYqA2ZkbbAGja")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    result = execute_query(
        query="Show all services",
        qdrant_url=qdrant_url,
        neo4j_uri=neo4j_uri,
        neo4j_username=neo4j_user,
        neo4j_password=neo4j_password,
        ollama_base_url=ollama_url,
        source_types=["web", "docker_compose"],
        top_k=10,
    )

    assert result is not None
    assert "answer" in result


@pytest.mark.integration
@pytest.mark.slow
def test_query_with_date_filter() -> None:
    """Test query with date filter."""
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:7000")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "AVqx64QRKmogToi2CykgYqA2ZkbbAGja")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Filter for recent documents
    after_date = datetime(2025, 10, 1, tzinfo=UTC)

    result = execute_query(
        query="Recent infrastructure changes",
        qdrant_url=qdrant_url,
        neo4j_uri=neo4j_uri,
        neo4j_username=neo4j_user,
        neo4j_password=neo4j_password,
        ollama_base_url=ollama_url,
        after=after_date,
        top_k=10,
    )

    assert result is not None
    assert "answer" in result


@pytest.mark.integration
@pytest.mark.slow
def test_query_empty_results_gracefully() -> None:
    """Test query handles empty results gracefully."""
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:7000")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "AVqx64QRKmogToi2CykgYqA2ZkbbAGja")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Query unlikely to match anything
    result = execute_query(
        query="xyzabc123nonsensicalquery",
        qdrant_url=qdrant_url,
        neo4j_uri=neo4j_uri,
        neo4j_username=neo4j_user,
        neo4j_password=neo4j_password,
        ollama_base_url=ollama_url,
        top_k=5,
    )

    # Should return result even if no matches
    assert result is not None
    assert "answer" in result
