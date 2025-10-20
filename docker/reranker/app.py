import os
from functools import lru_cache
from typing import List

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import CrossEncoder


class RerankRequest(BaseModel):
    query: str = Field(..., description="User query text.")
    documents: List[str] = Field(
        ..., description="Candidate documents ordered arbitrarily."
    )


class RerankResponse(BaseModel):
    scores: List[float] = Field(
        ..., description="Score per document (aligned with input order)."
    )
    ranking: List[int] = Field(
        ...,
        description="Indices into the input list sorted from highest to lowest score.",
    )


def _resolve_device(preferred: str) -> str:
    if preferred == "cuda" and torch.cuda.is_available():
        return "cuda"
    if preferred == "cpu":
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=1)
def load_model() -> CrossEncoder:
    model_id = os.getenv("MODEL_ID", "Qwen/Qwen3-Reranker-0.6B")
    preferred_device = os.getenv("RERANKER_DEVICE", "auto").lower()
    device = _resolve_device("cuda" if preferred_device == "auto" else preferred_device)
    max_length = int(os.getenv("MAX_LENGTH", "512"))
    model = CrossEncoder(
        model_id,
        device=device,
        max_length=max_length,
        default_activation_function=None,
    )
    return model


app = FastAPI(title="Qwen3 Reranker Service", version="0.1.0")


@app.get("/healthz")
def health() -> dict[str, str]:
    try:
        load_model()
    except Exception as exc:  # pragma: no cover - defensive logging
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok"}


@app.post("/rerank", response_model=RerankResponse)
def rerank(request: RerankRequest) -> RerankResponse:
    if not request.documents:
        raise HTTPException(status_code=400, detail="documents must not be empty")

    model = load_model()
    pairs = [[request.query, doc] for doc in request.documents]
    batch_size = int(os.getenv("BATCH_SIZE", "16"))
    with torch.inference_mode():
        scores = model.predict(pairs, batch_size=batch_size)
    scores_list = scores.tolist() if isinstance(scores, torch.Tensor) else list(scores)
    ranking = sorted(range(len(scores_list)), key=lambda idx: scores_list[idx], reverse=True)
    return RerankResponse(scores=scores_list, ranking=ranking)

