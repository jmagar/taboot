"""Tests for hybrid retriever combining vector search and graph traversal."""

import pytest

from packages.retrieval.retrievers.hybrid import HybridRetriever


@pytest.mark.unit
def test_hybrid_retriever_init():
    """Test HybridRetriever initialization."""
    retriever = HybridRetriever(
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_documents",
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="test"
    )

    assert retriever.qdrant_url == "http://localhost:6333"
    assert retriever.neo4j_uri == "bolt://localhost:7687"


@pytest.mark.integration
@pytest.mark.slow
def test_hybrid_retriever_with_real_services(qdrant_client, neo4j_client):
    """Test hybrid retriever against real Qdrant and Neo4j."""
    retriever = HybridRetriever(
        qdrant_url="http://localhost:7000",  # Host port mapping
        qdrant_collection="test_documents",
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="changeme",
        tei_embedding_url="http://localhost:8080"  # Real TEI service
    )

    # Test retrieval
    results = retriever.retrieve(
        query="Which services expose port 8080?",
        top_k=10,
        max_graph_hops=2
    )

    assert isinstance(results, list)
