"""Tests for QA query engine with citations and latency tracking."""

import pytest
from packages.retrieval.query_engines.qa import QAQueryEngine


@pytest.mark.unit
def test_qa_query_engine_init():
    """Test QAQueryEngine initialization."""
    engine = QAQueryEngine(
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_documents",
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="test",
        ollama_base_url="http://localhost:11434"
    )

    assert engine.qdrant_url == "http://localhost:6333"
    assert engine.neo4j_uri == "bolt://localhost:7687"


@pytest.mark.integration
@pytest.mark.slow
def test_qa_query_engine_with_real_services(qdrant_client, neo4j_client):
    """Test query engine against real services."""
    engine = QAQueryEngine(
        qdrant_url="http://localhost:7000",  # Host port mapping
        qdrant_collection="test_documents",
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="changeme",
        ollama_base_url="http://localhost:11434",
        tei_embedding_url="http://localhost:8080"  # Real TEI service
    )

    response = engine.query(
        question="Which services expose port 8080?",
        top_k=10
    )

    assert response is not None
    assert "answer" in response
    assert "latency_ms" in response


@pytest.mark.unit
def test_qa_query_engine_formats_citations():
    """Test citation formatting in answers."""
    engine = QAQueryEngine(
        qdrant_url="http://localhost:6333",
        qdrant_collection="test",
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="test"
    )

    sources = [
        ("API Docs", "https://docs.example.com/api"),
        ("Config Guide", "https://docs.example.com/config")
    ]

    formatted = engine.format_sources(sources)
    assert "[1]" in formatted
    assert "[2]" in formatted
    assert "https://docs.example.com/api" in formatted
