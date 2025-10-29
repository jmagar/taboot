"""Retrieval settings configuration for embeddings, LLM, and search parameters."""

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RetrievalSettings(BaseSettings):
    """Configuration for retrieval system components."""

    # TEI Embeddings
    tei_embedding_url: str = Field(
        default=os.getenv("TEI_EMBEDDING_URL", "http://taboot-embed:80"),
        description="Text Embeddings Inference API URL",
    )
    embedding_dimension: int = Field(
        default=1024,
        description="Embedding vector dimension (Qwen3-Embedding-0.6B)",
    )
    embedding_model_name: str = Field(
        default="Qwen/Qwen3-Embedding-0.6B",
        description="Embedding model identifier",
    )

    # Ollama LLM
    ollama_base_url: str = Field(
        default=os.getenv("OLLAMA_BASE_URL", "http://localhost:4214"),
        description="Ollama API base URL",
    )
    llm_model_name: str = Field(
        default="qwen3:4b",
        description="LLM model for answer synthesis",
    )
    llm_temperature: float = Field(
        default=0.0,
        description="Temperature for deterministic synthesis",
    )

    # Vector Search
    top_k: int = Field(
        default=20,
        ge=5,
        le=50,
        description="Number of candidates from vector search",
    )
    rerank_top_n: int = Field(
        default=5,
        ge=3,
        le=20,
        description="Number of chunks after reranking",
    )

    # Graph Traversal
    max_graph_hops: int = Field(
        default=2,
        ge=1,
        le=3,
        description="Maximum hops for graph traversal",
    )
    relationship_priority: list[str] = Field(
        default=["DEPENDS_ON", "ROUTES_TO", "BINDS", "EXPOSES_ENDPOINT", "MENTIONS"],
        description="Priority order for relationship types in graph traversal",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra env vars not defined in model
    )
