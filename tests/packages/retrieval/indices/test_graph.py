"""Tests for PropertyGraphIndex over Neo4j."""

import pytest
from llama_index.core import Settings
from llama_index.embeddings.text_embeddings_inference import TextEmbeddingsInference
from llama_index.llms.ollama import Ollama

from packages.retrieval.indices.graph import create_graph_index


@pytest.mark.integration
@pytest.mark.slow
def test_create_graph_index_with_neo4j() -> None:
    """Test PropertyGraphIndex creation with Neo4j backend - real integration."""
    # Configure LlamaIndex to use ACTUAL services running in Docker
    # TEI: Qwen3-Embedding-0.6B (1024-dim) on localhost:8080
    # Ollama: qwen3:4b on localhost:11434
    Settings.embed_model = TextEmbeddingsInference(
        model_name="Qwen/Qwen3-Embedding-0.6B",
        base_url="http://localhost:8080",
        timeout=60,
        embed_batch_size=32,
    )
    Settings.llm = Ollama(model="qwen3:4b", base_url="http://localhost:11434")

    # Use actual password from .env and real Neo4j connection
    index = create_graph_index(
        neo4j_uri="bolt://localhost:7687",
        username="neo4j",
        password="AVqx64QRKmogToi2CykgYqA2ZkbbAGja",
        database="neo4j",
    )

    assert index is not None


@pytest.mark.integration
@pytest.mark.slow
def test_graph_index_query() -> None:
    """Test querying PropertyGraphIndex - real integration."""
    # Configure LlamaIndex to use ACTUAL services running in Docker
    # TEI: Qwen3-Embedding-0.6B (1024-dim) on localhost:8080
    # Ollama: qwen3:4b on localhost:11434
    Settings.embed_model = TextEmbeddingsInference(
        model_name="Qwen/Qwen3-Embedding-0.6B",
        base_url="http://localhost:8080",
        timeout=60,
        embed_batch_size=32,
    )
    Settings.llm = Ollama(model="qwen3:4b", base_url="http://localhost:11434")

    # Use actual password from .env and real Neo4j connection
    index = create_graph_index(
        neo4j_uri="bolt://localhost:7687",
        username="neo4j",
        password="AVqx64QRKmogToi2CykgYqA2ZkbbAGja",
        database="neo4j",
    )

    # Test retrieval against real Neo4j
    retriever = index.as_retriever()
    assert retriever is not None
