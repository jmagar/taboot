"""PullRequest entity schema.

Represents a GitHub pull request with merge information and diff statistics.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PullRequest(BaseModel):
    """GitHub pull request entity.

    Extracted from:
    - GitHub API pull request data
    - Git merge requests
    - Code review systems

    Examples:
        >>> from datetime import datetime, UTC
        >>> pr = PullRequest(
        ...     number=123,
        ...     title="Add new feature",
        ...     state="open",
        ...     base_branch="main",
        ...     head_branch="feature/new-thing",
        ...     merged=False,
        ...     commits=5,
        ...     additions=250,
        ...     deletions=50,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> pr.number
        123
    """

    # Identity fields
    repository_full_name: str = Field(
        ...,
        min_length=1,
        description="Full repository name this pull request belongs to (owner/name)",
        examples=["anthropics/claude-code"],
    )
    number: int = Field(
        ...,
        ge=1,
        description="Pull request number (unique within repository)",
        examples=[123, 456, 1000],
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Pull request title",
        examples=["Add new feature", "Fix bug in parser", "Update documentation"],
    )
    state: str = Field(
        ...,
        min_length=1,
        description="Pull request state (open, closed, merged)",
        examples=["open", "closed", "merged"],
    )

    # Branch information
    base_branch: str = Field(
        ...,
        min_length=1,
        description="Target branch for merge",
        examples=["main", "develop", "release/v1.0"],
    )
    head_branch: str = Field(
        ...,
        min_length=1,
        description="Source branch being merged",
        examples=["feature/new-thing", "fix/bug-123", "refactor/cleanup"],
    )

    # Merge information (optional)
    merged: bool | None = Field(
        None,
        description="Whether the pull request has been merged",
        examples=[True, False],
    )
    merged_at: datetime | None = Field(
        None,
        description="When the pull request was merged (if merged)",
    )

    # Statistics (optional)
    commits: int | None = Field(
        None,
        ge=0,
        description="Number of commits in the pull request",
        examples=[1, 5, 20],
    )
    additions: int | None = Field(
        None,
        ge=0,
        description="Number of lines added",
        examples=[100, 250, 1000],
    )
    deletions: int | None = Field(
        None,
        ge=0,
        description="Number of lines deleted",
        examples=[50, 100, 500],
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
        examples=["github_api", "git_log"],
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
                    "number": 123,
                    "title": "Add new feature",
                    "state": "merged",
                    "base_branch": "main",
                    "head_branch": "feature/new-thing",
                    "merged": True,
                    "merged_at": "2024-01-15T12:00:00Z",
                    "commits": 5,
                    "additions": 250,
                    "deletions": 50,
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
