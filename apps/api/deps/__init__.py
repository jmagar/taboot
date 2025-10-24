"""Dependency injection helpers for the API layer."""

from __future__ import annotations

from .auth import get_redis_client, verify_api_key
from .extraction import (
    get_document_store,
    get_entity_pattern_matcher,
    get_extract_use_case,
    get_extraction_orchestrator,
    get_status_use_case,
    get_tier_c_llm_client,
    get_window_selector,
)

__all__ = [
    "get_document_store",
    "get_entity_pattern_matcher",
    "get_extract_use_case",
    "get_extraction_orchestrator",
    "get_redis_client",
    "get_status_use_case",
    "get_tier_c_llm_client",
    "get_window_selector",
    "verify_api_key",
]
