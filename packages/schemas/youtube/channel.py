"""Channel entity schema.

Represents YouTube channels.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Channel(BaseModel):
    """Channel entity representing a YouTube channel.

    Extracted from:
    - YouTube API
    - LlamaIndex YouTube reader
    """

    # Identity fields
    channel_id: str = Field(
        ...,
        min_length=1,
        description="YouTube channel ID (unique identifier)",
        examples=["UCxxxxxxxxxxxxx", "UCyyyyyyyyyyyyyy"],
    )
    channel_name: str = Field(
        ...,
        min_length=1,
        description="Channel name/title",
        examples=["Tech Channel", "Python Tutorials"],
    )
    channel_url: str = Field(
        ...,
        min_length=1,
        description="Full YouTube channel URL",
        examples=[
            "https://www.youtube.com/channel/UCxxxxxxxxxxxxx",
            "https://www.youtube.com/@username",
        ],
    )

    # Channel metadata
    subscribers: int | None = Field(
        None,
        ge=0,
        description="Subscriber count (as of extraction time)",
        examples=[1000, 1000000, 10000000],
    )
    verified: bool = Field(
        False,
        description="Whether the channel is verified by YouTube",
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
        description="When the source content was created",
    )

    # Extraction metadata (required on ALL entities)
    extraction_tier: Literal["A", "B", "C"] = Field(
        ...,
        description="Extraction tier: A (deterministic), B (spaCy), C (LLM)",
    )
    extraction_method: str = Field(
        ...,
        description="Method used for extraction",
        examples=["youtube_api", "llamaindex_youtube_reader"],
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
                    "channel_id": "UCxxxxxxxxxxxxx",
                    "channel_name": "Tech Channel",
                    "channel_url": "https://www.youtube.com/channel/UCxxxxxxxxxxxxx",
                    "subscribers": 1000000,
                    "verified": True,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "youtube_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
