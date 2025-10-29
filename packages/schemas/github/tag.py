"""Tag entity schema.

Represents a Git tag with optional annotation message and tagger information.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Tag(BaseModel):
    """Git tag entity.

    Extracted from:
    - GitHub API tag data
    - Git tags
    - Release tags

    Examples:
        >>> from datetime import datetime, UTC
        >>> tag = Tag(
        ...     name="v1.0.0",
        ...     sha="abc123def456",
        ...     ref="refs/tags/v1.0.0",
        ...     message="Release version 1.0.0",
        ...     tagger="johndoe",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> tag.name
        'v1.0.0'
    """

    # Identity fields
    repository_full_name: str = Field(
        ...,
        min_length=1,
        description="Full repository name this tag belongs to (owner/name)",
        examples=["anthropics/claude-code"],
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Tag name (often a version)",
        examples=["v1.0.0", "v2.1.3", "release-2024-01"],
    )

    # Git metadata
    sha: str = Field(
        ...,
        min_length=1,
        description="Commit SHA that the tag points to",
        examples=["abc123def456", "1234567890abcdef"],
    )
    ref: str = Field(
        ...,
        min_length=1,
        description="Git ref path",
        examples=["refs/tags/v1.0.0", "refs/tags/release-2024"],
    )

    # Annotation (optional, for annotated tags)
    message: str | None = Field(
        None,
        description="Tag annotation message (for annotated tags)",
        examples=["Release version 1.0.0", "Hotfix for bug X"],
    )
    tagger: str | None = Field(
        None,
        description="GitHub username of the person who created the tag",
        examples=["johndoe", "release-bot"],
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
        examples=["github_api", "git_show_ref"],
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
                    "name": "v1.0.0",
                    "sha": "abc123def456",
                    "ref": "refs/tags/v1.0.0",
                    "message": "Release version 1.0.0",
                    "tagger": "johndoe",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-15T08:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
