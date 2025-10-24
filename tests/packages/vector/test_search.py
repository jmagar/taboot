"""Tests for Qdrant vector search with metadata filters."""

from datetime import UTC, datetime

import pytest

from packages.vector.search import VectorSearch


@pytest.mark.unit
def test_vector_search_init() -> None:
    """Test VectorSearch initialization."""
    search = VectorSearch(qdrant_url="http://localhost:6333", collection_name="test_collection")

    assert search.collection_name == "test_collection"
    assert search.qdrant_url == "http://localhost:6333"


@pytest.mark.unit
def test_vector_search_builds_metadata_filter() -> None:
    """Test metadata filter construction for source types and dates."""
    search = VectorSearch(qdrant_url="http://localhost:6333", collection_name="test")

    # Test source filter
    filter_dict = search.build_metadata_filter(source_types=["web", "docker_compose"])
    assert filter_dict is not None
    assert "source_type" in str(filter_dict)

    # Test date filter
    after_date = datetime(2025, 10, 15, tzinfo=UTC)
    filter_dict = search.build_metadata_filter(after=after_date)
    assert filter_dict is not None


@pytest.mark.integration
@pytest.mark.slow
def test_vector_search_with_real_qdrant(qdrant_client) -> None:
    """Test vector search against real Qdrant instance."""
    search = VectorSearch(qdrant_url="http://localhost:6333", collection_name="test_documents")

    # Create test embedding
    test_embedding = [0.1] * 1024

    results = search.search(query_embedding=test_embedding, top_k=10)

    assert isinstance(results, list)
    assert len(results) <= 10
