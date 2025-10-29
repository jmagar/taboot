"""Environment configuration helpers for the reranker service."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RerankConfig:
    """Runtime configuration for the reranker service."""

    model_id: str
    batch_size: int
    device: str


def _int_from_env(*keys: str, default: int) -> int:
    """Read the first available environment variable and coerce to int."""

    for key in keys:
        value = os.getenv(key)
        if value is None:
            continue
        try:
            return int(value)
        except ValueError:
            logger.warning("Invalid integer for %s=%s; using default %s", key, value, default)
            break
    return default


def _str_from_env(*keys: str, default: str) -> str:
    """Read the first available environment variable as string."""

    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default


def load_config() -> RerankConfig:
    """Load reranker configuration from the environment."""

    model_id = _str_from_env("MODEL_ID", "RERANKER_MODEL", default="Qwen/Qwen3-Reranker-0.6B")
    batch_size = _int_from_env("BATCH_SIZE", "RERANKER_BATCH_SIZE", default=16)
    device = _str_from_env("DEVICE", "RERANKER_DEVICE", default="auto")
    return RerankConfig(model_id=model_id, batch_size=batch_size, device=device)
