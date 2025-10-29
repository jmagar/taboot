"""Comment entity schema.

Represents a comment on a GitHub issue or pull request.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Comment(BaseModel):
    """GitHub comment entity.

    Extracted from:
    - GitHub API comment data
    - Issue comments
    - Pull request comments
    - Code review comments

    Examples:
        >>> from datetime import datetime, UTC
        >>> comment = Comment(
        ...     id=12345,
        ...     author_login="johndoe",
        ...     body="This looks good!",
        ...     comment_created_at=datetime.now(UTC),
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> comment.id
        12345
    """

    # Identity fields
    repository_full_name: str = Field(
        ...,
        min_length=1,
        description="Full repository name this comment belongs to (owner/name)",
        examples=["anthropics/claude-code"],
    )
    issue_number: int = Field(
        ...,
        ge=1,
        description="Issue number associated with the comment",
        examples=[42, 123],
    )
    id: int = Field(
        ...,
        ge=1,
        description="Comment ID (unique across GitHub)",
        examples=[12345, 67890, 111111],
    )

    # Author information
    author_login: str = Field(
        ...,
        min_length=1,
        description="GitHub username of comment author",
        examples=["johndoe", "jane-smith"],
    )

    # Content
    body: str = Field(
        ...,
        min_length=1,
        description="Comment body (markdown text)",
        examples=["This looks good!", "Can you fix the typo on line 42?", "LGTM :+1:"],
    )

    # Comment timestamps (separate from our tracking timestamps)
    comment_created_at: datetime = Field(
        ...,
        description="When the comment was created on GitHub",
    )
    comment_updated_at: datetime | None = Field(
        None,
        description="When the comment was last updated on GitHub (if edited)",
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
        examples=["github_api", "comment_scraper"],
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
                    "issue_number": 42,
                    "id": 12345,
                    "author_login": "johndoe",
                    "body": "This looks good!",
                    "comment_created_at": "2024-01-15T12:00:00Z",
                    "comment_updated_at": "2024-01-15T13:00:00Z",
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
