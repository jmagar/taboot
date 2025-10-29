"""Repository entity schema.

Represents a GitHub repository with metadata, statistics, and configuration.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Repository(BaseModel):
    """GitHub repository entity.

    Extracted from:
    - GitHub API repository data
    - Repository README metadata
    - Git configuration files

    Examples:
        >>> from datetime import datetime, UTC
        >>> repo = Repository(
        ...     owner="anthropics",
        ...     name="claude-code",
        ...     full_name="anthropics/claude-code",
        ...     url="https://github.com/anthropics/claude-code",
        ...     default_branch="main",
        ...     description="AI-powered coding assistant",
        ...     language="Python",
        ...     stars=1500,
        ...     forks=200,
        ...     open_issues=45,
        ...     is_private=False,
        ...     is_fork=False,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> repo.full_name
        'anthropics/claude-code'
    """

    # Identity fields
    owner: str = Field(
        ...,
        min_length=1,
        description="Repository owner (user or organization)",
        examples=["anthropics", "openai", "google"],
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Repository name",
        examples=["claude-code", "pytorch", "tensorflow"],
    )
    full_name: str = Field(
        ...,
        min_length=1,
        description="Full repository name (owner/name)",
        examples=["anthropics/claude-code", "pytorch/pytorch"],
    )
    url: str = Field(
        ...,
        min_length=1,
        description="GitHub repository URL",
        examples=["https://github.com/anthropics/claude-code"],
    )
    default_branch: str = Field(
        ...,
        min_length=1,
        description="Default branch name",
        examples=["main", "master", "develop"],
    )

    # Metadata fields (optional)
    description: str | None = Field(
        None,
        description="Repository description",
        examples=["AI-powered coding assistant", "Machine learning framework"],
    )
    language: str | None = Field(
        None,
        description="Primary programming language",
        examples=["Python", "TypeScript", "Go", "Rust"],
    )

    # Statistics (optional)
    stars: int | None = Field(
        None,
        ge=0,
        description="Number of stars (GitHub stars count)",
        examples=[1500, 25000],
    )
    forks: int | None = Field(
        None,
        ge=0,
        description="Number of forks",
        examples=[200, 5000],
    )
    open_issues: int | None = Field(
        None,
        ge=0,
        description="Number of open issues",
        examples=[45, 230],
    )

    # Configuration (optional)
    is_private: bool | None = Field(
        None,
        description="Whether repository is private",
        examples=[False, True],
    )
    is_fork: bool | None = Field(
        None,
        description="Whether repository is a fork",
        examples=[False, True],
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
        examples=["github_api", "git_config", "readme_parser"],
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
                    "owner": "anthropics",
                    "name": "claude-code",
                    "full_name": "anthropics/claude-code",
                    "url": "https://github.com/anthropics/claude-code",
                    "default_branch": "main",
                    "description": "AI-powered coding assistant",
                    "language": "Python",
                    "stars": 1500,
                    "forks": 200,
                    "open_issues": 45,
                    "is_private": False,
                    "is_fork": False,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2023-01-01T00:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
