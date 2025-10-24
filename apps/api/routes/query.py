"""API query endpoint implementation."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from apps.api.deps.auth import verify_api_key
from packages.core.use_cases.query import execute_query

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Query request schema."""

    question: str = Field(..., min_length=1, description="Question to answer")
    top_k: int = Field(
        default=20, ge=1, le=100, description="Number of candidates from vector search"
    )
    rerank_top_n: int = Field(
        default=5, ge=1, le=20, description="Number of chunks after reranking"
    )
    source_types: list[str] | None = Field(
        default=None, description="Filter by source types"
    )
    after: datetime | None = Field(default=None, description="Filter by ingestion date")


class QueryResponse(BaseModel):
    """Query response schema."""

    answer: str
    sources: list[tuple[str, str]]
    latency_ms: int
    latency_breakdown: dict[str, int]
    vector_count: int
    graph_count: int


@router.post("", response_model=QueryResponse, dependencies=[Depends(verify_api_key)])
async def query_knowledge_base(request: QueryRequest) -> QueryResponse:
    """Execute natural language query with hybrid retrieval.

    Args:
        request: Query request with question and filters

    Returns:
        Query response with answer, sources, and latency

    Raises:
        HTTPException: If query fails
    """
    from packages.common.config import get_config

    config = get_config()

    logger.info(
        "Query execution started",
        extra={
            "question_length": len(request.question),
            "top_k": request.top_k,
            "rerank_top_n": request.rerank_top_n,
        },
    )

    try:
        # Use configured Ollama URL if available, otherwise construct from host and port
        ollama_url = getattr(
            config,
            "ollama_url",
            f"http://localhost:{config.ollama_port}",
        )

        result = execute_query(
            query=request.question,
            qdrant_url=config.qdrant_url,
            qdrant_collection=config.collection_name,
            neo4j_uri=config.neo4j_uri,
            neo4j_username=config.neo4j_user,
            neo4j_password=config.neo4j_password,
            ollama_base_url=ollama_url,
            top_k=request.top_k,
            rerank_top_n=request.rerank_top_n,
            source_types=request.source_types,
            after=request.after,
        )

        if not result:
            logger.error("Query execution returned empty result")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Query execution failed",
            )

        logger.info(
            "Query execution completed",
            extra={"result_sources": len(result.get("sources", []))},
        )

        return QueryResponse(**result)

    except ValueError as e:
        logger.warning("Query validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Query execution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {e!s}",
        ) from e
