"""Inference helpers for the reranker FastAPI service."""

from __future__ import annotations

from collections.abc import Sequence

import torch
from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    """Thin wrapper around a sentence-transformers CrossEncoder."""

    def __init__(self, model_id: str, *, device: str = "auto", batch_size: int = 16) -> None:
        self.model_id = model_id
        self.batch_size = batch_size
        self.device = self._resolve_device(device)
        self._encoder = CrossEncoder(self.model_id, device=self.device)
        self._ensure_padding_token()

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device.lower() == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        """Compute cross-encoder scores for the given documents."""

        if not documents:
            return []

        pairs = [[query, doc] for doc in documents]
        scores = self._encoder.predict(pairs, batch_size=self.batch_size, convert_to_numpy=True)
        return [float(score) for score in scores]

    def _ensure_padding_token(self) -> None:
        """Configure tokenizer padding to support batched inference."""

        tokenizer = getattr(self._encoder, "tokenizer", None)
        if tokenizer is None:
            return

        pad_source = getattr(tokenizer, "pad_token", None)
        if pad_source is None:
            pad_source = getattr(tokenizer, "eos_token", None)
        if pad_source is None:
            pad_source = getattr(tokenizer, "bos_token", None)
        if pad_source is not None:
            tokenizer.pad_token = pad_source

        if tokenizer.pad_token_id is None:
            tokenizer.add_special_tokens({"pad_token": "[PAD]"})
            self._encoder.model.resize_token_embeddings(len(tokenizer))

        tokenizer.padding_side = "right"

        model_config = getattr(self._encoder.model, "config", None)
        if model_config is not None:
            if tokenizer.pad_token_id is not None:
                model_config.pad_token_id = tokenizer.pad_token_id
            if tokenizer.pad_token is not None:
                model_config.pad_token = tokenizer.pad_token

    def close(self) -> None:
        """Release encoder resources."""

        encoder = getattr(self, "_encoder", None)
        if encoder is None:
            return

        # torch.nn.Module implements __del__, but explicitly dereferencing helps with VRAM reuse.
        if hasattr(encoder, "model"):
            encoder.model.to("cpu")
        del self._encoder
