"""API query endpoint implementation."""

import os
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from packages.core.use_cases.query import execute_query


router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Query request schema."""

    question: str = Field(..., min_length=1, description="Question to answer")
    top_k: int = Field(default=20, ge=1, le=100, description="Number of candidates from vector search")
    rerank_top_n: int = Field(default=5, ge=1, le=20, description="Number of chunks after reranking")
    source_types: Optional[List[str]] = Field(default=None, description="Filter by source types")
    after: Optional[datetime] = Field(default=None, description="Filter by ingestion date")


class QueryResponse(BaseModel):
    """Query response schema."""

    answer: str
    sources: List[tuple[str, str]]
    latency_ms: int
    latency_breakdown: dict
    vector_count: int
    graph_count: int


@router.post("", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest) -> QueryResponse:
    """
    Execute natural language query with hybrid retrieval.

    Args:
        request: Query request with question and filters

    Returns:
        Query response with answer, sources, and latency

    Raises:
        HTTPException: If query fails
    """
    from packages.common.config import get_config

    config = get_config()

    try:
        result = execute_query(
            query=request.question,
            qdrant_url=config.qdrant_url,
            qdrant_collection=config.collection_name,
            neo4j_uri=config.neo4j_uri,
            neo4j_username=config.neo4j_user,
            neo4j_password=config.neo4j_password,
            ollama_base_url=f"http://localhost:{config.ollama_port}",
            top_k=request.top_k,
            rerank_top_n=request.rerank_top_n,
            source_types=request.source_types,
            after=request.after
        )

        if not result:
            raise HTTPException(status_code=500, detail="Query execution failed")

        return QueryResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
