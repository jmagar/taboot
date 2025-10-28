"""HTTP client for the dedicated reranker microservice."""

from __future__ import annotations

import logging
from typing import Sequence

import httpx

logger = logging.getLogger(__name__)


class Reranker:
    """Client for the Qwen3 reranker microservice."""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Reranker-0.6B",
        device: str = "auto",
        batch_size: int = 16,
        *,
        base_url: str = "http://taboot-rerank:8000",
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize the reranker client.

        Args:
            model_name: Logical model identifier (for logging/telemetry).
            device: Requested device (kept for compatibility; forwarded via logs).
            batch_size: Batch size hint (forwarded to service when relevant).
            base_url: Base URL of the reranker service.
            timeout: Request timeout in seconds.
            client: Optional pre-configured httpx.Client (primarily for tests).
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._client = client or httpx.Client(timeout=self.timeout)
        self._owns_client = client is None

    def _post_rerank(self, query: str, passages: Sequence[str]) -> tuple[list[float], list[int]]:
        """Send rerank request to the microservice and parse response."""
        if not passages:
            return [], []

        payload = {"query": query, "documents": list(passages)}
        try:
            response = self._client.post(
                f"{self.base_url}/rerank",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network errors
            logger.exception("Reranker request failed: %s", exc)
            raise RuntimeError(f"Reranker request failed: {exc}") from exc

        data = response.json()

        scores_raw = data.get("scores", [])
        ranking_raw = data.get("ranking", [])

        if not isinstance(scores_raw, list) or not isinstance(ranking_raw, list):
            raise RuntimeError("Reranker returned invalid payload")

        try:
            scores = [float(score) for score in scores_raw]
            ranking = [int(idx) for idx in ranking_raw]
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Reranker returned non-numeric payload") from exc

        return scores, ranking

    def rerank(self, query: str, passages: list[str], top_n: int = 5) -> list[float]:
        """Return top-n scores for passages."""
        scores, ranking = self._post_rerank(query, passages)

        if not scores or not ranking:
            return []

        top_indices = ranking[:top_n]
        return [scores[idx] for idx in top_indices if 0 <= idx < len(scores)]

    def rerank_with_indices(
        self, query: str, passages: list[str], top_n: int = 5
    ) -> list[tuple[int, float]]:
        """Return (index, score) tuples sorted by relevance."""
        scores, ranking = self._post_rerank(query, passages)

        if not scores or not ranking:
            return []

        scored = [(idx, scores[idx]) for idx in ranking if 0 <= idx < len(scores)]
        return scored[:top_n]

    def close(self) -> None:
        """Close the underlying HTTP client if owned."""
        if self._owns_client:
            self._client.close()

    def __del__(self) -> None:  # pragma: no cover - best-effort cleanup
        try:
            self.close()
        except Exception:
            pass
