"""Issue entity schema.

Represents a GitHub issue with metadata, state, and comment tracking.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Issue(BaseModel):
    """GitHub issue entity.

    Extracted from:
    - GitHub API issue data
    - Issue tracking systems
    - Project management tools

    Examples:
        >>> from datetime import datetime, UTC
        >>> issue = Issue(
        ...     number=42,
        ...     title="Fix bug in parser",
        ...     state="open",
        ...     body="The parser fails on edge case X",
        ...     author_login="johndoe",
        ...     comments_count=5,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> issue.number
        42
    """

    # Identity fields
    number: int = Field(
        ...,
        ge=1,
        description="Issue number (unique within repository)",
        examples=[42, 123, 1000],
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Issue title",
        examples=["Fix bug in parser", "Add new feature", "Update documentation"],
    )
    state: str = Field(
        ...,
        min_length=1,
        description="Issue state (open, closed, etc.)",
        examples=["open", "closed"],
    )

    # Content fields (optional)
    body: str | None = Field(
        None,
        description="Issue body/description",
        examples=["The parser fails on edge case X", "We need to add support for Y"],
    )

    # Author information
    author_login: str = Field(
        ...,
        min_length=1,
        description="GitHub username of issue author",
        examples=["johndoe", "jane-smith"],
    )

    # Temporal information (optional)
    closed_at: datetime | None = Field(
        None,
        description="When the issue was closed (if closed)",
    )

    # Statistics (optional)
    comments_count: int | None = Field(
        None,
        ge=0,
        description="Number of comments on the issue",
        examples=[0, 5, 50],
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
        examples=["github_api", "issue_scraper"],
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
                    "number": 42,
                    "title": "Fix bug in parser",
                    "state": "open",
                    "body": "The parser fails on edge case X",
                    "author_login": "johndoe",
                    "closed_at": None,
                    "comments_count": 5,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-10T08:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
