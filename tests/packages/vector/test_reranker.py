"""Unit tests for the HTTP-based reranker client."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from packages.vector.reranker import Reranker


def _build_mock_client(response_payload: dict[str, Any]) -> httpx.Client:
    """Create an httpx client backed by a mock transport for tests."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert "query" in body
        assert isinstance(body.get("documents"), list)
        return httpx.Response(200, json=response_payload)

    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


@pytest.mark.unit
def test_reranker_init_stores_metadata() -> None:
    """Ensure constructor preserves configuration attributes."""
    client = _build_mock_client({"scores": [], "ranking": []})
    reranker = Reranker(
        model_name="Qwen/Qwen3-Reranker-0.6B",
        device="cpu",
        batch_size=32,
        base_url="http://mock-service",
        client=client,
    )

    assert reranker.model_name == "Qwen/Qwen3-Reranker-0.6B"
    assert reranker.device == "cpu"
    assert reranker.batch_size == 32

    client.close()


@pytest.mark.unit
def test_reranker_returns_top_scores() -> None:
    """Client returns scores ordered by ranking from service."""
    payload = {"scores": [0.9, 0.1, 0.6], "ranking": [0, 2, 1]}
    client = _build_mock_client(payload)
    reranker = Reranker(client=client, base_url="http://mock")

    query = "Which services expose port 8080?"
    passages = [
        "The API service exposes port 8080 with JWT authentication.",
        "Redis runs on port 6379.",
        "The web frontend serves static content on port 8080.",
    ]

    scores = reranker.rerank(query=query, passages=passages, top_n=2)
    assert scores == [0.9, 0.6]

    client.close()


@pytest.mark.unit
def test_reranker_returns_indices_with_scores() -> None:
    """Client surfaces index-score tuples respecting service ranking."""
    payload = {"scores": [0.2, 0.5, 0.9], "ranking": [2, 1, 0]}
    client = _build_mock_client(payload)
    reranker = Reranker(client=client, base_url="http://mock")

    results = reranker.rerank_with_indices(query="q", passages=["a", "b", "c"], top_n=2)
    assert results == [(2, 0.9), (1, 0.5)]

    client.close()
