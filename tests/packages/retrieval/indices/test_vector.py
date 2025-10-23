"""Tests for VectorStoreIndex over Qdrant."""

import os
import pytest
from packages.retrieval.indices.vector import create_vector_index
from llama_index.core import Settings
from llama_index.embeddings.text_embeddings_inference import TextEmbeddingsInference


@pytest.mark.integration
@pytest.mark.slow
def test_create_vector_index_with_qdrant():
    """Test VectorStoreIndex creation with Qdrant backend - real integration."""
    # Configure LlamaIndex to use ACTUAL TEI service (Qwen3-Embedding-0.6B, 1024-dim)
    Settings.embed_model = TextEmbeddingsInference(
        model_name="Qwen/Qwen3-Embedding-0.6B",
        base_url="http://localhost:8080",
        timeout=60,
        embed_batch_size=32
    )

    # Use host port 7000 (maps to container port 6333 from docker-compose.yaml)
    index = create_vector_index(
        qdrant_url="http://localhost:7000",
        collection_name="test_documents",
        embedding_dim=1024
    )

    assert index is not None
    assert index.docstore is not None


@pytest.mark.integration
@pytest.mark.slow
def test_vector_index_query():
    """Test querying VectorStoreIndex - real integration."""
    # Configure LlamaIndex to use ACTUAL TEI service (Qwen3-Embedding-0.6B, 1024-dim)
    Settings.embed_model = TextEmbeddingsInference(
        model_name="Qwen/Qwen3-Embedding-0.6B",
        base_url="http://localhost:8080",
        timeout=60,
        embed_batch_size=32
    )

    # Use host port 7000 (maps to container port 6333 from docker-compose.yaml)
    index = create_vector_index(
        qdrant_url="http://localhost:7000",
        collection_name="test_documents",
        embedding_dim=1024
    )

    # Test retrieval against real Qdrant
    retriever = index.as_retriever(similarity_top_k=5)
    assert retriever is not None
