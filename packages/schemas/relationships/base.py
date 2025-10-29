"""Base relationship schema.

All relationship types must inherit from BaseRelationship.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class BaseRelationship(BaseModel):
    """Base class for all Neo4j relationships.

    Provides common temporal tracking and extraction metadata fields
    required on ALL relationships in the graph.

    Examples:
        >>> from datetime import datetime, UTC
        >>> rel = BaseRelationship(
        ...     created_at=datetime.now(UTC),
        ...     source="job_12345",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.confidence
        1.0
    """

    # Temporal tracking
    created_at: datetime = Field(
        ...,
        description="When we created this relationship in our system",
    )
    source_timestamp: datetime | None = Field(
        None,
        description="When the source content was created (if available from source)",
    )

    # Extraction metadata
    source: str = Field(
        ...,
        min_length=1,
        description="Ingestion job ID or reader type that created this relationship",
        examples=["job_12345", "github_reader", "docker_compose_reader"],
    )
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence (0.0-1.0, usually 1.0 for Tier A)",
    )
    extractor_version: str = Field(
        ...,
        min_length=1,
        description="Version of the extractor that created this relationship",
        examples=["1.0.0", "1.2.0"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "created_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-15T09:00:00Z",
                    "source": "job_12345",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
