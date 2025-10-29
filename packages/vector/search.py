"""Qdrant vector search with metadata filtering."""

from datetime import datetime
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Condition,
    FieldCondition,
    Filter,
    MatchAny,
    Range,
    SearchParams,
)


class VectorSearch:
    """Vector search with metadata filters for source types and dates."""

    def __init__(self, qdrant_url: str, collection_name: str):
        """
        Initialize vector search client.

        Args:
            qdrant_url: Qdrant server URL
            collection_name: Name of the collection to search
        """
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.client = QdrantClient(url=qdrant_url, prefer_grpc=False)

    def build_metadata_filter(
        self, source_types: list[str] | None = None, after: datetime | None = None
    ) -> Filter | None:
        """
        Build Qdrant filter for metadata constraints.

        Args:
            source_types: Filter by source types (e.g., ['web', 'docker_compose'])
            after: Filter by ingestion date (after this timestamp)

        Returns:
            Qdrant Filter object or None if no filters
        """
        conditions: list[Condition] = []

        if source_types:
            conditions.append(FieldCondition(key="source_type", match=MatchAny(any=source_types)))

        if after:
            timestamp = int(after.timestamp())
            conditions.append(FieldCondition(key="ingested_at", range=Range(gte=timestamp)))

        if not conditions:
            return None

        return Filter(must=conditions)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 20,
        source_types: list[str] | None = None,
        after: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform vector search with optional metadata filters.

        Args:
            query_embedding: Query vector (1024-dim)
            top_k: Number of results to return
            source_types: Filter by source types
            after: Filter by ingestion date

        Returns:
            List of search results with payloads and scores
        """
        metadata_filter = self.build_metadata_filter(source_types=source_types, after=after)

        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=metadata_filter,
            limit=top_k,
            search_params=SearchParams(hnsw_ef=128),
        )

        results = []
        for hit in search_results:
            payload = hit.payload or {}
            results.append(
                {
                    "chunk_id": str(hit.id),
                    "score": hit.score,
                    "content": payload.get("content", ""),
                    "doc_id": payload.get("doc_id"),
                    "source_url": payload.get("source_url"),
                    "section": payload.get("section"),
                    "metadata": payload,
                }
            )

        return results
