"""Milestone entity schema.

Represents a GitHub milestone for tracking progress toward a goal.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Milestone(BaseModel):
    """GitHub milestone entity.

    Extracted from:
    - GitHub API milestone data
    - Project milestones
    - Release planning

    Examples:
        >>> from datetime import datetime, UTC
        >>> milestone = Milestone(
        ...     number=1,
        ...     title="v1.0 Release",
        ...     state="open",
        ...     due_on=datetime(2024, 12, 31, 0, 0, 0, tzinfo=UTC),
        ...     description="First major release",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> milestone.title
        'v1.0 Release'
    """

    # Identity fields
    number: int = Field(
        ...,
        ge=1,
        description="Milestone number (unique within repository)",
        examples=[1, 2, 10],
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Milestone title",
        examples=["v1.0 Release", "Q1 2024", "Beta Launch"],
    )
    state: str = Field(
        ...,
        min_length=1,
        description="Milestone state (open, closed)",
        examples=["open", "closed"],
    )

    # Due date (optional)
    due_on: datetime | None = Field(
        None,
        description="Milestone due date",
    )

    # Description (optional)
    description: str | None = Field(
        None,
        description="Milestone description",
        examples=["First major release", "All Q1 deliverables", "Beta feature set"],
    )

    # Temporal tracking (required on ALL entities)
    created_at: datetime = Field(
        ...,
        description="When we created this node in our system",
    )
    updated_at: datetime = Field(
        ...,
        description="When we last modified this node",
    )
    source_timestamp: datetime | None = Field(
        None,
        description="When the source content was created (if available from source)",
    )

    # Extraction metadata (required on ALL entities)
    extraction_tier: Literal["A", "B", "C"] = Field(
        ...,
        description="Extraction tier: A (deterministic), B (spaCy), C (LLM)",
    )
    extraction_method: str = Field(
        ...,
        description="Method used for extraction",
        examples=["github_api", "milestone_scraper"],
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Extraction confidence (0.0-1.0, usually 1.0 for Tier A)",
    )
    extractor_version: str = Field(
        ...,
        description="Version of the extractor that created this entity",
        examples=["1.0.0", "1.2.0"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "number": 1,
                    "title": "v1.0 Release",
                    "state": "open",
                    "due_on": "2024-12-31T00:00:00Z",
                    "description": "First major release",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-01T00:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
