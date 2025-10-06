"""Query engine for LlamaCrawl RAG pipeline.

This module implements the query engine that orchestrates:
1. Query embedding generation (TEIEmbedding)
2. Vector search in Qdrant (top_k candidates)
3. Metadata filtering at query time
4. Reranking with TEIRerank (top_n results)
5. Graph traversal for related documents (Neo4j)
6. Result aggregation and ranking

The query engine integrates LlamaIndex components with custom TEI embedding
and reranking services, applying hybrid search patterns for optimal retrieval.
"""

import time
from datetime import datetime
from typing import Any

from llama_index.core import PropertyGraphIndex, StorageContext, VectorStoreIndex
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.vector_stores.qdrant import QdrantVectorStore

from llamacrawl.config import Config
from llamacrawl.embeddings.reranker import TEIRerank
from llamacrawl.embeddings.tei import TEIEmbedding
from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.storage.qdrant import QdrantClient
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)


class QueryEngine:
    """Query engine for hybrid search with vector retrieval, reranking, and graph traversal.

    This class orchestrates the complete query pipeline:
    1. Generate query embedding using TEIEmbedding
    2. Perform vector search in Qdrant with metadata filters (top_k candidates)
    3. Rerank results using TEIRerank (top_n results)
    4. Optionally traverse graph relationships in Neo4j for related documents
    5. Return ranked results with scores and metadata

    The engine supports filtering by source type, date ranges, and custom metadata,
    with all filters applied at Qdrant query time for efficiency.

    Attributes:
        config: Configuration object with query settings
        qdrant_client: Qdrant vector store client
        neo4j_client: Neo4j graph database client
        embed_model: TEI embedding model
        reranker: TEI reranker postprocessor
        vector_index: LlamaIndex VectorStoreIndex
        graph_index: LlamaIndex PropertyGraphIndex (optional)
    """

    def __init__(
        self,
        config: Config,
        qdrant_client: QdrantClient,
        neo4j_client: Neo4jClient,
        embed_model: TEIEmbedding,
        reranker: TEIRerank,
    ):
        """Initialize query engine with storage backends and models.

        Args:
            config: Configuration object with query settings
            qdrant_client: Qdrant vector store client
            neo4j_client: Neo4j graph database client
            embed_model: TEI embedding model instance
            reranker: TEI reranker postprocessor instance
        """
        self.config = config
        self.qdrant_client = qdrant_client
        self.neo4j_client = neo4j_client
        self.embed_model = embed_model
        self.reranker = reranker

        logger.info(
            "Initializing QueryEngine",
            extra={
                "top_k": config.query.top_k,
                "rerank_top_n": config.query.rerank_top_n,
                "enable_reranking": config.query.enable_reranking,
                "enable_graph_traversal": config.query.enable_graph_traversal,
                "max_graph_depth": config.query.max_graph_depth,
            },
        )

        # Initialize LlamaIndex components
        self._initialize_indexes()

        logger.info("QueryEngine initialized successfully")

    def _initialize_indexes(self) -> None:
        """Initialize LlamaIndex VectorStoreIndex and PropertyGraphIndex.

        Creates indexes from existing storage backends:
        - VectorStoreIndex from Qdrant
        - PropertyGraphIndex from Neo4j (if graph traversal enabled)
        """
        logger.debug("Initializing LlamaIndex indexes")

        # Create Qdrant vector store for LlamaIndex
        qdrant_vector_store = QdrantVectorStore(
            client=self.qdrant_client.client,
            collection_name=self.qdrant_client.collection_name,
        )

        # Create storage context with vector store
        storage_context = StorageContext.from_defaults(vector_store=qdrant_vector_store)

        # Initialize VectorStoreIndex from existing Qdrant collection
        self.vector_index = VectorStoreIndex.from_vector_store(
            vector_store=qdrant_vector_store,
            storage_context=storage_context,
            embed_model=self.embed_model,
        )

        logger.debug("VectorStoreIndex initialized from Qdrant")

        # Initialize PropertyGraphIndex if graph traversal is enabled
        if self.config.query.enable_graph_traversal:
            try:
                # Create Neo4j graph store for LlamaIndex
                neo4j_graph_store = Neo4jPropertyGraphStore(
                    username=self.neo4j_client.username,
                    password=self.neo4j_client.password,
                    url=self.neo4j_client.uri,
                )

                # Create PropertyGraphIndex from existing Neo4j graph
                self.graph_index: PropertyGraphIndex | None = PropertyGraphIndex.from_existing(
                    property_graph_store=neo4j_graph_store,
                    embed_model=self.embed_model,
                )

                logger.debug("PropertyGraphIndex initialized from Neo4j")

            except Exception as e:
                logger.warning(
                    f"Failed to initialize PropertyGraphIndex: {e}. "
                    "Graph traversal will be disabled.",
                    extra={"error": str(e)},
                )
                self.graph_index = None
        else:
            self.graph_index = None
            logger.debug("Graph traversal disabled, skipping PropertyGraphIndex initialization")

    def query(
        self,
        query_text: str,
        sources: list[str] | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
        custom_filters: dict[str, Any] | None = None,
        top_k: int | None = None,
        top_n: int | None = None,
    ) -> dict[str, Any]:
        """Execute query pipeline with vector search, reranking, and graph traversal.

        Pipeline stages:
        1. Generate query embedding (TEIEmbedding)
        2. Vector search in Qdrant with metadata filters (top_k candidates)
        3. Rerank results with TEIRerank (top_n results) - if enabled
        4. Graph traversal for related documents (Neo4j) - if enabled
        5. Return ranked results with timing metrics

        Args:
            query_text: Query string to search for
            sources: Optional list of source types to filter by (e.g., ["github", "firecrawl"])
            after: Optional datetime to filter documents created/updated after
            before: Optional datetime to filter documents created/updated before
            custom_filters: Optional dict of custom metadata filters
                (e.g., {"repo_owner": "llamaindex"})
            top_k: Number of candidates to retrieve (overrides config, default: 20)
            top_n: Number of results after reranking (overrides config, default: 5)

        Returns:
            Dictionary with keys:
                - query: Original query text
                - results: List of result dicts with doc_id, score, title, content, metadata
                - related_docs: List of related documents from graph traversal (if enabled)
                - metrics: Performance metrics (total_time_ms, stages)

        Example:
            >>> results = engine.query(
            ...     "How does LlamaIndex work?",
            ...     sources=["documentation", "github"],
            ...     after=datetime(2025, 1, 1),
            ...     top_k=20,
            ...     top_n=5
            ... )
            >>> print(f"Found {len(results['results'])} results")
        """
        start_time = time.time()

        logger.info(
            "Query started",
            extra={
                "query": query_text,
                "sources": sources,
                "after": after.isoformat() if after else None,
                "before": before.isoformat() if before else None,
                "top_k": top_k or self.config.query.top_k,
                "top_n": top_n or self.config.query.rerank_top_n,
            },
        )

        # Use config defaults if not overridden
        top_k = top_k or self.config.query.top_k
        top_n = top_n or self.config.query.rerank_top_n

        # Initialize metrics tracking
        metrics: dict[str, Any] = {"stages": {}}

        # Stage 1: Generate query embedding
        stage_start = time.time()
        logger.debug("Stage 1: Generating query embedding")

        query_embedding = self.embed_model.get_query_embedding(query_text)

        metrics["stages"]["embedding"] = (time.time() - stage_start) * 1000
        logger.debug(
            "Query embedding generated",
            extra={
                "embedding_dim": len(query_embedding),
                "time_ms": metrics["stages"]["embedding"],
            },
        )

        # Stage 2: Build metadata filters for Qdrant
        stage_start = time.time()
        logger.debug("Stage 2: Building metadata filters")

        filters_dict = self._build_filters(sources, after, before, custom_filters)

        metrics["stages"]["filter_build"] = (time.time() - stage_start) * 1000
        logger.debug(
            "Metadata filters built",
            extra={"filters": filters_dict, "time_ms": metrics["stages"]["filter_build"]},
        )

        # Stage 3: Vector search in Qdrant
        stage_start = time.time()
        logger.debug(f"Stage 3: Vector search (top_k={top_k})")

        search_results = self.qdrant_client.search(
            query_vector=query_embedding,
            filters=filters_dict,
            limit=top_k,
        )

        metrics["stages"]["vector_search"] = (time.time() - stage_start) * 1000
        metrics["candidates_retrieved"] = len(search_results)
        logger.info(
            f"Vector search completed: {len(search_results)} candidates",
            extra={
                "candidates": len(search_results),
                "time_ms": metrics["stages"]["vector_search"],
            },
        )

        # Stage 4: Reranking (if enabled)
        if self.config.query.enable_reranking and search_results:
            stage_start = time.time()
            logger.debug(f"Stage 4: Reranking (top_n={top_n})")

            # Convert search results to NodeWithScore objects
            nodes = self._search_results_to_nodes(search_results)

            # Create query bundle
            query_bundle = QueryBundle(query_str=query_text)

            # Rerank nodes
            reranked_nodes = self.reranker._postprocess_nodes(nodes, query_bundle)

            # Convert back to results format
            results = self._nodes_to_results(reranked_nodes)

            metrics["stages"]["reranking"] = (time.time() - stage_start) * 1000
            metrics["results_after_reranking"] = len(results)
            logger.info(
                f"Reranking completed: {len(results)} results",
                extra={
                    "results": len(results),
                    "time_ms": metrics["stages"]["reranking"],
                },
            )
        else:
            # No reranking - convert search results directly
            results = [
                {
                    "doc_id": str(r["id"]),
                    "score": r["score"],
                    "title": r["payload"].get("title", ""),
                    "content": r["payload"].get("content", ""),
                    "source_type": r["payload"].get("source_type", ""),
                    "source_url": r["payload"].get("source_url", ""),
                    "timestamp": r["payload"].get("timestamp", ""),
                    "metadata": r["payload"].get("metadata", {}),
                }
                for r in search_results[:top_n]
            ]
            metrics["results_after_reranking"] = len(results)
            logger.debug("Reranking disabled, using top-n from vector search")

        # Stage 5: Graph traversal (if enabled and results exist)
        related_docs: list[dict[str, Any]] = []
        if self.config.query.enable_graph_traversal and results and self.graph_index:
            stage_start = time.time()
            logger.debug(
                f"Stage 5: Graph traversal (max_depth={self.config.query.max_graph_depth})"
            )

            try:
                # Traverse graph for each top result
                related_docs = self._traverse_graph_for_related_docs(
                    results, max_depth=self.config.query.max_graph_depth
                )

                metrics["stages"]["graph_traversal"] = (time.time() - stage_start) * 1000
                metrics["related_docs_found"] = len(related_docs)
                logger.info(
                    f"Graph traversal completed: {len(related_docs)} related documents",
                    extra={
                        "related_docs": len(related_docs),
                        "time_ms": metrics["stages"]["graph_traversal"],
                    },
                )
            except Exception as e:
                logger.error(
                    f"Graph traversal failed: {e}",
                    extra={"error": str(e), "error_type": type(e).__name__},
                )
                metrics["stages"]["graph_traversal"] = (time.time() - stage_start) * 1000
                metrics["graph_traversal_error"] = str(e)
        else:
            logger.debug("Graph traversal disabled or no results to traverse")

        # Calculate total time
        total_time = (time.time() - start_time) * 1000
        metrics["total_time_ms"] = total_time

        logger.info(
            f"Query completed in {total_time:.2f}ms",
            extra={
                "total_time_ms": total_time,
                "num_results": len(results),
                "num_related_docs": len(related_docs),
                "metrics": metrics,
            },
        )

        return {
            "query": query_text,
            "results": results,
            "related_docs": related_docs,
            "metrics": metrics,
        }

    def _build_filters(
        self,
        sources: list[str] | None,
        after: datetime | None,
        before: datetime | None,
        custom_filters: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Build Qdrant filter dictionary from query parameters.

        Args:
            sources: List of source types to filter by
            after: Filter documents created/updated after this datetime
            before: Filter documents created/updated before this datetime
            custom_filters: Custom metadata filters

        Returns:
            Filter dictionary for Qdrant, or None if no filters
        """
        filters: dict[str, Any] = {}

        # Source type filter (single or multiple)
        if sources:
            if len(sources) == 1:
                filters["source_type"] = sources[0]
            else:
                filters["source_types"] = sources

        # Date range filters
        if after:
            filters["date_from"] = after.isoformat()
        if before:
            filters["date_to"] = before.isoformat()

        # Merge custom filters
        if custom_filters:
            filters.update(custom_filters)

        return filters if filters else None

    def _search_results_to_nodes(self, search_results: list[dict[str, Any]]) -> list[NodeWithScore]:
        """Convert Qdrant search results to LlamaIndex NodeWithScore objects.

        Args:
            search_results: List of search results from Qdrant

        Returns:
            List of NodeWithScore objects for reranking
        """
        from llama_index.core.schema import TextNode

        nodes: list[NodeWithScore] = []
        for result in search_results:
            # Create TextNode from payload
            node = TextNode(
                text=result["payload"].get("content", ""),
                id_=str(result["id"]),
                metadata={
                    "doc_id": str(result["id"]),
                    "title": result["payload"].get("title", ""),
                    "source_type": result["payload"].get("source_type", ""),
                    "source_url": result["payload"].get("source_url", ""),
                    "timestamp": result["payload"].get("timestamp", ""),
                    **result["payload"].get("metadata", {}),
                },
            )

            # Wrap in NodeWithScore
            node_with_score = NodeWithScore(node=node, score=result["score"])
            nodes.append(node_with_score)

        return nodes

    def _nodes_to_results(self, nodes: list[NodeWithScore]) -> list[dict[str, Any]]:
        """Convert LlamaIndex NodeWithScore objects back to result dictionaries.

        Args:
            nodes: List of NodeWithScore objects from reranking

        Returns:
            List of result dictionaries
        """
        results: list[dict[str, Any]] = []
        for node_with_score in nodes:
            node = node_with_score.node
            metadata = node.metadata or {}

            # Keys to exclude from metadata dict
            excluded_keys = ["doc_id", "title", "source_type", "source_url", "timestamp"]

            result = {
                "doc_id": metadata.get("doc_id", node.id_),
                "score": node_with_score.score or 0.0,
                "title": metadata.get("title", ""),
                "content": node.get_content(),
                "source_type": metadata.get("source_type", ""),
                "source_url": metadata.get("source_url", ""),
                "timestamp": metadata.get("timestamp", ""),
                "metadata": {k: v for k, v in metadata.items() if k not in excluded_keys},
            }
            results.append(result)

        return results

    def _traverse_graph_for_related_docs(
        self, results: list[dict[str, Any]], max_depth: int = 2
    ) -> list[dict[str, Any]]:
        """Traverse Neo4j graph to find documents related to top results.

        For each top result, traverse the graph to find related documents through:
        - Direct references (REFERENCES, REPLIED_TO)
        - Shared entities (MENTIONS)
        - Shared authors (AUTHORED)

        Args:
            results: List of top query results
            max_depth: Maximum graph traversal depth (default: 2, max: 2 per gotchas)

        Returns:
            List of related documents with relevance scores
        """
        # Limit depth to max 2 hops (per gotchas)
        max_depth = min(max_depth, 2)

        related_docs_map: dict[str, dict[str, Any]] = {}

        # Traverse graph for top 3 results (to limit query time)
        for result in results[:3]:
            doc_id = result["doc_id"]

            try:
                # Find related documents via Neo4j
                related = self.neo4j_client.find_related_documents(
                    doc_id=doc_id, max_depth=max_depth, limit=10
                )

                # Add to map (deduplicate across multiple starting docs)
                for doc in related:
                    doc_id_key = doc["doc_id"]
                    if doc_id_key not in related_docs_map:
                        related_docs_map[doc_id_key] = doc
                    else:
                        # Increase relevance score if found from multiple paths
                        related_docs_map[doc_id_key]["relevance_score"] += doc.get(
                            "relevance_score", 1
                        )

            except Exception as e:
                logger.warning(
                    f"Failed to traverse graph for doc {doc_id}: {e}",
                    extra={"doc_id": doc_id, "error": str(e)},
                )
                continue

        # Convert to list and sort by relevance score
        related_docs = list(related_docs_map.values())
        related_docs.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Return top 10 most relevant
        return related_docs[:10]


# Export public API
__all__ = ["QueryEngine"]
