"""GitHubLabel entity schema.

Represents a GitHub label used for categorizing issues and pull requests.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GitHubLabel(BaseModel):
    """GitHub label entity.

    Extracted from:
    - GitHub API label data
    - Issue and pull request labels
    - Repository label configuration

    Examples:
        >>> from datetime import datetime, UTC
        >>> label = GitHubLabel(
        ...     name="bug",
        ...     color="ff0000",
        ...     description="Something isn't working",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> label.name
        'bug'
    """

    # Identity fields
    repository_full_name: str = Field(
        ...,
        min_length=1,
        description="Full repository name this label belongs to (owner/name)",
        examples=["anthropics/claude-code"],
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Label name",
        examples=["bug", "enhancement", "documentation", "help wanted"],
    )
    color: str = Field(
        ...,
        min_length=1,
        description="Label color (hex code without #)",
        examples=["ff0000", "00ff00", "0000ff", "ffa500"],
    )

    # Description (optional)
    description: str | None = Field(
        None,
        description="Label description",
        examples=["Something isn't working", "New feature or request", "Improvements or additions to documentation"],
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
        examples=["github_api", "label_scraper"],
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
                    "repository_full_name": "anthropics/claude-code",
                    "name": "bug",
                    "color": "ff0000",
                    "description": "Something isn't working",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2023-06-01T00:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
