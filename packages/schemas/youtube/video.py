"""Video entity schema.

Represents YouTube videos across YouTube data sources.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Video(BaseModel):
    """Video entity representing a YouTube video.

    Extracted from:
    - YouTube API
    - LlamaIndex YouTube reader
    - YouTube transcript extraction

    Examples:
        >>> from datetime import datetime, UTC
        >>> video = Video(
        ...     video_id="dQw4w9WgXcQ",
        ...     title="Never Gonna Give You Up",
        ...     url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ...     duration=212,
        ...     views=1400000000,
        ...     published_at=datetime(2009, 10, 25, tzinfo=UTC),
        ...     description="Rick Astley - Never Gonna Give You Up",
        ...     language="en",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="youtube_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> video.video_id
        'dQw4w9WgXcQ'
    """

    # Identity fields
    video_id: str = Field(
        ...,
        min_length=1,
        description="YouTube video ID (unique identifier)",
        examples=["dQw4w9WgXcQ", "jNQXAC9IVRw"],
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Video title",
        examples=["Python Tutorial for Beginners", "How to Learn Programming"],
    )
    url: str = Field(
        ...,
        min_length=1,
        description="Full YouTube video URL",
        examples=[
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
        ],
    )

    # Video metadata
    duration: int = Field(
        ...,
        ge=0,
        description="Video duration in seconds",
        examples=[212, 3600, 180],
    )
    views: int = Field(
        ...,
        ge=0,
        description="View count (as of extraction time)",
        examples=[1000, 1000000, 1400000000],
    )
    published_at: datetime = Field(
        ...,
        description="When the video was published on YouTube",
    )

    # Optional fields
    description: str | None = Field(
        None,
        description="Video description text",
        examples=["This is a tutorial about Python programming for beginners."],
    )
    language: str | None = Field(
        None,
        description="Video language code (ISO 639-1)",
        examples=["en", "es", "fr", "de", "ja"],
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
        description="When the source content was created (usually same as published_at)",
    )

    # Extraction metadata (required on ALL entities)
    extraction_tier: Literal["A", "B", "C"] = Field(
        ...,
        description="Extraction tier: A (deterministic), B (spaCy), C (LLM)",
    )
    extraction_method: str = Field(
        ...,
        description="Method used for extraction",
        examples=["youtube_api", "llamaindex_youtube_reader", "transcript_parser"],
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
                    "video_id": "dQw4w9WgXcQ",
                    "title": "Never Gonna Give You Up",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "duration": 212,
                    "views": 1400000000,
                    "published_at": "2009-10-25T00:00:00Z",
                    "description": "Rick Astley - Never Gonna Give You Up",
                    "language": "en",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2009-10-25T00:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "youtube_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
