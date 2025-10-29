"""Query orchestration use-case coordinating retrieval and synthesis."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from packages.retrieval.query_engines.qa import QAConfig, QAQueryEngine


def execute_query(
    query: str,
    qdrant_url: str,
    neo4j_uri: str,
    neo4j_username: str,
    neo4j_password: str,
    qdrant_collection: str = "documents",
    tei_embedding_url: str | None = None,
    ollama_base_url: str = "http://localhost:11434",
    reranker_url: str = "http://localhost:8000",
    reranker_timeout: float = 30.0,
    reranker_model: str = "Qwen/Qwen3-Reranker-0.6B",
    reranker_device: str = "auto",
    reranker_batch_size: int = 16,
    top_k: int = 20,
    rerank_top_n: int = 5,
    source_types: list[str] | None = None,
    after: datetime | None = None,
    dry_run: bool = False,
) -> dict[str, Any] | None:
    """
    Execute natural language query with hybrid retrieval.

    Args:
        query: User question
        qdrant_url: Qdrant server URL
        neo4j_uri: Neo4j connection URI
        neo4j_username: Neo4j username
        neo4j_password: Neo4j password
        qdrant_collection: Qdrant collection name
        ollama_base_url: Ollama API URL
        top_k: Candidates from vector search
        rerank_top_n: Chunks after reranking
        source_types: Filter by source types
        after: Filter by ingestion date
        dry_run: If True, skip actual query execution

    Returns:
        Query result with answer, sources, and latency

    Raises:
        ValueError: If query is empty
    """
    # Validation
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if dry_run:
        return None

    # Initialize query engine
    config = QAConfig(
        qdrant_url=qdrant_url,
        qdrant_collection=qdrant_collection,
        neo4j_uri=neo4j_uri,
        neo4j_username=neo4j_username,
        neo4j_password=neo4j_password,
        tei_embedding_url=tei_embedding_url,
        ollama_base_url=ollama_base_url,
        reranker_url=reranker_url,
        reranker_timeout=reranker_timeout,
        reranker_model=reranker_model,
        reranker_device=reranker_device,
        reranker_batch_size=reranker_batch_size,
    )
    engine = QAQueryEngine(config=config)

    try:
        # Execute query
        result = engine.query(
            question=query, top_k=top_k, rerank_top_n=rerank_top_n, source_types=source_types
        )

        return result

    finally:
        engine.close()
