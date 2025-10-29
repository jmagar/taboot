"""Subreddit entity schema.

Represents a Reddit subreddit/community.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Subreddit(BaseModel):
    """Subreddit entity representing a Reddit community.

    Extracted from:
    - Reddit API

    Examples:
        >>> from datetime import datetime, UTC
        >>> subreddit = Subreddit(
        ...     name="python",
        ...     display_name="Python",
        ...     description="News about Python programming",
        ...     subscribers=1500000,
        ...     over_18=False,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="reddit_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> subreddit.name
        'python'
    """

    # Identity fields
    name: str = Field(
        ...,
        min_length=1,
        description="Subreddit name (lowercase, without /r/ prefix)",
        examples=["python", "programming", "learnpython"],
    )
    display_name: str = Field(
        ...,
        min_length=1,
        description="Display name with original capitalization",
        examples=["Python", "programming", "learnpython"],
    )

    # Content fields (optional)
    description: str | None = Field(
        None,
        description="Subreddit description/sidebar text",
        examples=["News about the dynamic, interpreted programming language Python."],
    )
    subscribers: int | None = Field(
        None,
        ge=0,
        description="Number of subscribers",
        examples=[1500000, 50000],
    )
    created_utc: datetime | None = Field(
        None,
        description="When the subreddit was created (UTC timestamp from Reddit)",
    )
    over_18: bool | None = Field(
        None,
        description="Whether the subreddit is marked as NSFW",
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
                    "name": "python",
                    "display_name": "Python",
                    "description": "News about the dynamic, interpreted programming language Python.",
                    "subscribers": 1500000,
                    "created_utc": "2008-01-25T00:00:00Z",
                    "over_18": False,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2008-01-25T00:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "reddit_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
