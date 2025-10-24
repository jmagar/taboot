"""API documents endpoint implementation (T168).

Implements GET /documents with filtering and pagination.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.deps import get_document_store
from apps.api.schemas import ResponseEnvelope
from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.core.use_cases.list_documents import DocumentListResponse
from packages.schemas.models import ExtractionState, SourceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=ResponseEnvelope[DocumentListResponse])
def list_documents(
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum documents to return"),
    ] = 10,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of documents to skip (pagination)"),
    ] = 0,
    source_type: Annotated[
        str | None,
        Query(
            description="Filter by source type (web, github, etc.)",
        ),
    ] = None,
    extraction_state: Annotated[
        str | None,
        Query(
            description="Filter by extraction state (pending, completed, etc.)",
        ),
    ] = None,
    *,
    document_store: Annotated[PostgresDocumentStore, Depends(get_document_store)],
) -> ResponseEnvelope[DocumentListResponse]:
    """List ingested documents with optional filters and pagination.

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
        source_type_enum: SourceType | None = None
        if source_type:
            try:
                source_type_enum = SourceType(source_type)
            except ValueError:
                valid_values = [s.value for s in SourceType]
                logger.warning(
                    "Invalid source_type provided",
                    extra={"source_type": source_type, "valid_values": valid_values},
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid source_type '{source_type}'. "
                    f"Valid values: {', '.join(valid_values)}",
                ) from None

        extraction_state_enum: ExtractionState | None = None
        if extraction_state:
            try:
                extraction_state_enum = ExtractionState(extraction_state)
            except ValueError:
                valid_values = [e.value for e in ExtractionState]
                logger.warning(
                    "Invalid extraction_state provided",
                    extra={
                        "extraction_state": extraction_state,
                        "valid_values": valid_values,
                    },
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid extraction_state '{extraction_state}'. "
                    f"Valid values: {', '.join(valid_values)}",
                ) from None

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

        logger.info(
            "Listed %d documents (total=%d, limit=%d, offset=%d)",
            len(result.documents),
            result.total,
            limit,
            offset,
        )

        return ResponseEnvelope(data=result, error=None)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.exception("Validation error in list documents")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("List documents failed")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {e!s}") from e
