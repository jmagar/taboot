"""RedditPost entity schema.

Represents a Reddit post/submission.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RedditPost(BaseModel):
    """RedditPost entity representing a Reddit post/submission.

    Extracted from:
    - Reddit API

    Examples:
        >>> from datetime import datetime, UTC
        >>> post = RedditPost(
        ...     post_id="abc123",
        ...     title="How to learn Python?",
        ...     selftext="I'm new to programming and want to learn Python.",
        ...     score=150,
        ...     num_comments=42,
        ...     is_self=True,
        ...     over_18=False,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="reddit_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> post.post_id
        'abc123'
    """

    # Identity fields
    post_id: str = Field(
        ...,
        min_length=1,
        description="Reddit post ID (unique identifier)",
        examples=["abc123", "xyz789"],
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Post title",
        examples=["How to learn Python?", "What's new in Python 3.12?"],
    )

    # Content fields (optional)
    selftext: str | None = Field(
        None,
        description="Post body text (for self posts)",
        examples=["I'm new to programming and want to learn Python. Any suggestions?"],
    )
    score: int | None = Field(
        None,
        description="Post score (upvotes - downvotes)",
        examples=[150, 42, -5],
    )
    num_comments: int | None = Field(
        None,
        ge=0,
        description="Number of comments on the post",
        examples=[42, 0, 1500],
    )
    created_utc: datetime | None = Field(
        None,
        description="When the post was created (UTC timestamp from Reddit)",
    )
    url: str | None = Field(
        None,
        description="Full URL to the post on Reddit",
        examples=["https://reddit.com/r/python/comments/abc123/how_to_learn_python/"],
    )
    permalink: str | None = Field(
        None,
        description="Relative permalink to the post",
        examples=["/r/python/comments/abc123/how_to_learn_python/"],
    )
    is_self: bool | None = Field(
        None,
        description="Whether this is a self/text post (vs link post)",
    )
    over_18: bool | None = Field(
        None,
        description="Whether the post is marked as NSFW",
    )
    gilded: int | None = Field(
        None,
        ge=0,
        description="Number of times the post has been gilded/awarded",
        examples=[0, 1, 5],
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
                    "post_id": "abc123",
                    "title": "How to learn Python?",
                    "selftext": "I'm new to programming and want to learn Python. Any suggestions?",
                    "score": 150,
                    "num_comments": 42,
                    "created_utc": "2024-01-01T10:00:00Z",
                    "url": "https://reddit.com/r/python/comments/abc123/how_to_learn_python/",
                    "permalink": "/r/python/comments/abc123/how_to_learn_python/",
                    "is_self": True,
                    "over_18": False,
                    "gilded": 2,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-01T10:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "reddit_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
