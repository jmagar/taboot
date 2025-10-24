"""Hybrid retriever combining vector search with graph traversal."""

from typing import Any

from packages.graph.traversal import GraphTraversal
from packages.ingest.embedder import get_embedding
from packages.vector.reranker import Reranker
from packages.vector.search import VectorSearch


class HybridRetriever:
    """Combines vector search, reranking, and graph traversal."""

    def __init__(
        self,
        qdrant_url: str,
        qdrant_collection: str,
        neo4j_uri: str,
        neo4j_username: str,
        neo4j_password: str,
        reranker_model: str = "Qwen/Qwen3-Reranker-0.6B",
        reranker_device: str = "auto",
        tei_embedding_url: str | None = None,
    ):
        """
        Initialize hybrid retriever.

        Args:
            qdrant_url: Qdrant server URL
            qdrant_collection: Qdrant collection name
            neo4j_uri: Neo4j connection URI
            neo4j_username: Neo4j username
            neo4j_password: Neo4j password
            reranker_model: Reranker model name
            reranker_device: Reranker device ('cpu', 'cuda', 'auto')
            tei_embedding_url: TEI API URL for query embedding
        """
        self.qdrant_url = qdrant_url
        self.neo4j_uri = neo4j_uri

        # Initialize components
        self.vector_search = VectorSearch(qdrant_url=qdrant_url, collection_name=qdrant_collection)

        self.reranker = Reranker(model_name=reranker_model, device=reranker_device, batch_size=16)

        self.graph_traversal = GraphTraversal(
            neo4j_uri=neo4j_uri, username=neo4j_username, password=neo4j_password, max_hops=2
        )

        self.tei_url = tei_embedding_url or "http://taboot-embed:80"

    def retrieve(
        self,
        query: str,
        top_k: int = 20,
        rerank_top_n: int = 5,
        max_graph_hops: int = 2,
        source_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid retrieval: vector search → rerank → graph expansion.

        Args:
            query: Query string
            top_k: Number of candidates from vector search
            rerank_top_n: Number of chunks after reranking
            max_graph_hops: Maximum graph traversal depth
            source_types: Filter by source types

        Returns:
            List of retrieved contexts with vector and graph results
        """
        # Step 1: Get query embedding
        query_embedding = get_embedding(query, tei_url=self.tei_url)

        # Step 2: Vector search
        vector_results = self.vector_search.search(
            query_embedding=query_embedding, top_k=top_k, source_types=source_types
        )

        if not vector_results:
            return []

        # Step 3: Rerank
        passages = [r["content"] for r in vector_results]
        reranked_indices = self.reranker.rerank_with_indices(
            query=query, passages=passages, top_n=rerank_top_n
        )

        top_results = [vector_results[idx] for idx, _ in reranked_indices]

        # Step 4: Extract entity names from top chunks
        entity_names = self._extract_entity_names(top_results)

        # Step 5: Graph traversal from entities
        graph_results = []
        if entity_names:
            graph_results = self.graph_traversal.traverse_from_entities(
                entity_names=entity_names, max_hops=max_graph_hops
            )

        # Step 6: Combine results
        combined = {
            "vector_results": top_results,
            "graph_results": graph_results,
            "entity_names": entity_names,
        }

        return [combined]

    def _extract_entity_names(self, chunks: list[dict[str, Any]]) -> list[str]:
        """
        Extract entity names mentioned in chunks.

        Args:
            chunks: List of chunk results with metadata

        Returns:
            List of unique entity names
        """
        # Placeholder: Extract from metadata or use NER
        # For now, return empty list (implement based on chunk metadata)
        entity_names = []

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            if "entities" in metadata:
                entity_names.extend(metadata["entities"])

        return list(set(entity_names))

    def close(self) -> None:
        """Close connections."""
        self.graph_traversal.close()
