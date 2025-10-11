"""TEI Reranker integration for LlamaCrawl.

This module provides a custom reranker postprocessor that integrates with
HuggingFace Text Embeddings Inference (TEI) reranking endpoint. The reranker
uses cross-encoder models to re-score retrieved documents based on relevance
to the query, improving retrieval quality.
"""


from typing import Any

import httpx
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

from llamacrawl.utils.logging import get_logger
from llamacrawl.utils.retry import retry_with_backoff

logger = get_logger(__name__)


class TEIRerank(BaseNodePostprocessor):
    """HuggingFace TEI Reranker postprocessor for LlamaIndex.

    This postprocessor uses a TEI reranking endpoint to re-score retrieved
    documents based on their relevance to the query. It extends LlamaIndex's
    BaseNodePostprocessor to integrate seamlessly into query pipelines.

    The reranker uses cross-encoder models which are more accurate than
    bi-encoder embeddings for relevance scoring, providing 5-15% improvement
    in downstream task performance.

    Attributes:
        base_url: TEI reranker service URL (e.g., "http://localhost:8081")
        top_n: Number of top results to return after reranking
        timeout: Request timeout in seconds
        raw_scores: If False, returns normalized scores (0-1); if True, returns raw logits
    """

    base_url: str
    top_n: int = 5
    timeout: int = 60
    raw_scores: bool = False

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        top_n: int = 5,
        timeout: int = 60,
        raw_scores: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize TEI reranker.

        Args:
            base_url: TEI reranker service URL (default: "http://localhost:8081")
            top_n: Number of top results to return after reranking (default: 5)
            timeout: Request timeout in seconds (default: 60)
            raw_scores: Return raw logits vs normalized scores (default: False)
            **kwargs: Additional arguments passed to BaseNodePostprocessor
        """
        super().__init__(
            base_url=base_url,
            top_n=top_n,
            timeout=timeout,
            raw_scores=raw_scores,
            **kwargs
        )

    @classmethod
    def class_name(cls) -> str:
        """Return class name for serialization."""
        return "TEIRerank"

    @retry_with_backoff(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        exceptions=(httpx.HTTPError, httpx.TimeoutException, ConnectionError),
    )
    def _call_rerank_api(self, query: str, texts: list[str]) -> list[dict[str, float | int]]:
        """Call TEI rerank API with retry logic.

        Args:
            query: The query text
            texts: List of document texts to rerank

        Returns:
            List of dicts with 'index' and 'score' keys

        Raises:
            RuntimeError: If TEI rerank request fails after retries
            httpx.HTTPError: If HTTP error occurs
            httpx.TimeoutException: If request times out
        """
        url = f"{self.base_url.rstrip('/')}/rerank"
        headers = {"Content-Type": "application/json"}
        payload = {
            "query": query,
            "texts": texts,
            "raw_scores": self.raw_scores,
        }

        logger.debug(
            "Requesting reranking from TEI",
            extra={
                "url": url,
                "num_texts": len(texts),
                "query_length": len(query),
                "raw_scores": self.raw_scores,
            },
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                results: list[dict[str, float | int]] = response.json()

                logger.debug(
                    "Successfully received reranking from TEI",
                    extra={
                        "num_results": len(results),
                    },
                )

                return results

        except httpx.HTTPStatusError as e:
            logger.error(
                "TEI rerank request failed with HTTP error",
                extra={
                    "url": url,
                    "status_code": e.response.status_code,
                    "error": str(e),
                    "num_texts": len(texts),
                },
            )
            raise RuntimeError(f"TEI rerank request failed: HTTP {e.response.status_code}") from e

        except httpx.TimeoutException as e:
            logger.error(
                "TEI rerank request timed out",
                extra={
                    "url": url,
                    "timeout": self.timeout,
                    "num_texts": len(texts),
                },
            )
            raise RuntimeError(f"TEI rerank request timed out after {self.timeout}s") from e

        except httpx.HTTPError as e:
            logger.error(
                "TEI rerank request failed",
                extra={
                    "url": url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "num_texts": len(texts),
                },
            )
            raise RuntimeError(f"TEI rerank request failed: {str(e)}") from e

    def _postprocess_nodes(
        self,
        nodes: list[NodeWithScore],
        query_bundle: QueryBundle | None = None,
        top_n: int | None = None,
    ) -> list[NodeWithScore]:
        """Rerank nodes based on query relevance.

        This method implements the core reranking logic:
        1. Extract text content from nodes
        2. Call TEI rerank API with query and texts
        3. Sort results by score (highest first)
        4. Update node scores with reranker scores
        5. Return top-n nodes

        Args:
            nodes: List of nodes with scores from initial retrieval
            query_bundle: Query bundle containing the query text
            top_n: Optional override for top_n (defaults to self.top_n)

        Returns:
            List of reranked nodes (top-n by score)
        """
        # Use provided top_n or fall back to instance attribute
        effective_top_n = top_n if top_n is not None else self.top_n
        # Handle empty node list gracefully
        if not nodes:
            logger.warning("Reranking called with empty node list, returning empty list")
            return []

        # Handle missing query bundle
        if not query_bundle:
            logger.warning(
                "Reranking called without query bundle, returning original nodes (top-n)",
                extra={"num_nodes": len(nodes), "top_n": effective_top_n},
            )
            return nodes[: effective_top_n]

        # Extract query text
        query = query_bundle.query_str

        # Extract texts from nodes
        texts = [node.node.get_content() for node in nodes]

        logger.info(
            "Reranking nodes",
            extra={
                "num_candidates": len(nodes),
                "top_n": effective_top_n,
                "query_length": len(query),
            },
        )

        try:
            # Call TEI rerank API (with retry logic)
            results = self._call_rerank_api(query, texts)

            # Sort by score (highest first)
            results = sorted(results, key=lambda x: x["score"], reverse=True)

            # Log reranking scores for debugging
            if logger.isEnabledFor(10):  # DEBUG level
                for i, result in enumerate(results[: effective_top_n]):
                    logger.debug(
                        f"Reranked result {i+1}",
                        extra={
                            "rank": i + 1,
                            "score": result["score"],
                            "original_index": result["index"],
                        },
                    )

            # Create reranked nodes with updated scores
            reranked_nodes: list[NodeWithScore] = []
            for result in results[: effective_top_n]:
                idx: int = int(result["index"])
                node = nodes[idx]
                # Update score with reranker score
                node.score = float(result["score"])
                reranked_nodes.append(node)

            logger.info(
                "Reranking completed",
                extra={
                    "num_reranked": len(reranked_nodes),
                    "top_score": reranked_nodes[0].score if reranked_nodes else None,
                },
            )

            return reranked_nodes

        except Exception as e:
            # Fallback to original nodes on error
            logger.error(
                f"Reranking failed: {e}, falling back to original order",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "num_nodes": len(nodes),
                },
            )
            # Return top-n from original nodes
            return nodes[: effective_top_n]


# Export public API
__all__ = ["TEIRerank"]
