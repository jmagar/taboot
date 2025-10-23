"""API documents endpoint implementation (T168).

Implements GET /documents with filtering and pagination.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from packages.core.use_cases.list_documents import DocumentListResponse, ListDocumentsUseCase
from packages.schemas.models import Document, ExtractionState, SourceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def list_documents(
    limit: int = Query(default=10, ge=1, le=100, description="Maximum documents to return"),
    offset: int = Query(default=0, ge=0, description="Number of documents to skip (pagination)"),
    source_type: Optional[str] = Query(
        default=None, description="Filter by source type (web, github, etc.)"
    ),
    extraction_state: Optional[str] = Query(
        default=None, description="Filter by extraction state (pending, completed, etc.)"
    ),
) -> DocumentListResponse:
    """
    List ingested documents with optional filters and pagination.

    Query parameters:
        - limit: Maximum documents to return (1-100, default: 10)
        - offset: Number of documents to skip for pagination (default: 0)
        - source_type: Filter by source type (web, github, reddit, youtube, gmail,
                      elasticsearch, docker_compose, swag, tailscale, unifi, ai_session)
        - extraction_state: Filter by extraction state (pending, tier_a_done,
                           tier_b_done, tier_c_done, completed, failed)

    Returns:
        DocumentListResponse with documents array, total count, limit, and offset

    Raises:
        HTTPException 400: Invalid filter values
        HTTPException 500: Database or internal errors
    """
    try:
        # Parse and validate filters
        source_type_enum: Optional[SourceType] = None
        if source_type:
            try:
                source_type_enum = SourceType(source_type)
            except ValueError:
                valid_values = [s.value for s in SourceType]
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid source_type '{source_type}'. "
                    f"Valid values: {', '.join(valid_values)}",
                ) from None

        extraction_state_enum: Optional[ExtractionState] = None
        if extraction_state:
            try:
                extraction_state_enum = ExtractionState(extraction_state)
            except ValueError:
                valid_values = [e.value for e in ExtractionState]
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid extraction_state '{extraction_state}'. "
                    f"Valid values: {', '.join(valid_values)}",
                ) from None

        # Import database client and document store
        from packages.common.db_schema import get_postgres_client
        from packages.common.postgres_document_store import PostgresDocumentStore

        # Get PostgreSQL connection
        conn = get_postgres_client()

        try:
            # Create document store with PostgreSQL connection
            document_store = PostgresDocumentStore(conn)

            # Query documents with filters
            documents = document_store.query_documents(
                limit=limit,
                offset=offset,
                source_type=source_type_enum,
                extraction_state=extraction_state_enum,
            )

            # Get total count for pagination
            total = document_store.count_documents(
                source_type=source_type_enum,
                extraction_state=extraction_state_enum,
            )

            result = DocumentListResponse(
                documents=documents,
                total=total,
                limit=limit,
                offset=offset,
            )
        finally:
            conn.close()

        logger.info(
            "Listed %d documents (total=%d, limit=%d, offset=%d)",
            len(result.documents), result.total, limit, offset
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.exception("Validation error in list documents: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("List documents failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {e!s}") from e

    return result
