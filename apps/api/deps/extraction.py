"""Extraction-related dependency providers for the API layer."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

from apps.api.deps.auth import get_redis_client
from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.common.config import get_config
from packages.common.db_schema import get_postgres_client
from packages.common.health import check_system_health
from packages.core.use_cases.extract_pending import ExtractPendingUseCase
from packages.core.use_cases.get_status import GetStatusUseCase
from packages.extraction.orchestrator import ExtractionOrchestrator
from packages.extraction.tier_a import parsers
from packages.extraction.tier_a.patterns import EntityPatternMatcher
from packages.extraction.tier_b.window_selector import WindowSelector
from packages.extraction.tier_c.llm_client import TierCLLMClient

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _entity_pattern_matcher() -> EntityPatternMatcher:
    """Cached EntityPatternMatcher instance for Tier A processing."""
    logger.debug("Initializing EntityPatternMatcher singleton")
    return EntityPatternMatcher()


@lru_cache(maxsize=1)
def _window_selector() -> WindowSelector:
    """Cached window selector for Tier B processing."""
    logger.debug("Initializing WindowSelector singleton")
    return WindowSelector()


def get_entity_pattern_matcher() -> EntityPatternMatcher:
    """Return shared EntityPatternMatcher instance."""
    return _entity_pattern_matcher()


def get_window_selector() -> WindowSelector:
    """Return shared WindowSelector instance."""
    return _window_selector()


def get_tier_c_llm_client(
    request: Request,
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> TierCLLMClient:
    """Provide a cached Tier C LLM client bound to the FastAPI application."""
    client: TierCLLMClient | None = getattr(request.app.state, "tier_c_llm_client", None)
    if client is None:
        config = get_config()
        client = TierCLLMClient(
            model="qwen3:4b",
            redis_client=redis_client,
            batch_size=config.tier_c_batch_size,
            temperature=0.0,
        )
        request.app.state.tier_c_llm_client = client
        logger.info("Initialized TierCLLMClient for extraction pipeline")
    return client


def get_extraction_orchestrator(
    request: Request,
    redis_client: Annotated[Redis, Depends(get_redis_client)],
    llm_client: Annotated[TierCLLMClient, Depends(get_tier_c_llm_client)],
    entity_pattern_matcher: Annotated[EntityPatternMatcher, Depends(get_entity_pattern_matcher)],
    window_selector: Annotated[WindowSelector, Depends(get_window_selector)],
) -> ExtractionOrchestrator:
    """Provide an application-scoped ExtractionOrchestrator."""
    orchestrator: ExtractionOrchestrator | None = getattr(
        request.app.state, "extraction_orchestrator", None
    )
    if orchestrator is None:
        orchestrator = ExtractionOrchestrator(
            tier_a_parser=parsers,
            tier_a_patterns=entity_pattern_matcher,
            window_selector=window_selector,
            llm_client=llm_client,
            redis_client=redis_client,
        )
        request.app.state.extraction_orchestrator = orchestrator
        logger.info("Initialized ExtractionOrchestrator singleton")
    return orchestrator


def get_document_store() -> Iterator[PostgresDocumentStore]:
    """Yield a PostgreSQL-backed document store for request-scoped operations."""
    conn = get_postgres_client()
    store = PostgresDocumentStore(conn)
    try:
        yield store
    finally:
        conn.close()


def get_extract_use_case(
    orchestrator: Annotated[ExtractionOrchestrator, Depends(get_extraction_orchestrator)],
    document_store: Annotated[PostgresDocumentStore, Depends(get_document_store)],
) -> ExtractPendingUseCase:
    """Construct the extract pending use case with injected dependencies."""
    return ExtractPendingUseCase(
        orchestrator=orchestrator,
        document_store=document_store,
    )


def get_status_use_case(
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> GetStatusUseCase:
    """Construct the status use case with shared Redis client."""
    return GetStatusUseCase(
        redis_client=redis_client,
        health_checker=check_system_health,
    )


__all__ = [
    "get_document_store",
    "get_entity_pattern_matcher",
    "get_extract_use_case",
    "get_extraction_orchestrator",
    "get_status_use_case",
    "get_tier_c_llm_client",
    "get_window_selector",
]
