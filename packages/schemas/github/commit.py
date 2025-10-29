"""Commit entity schema.

Represents a Git commit with author information and diff statistics.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Commit(BaseModel):
    """Git commit entity.

    Extracted from:
    - GitHub API commit data
    - Git log history
    - Repository commit graphs

    Examples:
        >>> from datetime import datetime, UTC
        >>> commit = Commit(
        ...     sha="abc123def456",
        ...     message="Fix bug in parser",
        ...     author_login="johndoe",
        ...     author_name="John Doe",
        ...     author_email="john@example.com",
        ...     timestamp=datetime.now(UTC),
        ...     tree_sha="tree123abc",
        ...     parent_shas=["parent1abc", "parent2def"],
        ...     additions=150,
        ...     deletions=50,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> commit.sha
        'abc123def456'
    """

    # Identity fields
    sha: str = Field(
        ...,
        min_length=1,
        description="Commit SHA hash (unique identifier)",
        examples=["abc123def456", "1234567890abcdef"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Commit message",
        examples=["Fix bug in parser", "Add new feature", "Update documentation"],
    )

    # Author information
    author_login: str | None = Field(
        None,
        description="GitHub username of commit author (if available)",
        examples=["johndoe", "jane-smith"],
    )
    author_name: str = Field(
        ...,
        min_length=1,
        description="Author name from git config",
        examples=["John Doe", "Jane Smith"],
    )
    author_email: str = Field(
        ...,
        min_length=1,
        description="Author email from git config",
        examples=["john@example.com", "jane@company.com"],
    )

    # Temporal information
    timestamp: datetime = Field(
        ...,
        description="When the commit was created (git author date)",
    )

    # Git metadata
    tree_sha: str = Field(
        ...,
        min_length=1,
        description="Tree SHA hash",
        examples=["tree123abc", "treexyz789"],
    )
    parent_shas: list[str] | None = Field(
        None,
        description="Parent commit SHAs (empty for initial commit, multiple for merge commits)",
        examples=[["parent1abc"], ["parent1abc", "parent2def"]],
    )

    # Statistics (optional)
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
                    "sha": "abc123def456",
                    "message": "Fix bug in parser",
                    "author_login": "johndoe",
                    "author_name": "John Doe",
                    "author_email": "john@example.com",
                    "timestamp": "2024-01-15T12:00:00Z",
                    "tree_sha": "tree123abc",
                    "parent_shas": ["parent1abc"],
                    "additions": 150,
                    "deletions": 50,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-15T12:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
