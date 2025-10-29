"""RedditComment entity schema.

Represents a Reddit comment on a post.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RedditComment(BaseModel):
    """RedditComment entity representing a comment on a Reddit post.

    Extracted from:
    - Reddit API

    Examples:
        >>> from datetime import datetime, UTC
        >>> comment = RedditComment(
        ...     comment_id="def456",
        ...     body="Great question! I recommend starting with the official Python tutorial.",
        ...     score=25,
        ...     parent_id="abc123",
        ...     depth=1,
        ...     gilded=1,
        ...     edited=False,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="reddit_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> comment.comment_id
        'def456'
    """

    # Identity fields
    comment_id: str = Field(
        ...,
        min_length=1,
        description="Reddit comment ID (unique identifier)",
        examples=["def456", "ghi789"],
    )
    body: str = Field(
        ...,
        min_length=1,
        description="Comment body text",
        examples=["Great question! I recommend starting with the official Python tutorial."],
    )

    # Content fields (optional)
    score: int | None = Field(
        None,
        description="Comment score (upvotes - downvotes)",
        examples=[25, 0, -3],
    )
    created_utc: datetime | None = Field(
        None,
        description="When the comment was created (UTC timestamp from Reddit)",
    )
    permalink: str | None = Field(
        None,
        description="Relative permalink to the comment",
        examples=["/r/python/comments/abc123/how_to_learn_python/def456/"],
    )
    parent_id: str | None = Field(
        None,
        description="ID of the parent post or comment",
        examples=["abc123", "def456"],
    )
    depth: int | None = Field(
        None,
        ge=0,
        description="Comment depth/nesting level (0 = top-level comment)",
        examples=[0, 1, 2],
    )
    gilded: int | None = Field(
        None,
        ge=0,
        description="Number of times the comment has been gilded/awarded",
        examples=[0, 1, 3],
    )
    edited: bool | None = Field(
        None,
        description="Whether the comment has been edited",
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
        examples=["reddit_api", "regex", "spacy_ner"],
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

    @field_validator("extraction_tier")
    @classmethod
    def validate_extraction_tier(cls, v: str) -> str:
        """Validate extraction_tier is A, B, or C."""
        if v not in ("A", "B", "C"):
            raise ValueError("extraction_tier must be A, B, or C")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "comment_id": "def456",
                    "body": "Great question! I recommend starting with the official Python tutorial.",
                    "score": 25,
                    "created_utc": "2024-01-01T11:00:00Z",
                    "permalink": "/r/python/comments/abc123/how_to_learn_python/def456/",
                    "parent_id": "abc123",
                    "depth": 1,
                    "gilded": 1,
                    "edited": False,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-01T11:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "reddit_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
