"""FastAPI application exposing the reranker cross-encoder."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from anyio import to_thread
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.rerank import __version__
from apps.rerank.config import RerankConfig, load_config
from apps.rerank.service import CrossEncoderReranker

logger = logging.getLogger(__name__)


class RerankRequest(BaseModel):
    """Request payload for reranking documents."""

    query: str = Field(..., description="Natural language query to score against documents.")
    documents: list[str] = Field(default_factory=list, description="Candidate passages to rerank.")
    top_n: int | None = Field(
        default=None,
        ge=1,
        description="Optional limit on the number of ranked indices to return.",
    )


class RerankResponse(BaseModel):
    """Response payload containing scores and ranking indices."""

    scores: list[float]
    ranking: list[int]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load and tear down the cross-encoder model."""

    config = load_config()
    logger.info(
        "Loading reranker model %s (device=%s, batch_size=%s)",
        config.model_id,
        config.device,
        config.batch_size,
    )

    reranker = await to_thread.run_sync(
        lambda: CrossEncoderReranker(
            config.model_id,
            device=config.device,
            batch_size=config.batch_size,
        )
    )

    app.state.config = config
    app.state.reranker = reranker

    try:
        yield
    finally:
        logger.info("Shutting down reranker model %s", config.model_id)
        reranker.close()


app = FastAPI(title="Taboot Reranker", version=__version__, lifespan=lifespan)


@app.get("/healthz", tags=["health"])
async def health(request: Request) -> dict[str, Any]:
    """Basic health probe with model metadata."""

    config: RerankConfig = request.app.state.config
    reranker: CrossEncoderReranker = request.app.state.reranker
    return {
        "status": "ok",
        "model": config.model_id,
        "device": reranker.device,
        "batch_size": config.batch_size,
    }


@app.post("/rerank", response_model=RerankResponse, tags=["rerank"])
async def rerank(payload: RerankRequest, request: Request) -> RerankResponse:
    """Return scores and ranked indices for the supplied documents."""

    reranker: CrossEncoderReranker = request.app.state.reranker

    try:
        scores = await to_thread.run_sync(reranker.score, payload.query, payload.documents)
    except Exception as exc:  # pragma: no cover - inference failures are runtime issues
        logger.exception("Reranker inference failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference failed",
        ) from exc

    ranking = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)

    if payload.top_n is not None:
        ranking = ranking[: payload.top_n]

    return RerankResponse(scores=scores, ranking=ranking)
