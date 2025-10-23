"""Tests for reranking with Qwen3-Reranker-0.6B."""

import pytest
from packages.vector.reranker import Reranker


@pytest.mark.unit
def test_reranker_init():
    """Test Reranker initialization."""
    reranker = Reranker(
        model_name="Qwen/Qwen3-Reranker-0.6B",
        device="cpu",
        batch_size=16
    )

    assert reranker.model_name == "Qwen/Qwen3-Reranker-0.6B"
    assert reranker.device == "cpu"
    assert reranker.batch_size == 16


@pytest.mark.unit
def test_reranker_scores_passages():
    """Test reranker scores query-passage pairs."""
    reranker = Reranker(
        model_name="Qwen/Qwen3-Reranker-0.6B",
        device="cpu",
        batch_size=4
    )

    query = "Which services expose port 8080?"
    passages = [
        "The API service exposes port 8080 with JWT authentication.",
        "Redis runs on port 6379.",
        "The web frontend serves static content on port 8080."
    ]

    scores = reranker.rerank(query=query, passages=passages, top_n=2)

    assert len(scores) == 2
    assert all(isinstance(score, float) for score in scores)
    assert all(0.0 <= score <= 1.0 for score in scores)


@pytest.mark.integration
@pytest.mark.slow
def test_reranker_with_gpu(skip_if_no_gpu):
    """Test reranker on GPU if available."""
    reranker = Reranker(
        model_name="Qwen/Qwen3-Reranker-0.6B",
        device="auto",
        batch_size=16
    )

    query = "docker compose services"
    passages = [
        "Docker Compose defines multi-container applications.",
        "PostgreSQL is a relational database.",
        "The compose file specifies service dependencies."
    ]

    scores = reranker.rerank(query=query, passages=passages, top_n=3)
    assert len(scores) == 3
