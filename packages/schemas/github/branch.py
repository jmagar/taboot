"""Branch entity schema.

Represents a Git branch with protection status and reference information.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Branch(BaseModel):
    """Git branch entity.

    Extracted from:
    - GitHub API branch data
    - Git refs
    - Branch protection rules

    Examples:
        >>> from datetime import datetime, UTC
        >>> branch = Branch(
        ...     name="main",
        ...     protected=True,
        ...     sha="abc123def456",
        ...     ref="refs/heads/main",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> branch.name
        'main'
    """

    # Identity fields
    repository_full_name: str = Field(
        ...,
        min_length=1,
        description="Full repository name this branch belongs to (owner/name)",
        examples=["anthropics/claude-code"],
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Branch name",
        examples=["main", "develop", "feature/new-thing"],
    )

    # Protection status (optional)
    protected: bool | None = Field(
        None,
        description="Whether the branch is protected",
        examples=[True, False],
    )

    # Git metadata
    sha: str = Field(
        ...,
        min_length=1,
        description="Commit SHA that the branch points to",
        examples=["abc123def456", "1234567890abcdef"],
    )
    ref: str = Field(
        ...,
        min_length=1,
        description="Git ref path",
        examples=["refs/heads/main", "refs/heads/feature/new"],
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
                    "name": "main",
                    "protected": True,
                    "sha": "abc123def456",
                    "ref": "refs/heads/main",
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
