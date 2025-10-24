"""Prometheus metrics endpoint for Taboot API.

Exposes application metrics in Prometheus format for monitoring and alerting.
Includes HTTP request metrics, extraction metrics, vector search metrics, and LLM call metrics.

Per OBSERVABILITY.md requirements:
- Prometheus-style metric names and labels
- Job pipeline metrics (duration, failures, retries)
- Extraction tier metrics (windows/sec, tier hit ratios)
- Vector search latency
- LLM call duration
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import REGISTRY, Counter, Gauge, Histogram, generate_latest

router = APIRouter(tags=["observability"])

# HTTP request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

# Job pipeline metrics
jobs_inflight = Gauge(
    "jobs_inflight",
    "Number of jobs currently in flight",
    ["type"],
    registry=REGISTRY,
)

job_duration_seconds = Histogram(
    "job_duration_seconds",
    "Job duration in seconds",
    ["type"],
    buckets=[1, 2, 5, 10, 30, 60, 120, 300],
    registry=REGISTRY,
)

job_failures_total = Counter(
    "job_failures_total",
    "Total job failures",
    ["type", "code"],
    registry=REGISTRY,
)

retry_attempts_total = Counter(
    "retry_attempts_total",
    "Total retry attempts",
    ["type"],
    registry=REGISTRY,
)

# Extraction metrics
extraction_windows_processed_total = Counter(
    "extraction_windows_processed_total",
    "Total extraction windows processed",
    ["tier"],
    registry=REGISTRY,
)

extraction_tier_latency_seconds = Histogram(
    "extraction_tier_latency_seconds",
    "Extraction tier latency in seconds",
    ["tier"],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0],
    registry=REGISTRY,
)

cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache hits",
    registry=REGISTRY,
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total cache misses",
    registry=REGISTRY,
)

# Vector search metrics
vector_search_duration_seconds = Histogram(
    "vector_search_duration_seconds",
    "Vector search latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0],
    registry=REGISTRY,
)

qdrant_upserts_total = Counter(
    "qdrant_upserts_total",
    "Total Qdrant upserts",
    registry=REGISTRY,
)

qdrant_points_count = Gauge(
    "qdrant_points_count",
    "Number of points in Qdrant collection",
    registry=REGISTRY,
)

# LLM metrics
llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds",
    "LLM call duration in seconds",
    ["model"],
    buckets=[0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0, 10.0],
    registry=REGISTRY,
)

embedding_latency_seconds = Histogram(
    "embedding_latency_seconds",
    "Embedding latency in seconds",
    ["model"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
    registry=REGISTRY,
)

rerank_latency_seconds = Histogram(
    "rerank_latency_seconds",
    "Reranking latency in seconds",
    ["model"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY,
)

# Neo4j metrics
neo4j_tx_latency_seconds = Histogram(
    "neo4j_tx_latency_seconds",
    "Neo4j transaction latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY,
)

neo4j_deadlocks_total = Counter(
    "neo4j_deadlocks_total",
    "Total Neo4j deadlocks",
    registry=REGISTRY,
)

neo4j_nodes_count = Gauge(
    "neo4j_nodes_count",
    "Number of nodes in Neo4j",
    ["label"],
    registry=REGISTRY,
)

neo4j_rels_count = Gauge(
    "neo4j_rels_count",
    "Number of relationships in Neo4j",
    ["type"],
    registry=REGISTRY,
)


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Prometheus metrics endpoint.

    Returns metrics in Prometheus text exposition format.
    This endpoint is scraped by Prometheus for monitoring and alerting.

    Returns:
        Response: Prometheus metrics in text/plain format.

    Example:
        $ curl http://localhost:8000/metrics
        # HELP http_requests_total Total HTTP requests
        # TYPE http_requests_total counter
        http_requests_total{method="GET",path="/health",status="200"} 42.0
        ...
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# Export public API
__all__ = [
    "router",
    "http_requests_total",
    "http_request_duration_seconds",
    "jobs_inflight",
    "job_duration_seconds",
    "job_failures_total",
    "retry_attempts_total",
    "extraction_windows_processed_total",
    "extraction_tier_latency_seconds",
    "cache_hits_total",
    "cache_misses_total",
    "vector_search_duration_seconds",
    "qdrant_upserts_total",
    "qdrant_points_count",
    "llm_call_duration_seconds",
    "embedding_latency_seconds",
    "rerank_latency_seconds",
    "neo4j_tx_latency_seconds",
    "neo4j_deadlocks_total",
    "neo4j_nodes_count",
    "neo4j_rels_count",
]
