"""Tests for retrieval settings configuration."""

import pytest

from packages.retrieval.context.settings import RetrievalSettings


@pytest.mark.unit
def test_retrieval_settings_loads_tei_config():
    """Test that retrieval settings loads TEI embedding configuration."""
    settings = RetrievalSettings()

    assert settings.tei_embedding_url is not None
    assert settings.embedding_dimension == 1024
    assert settings.embedding_model_name == "Qwen/Qwen3-Embedding-0.6B"


@pytest.mark.unit
def test_retrieval_settings_loads_ollama_config():
    """Test that retrieval settings loads Ollama LLM configuration."""
    settings = RetrievalSettings()

    assert settings.ollama_base_url is not None
    assert settings.llm_model_name == "qwen3:4b"
    assert settings.llm_temperature == 0.0  # Deterministic for synthesis


@pytest.mark.unit
def test_retrieval_settings_loads_search_params():
    """Test that retrieval settings loads vector search parameters."""
    settings = RetrievalSettings()

    assert settings.top_k >= 5
    assert settings.top_k <= 20
    assert settings.rerank_top_n >= 3
    assert settings.rerank_top_n <= settings.top_k


@pytest.mark.unit
def test_retrieval_settings_loads_graph_params():
    """Test that retrieval settings loads graph traversal parameters."""
    settings = RetrievalSettings()

    assert settings.max_graph_hops == 2
    assert settings.relationship_priority is not None
    assert len(settings.relationship_priority) > 0
    assert "DEPENDS_ON" in settings.relationship_priority
