"""Event entity schema.

Represents time-based occurrences.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Event(BaseModel):
    """Event entity representing time-based occurrences.

    Extracted from:
    - Gmail meetings
    - GitHub releases
    - Commit events
    - Google Calendar events

    Examples:
        >>> from datetime import datetime, UTC
        >>> event = Event(
        ...     name="Product Launch",
        ...     start_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        ...     end_time=datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC),
        ...     location="Conference Room A",
        ...     event_type="meeting",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="gmail_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> event.name
        'Product Launch'
    """

    # Identity fields
    name: str = Field(
        ...,
        min_length=1,
        description="Event name or title",
        examples=["Product Launch", "Team Meeting", "v1.0 Release"],
    )

    # Event timing (optional)
    start_time: datetime | None = Field(
        None,
        description="Event start time",
    )
    end_time: datetime | None = Field(
        None,
        description="Event end time",
    )

    # Event details (optional)
    location: str | None = Field(
        None,
        description="Event location",
        examples=["Conference Room A", "Online", "San Francisco Office"],
    )
    event_type: str | None = Field(
        None,
        description="Type of event",
        examples=["meeting", "release", "commit", "deadline"],
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
        examples=["gmail_api", "github_api", "spacy_ner", "qwen3_llm"],
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

    @model_validator(mode="after")
    def validate_time_range(self) -> "Event":
        """Validate that end_time is not before start_time."""
        if self.start_time and self.end_time:
            if self.end_time < self.start_time:
                raise ValueError("end_time must be >= start_time")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Product Launch",
                    "start_time": "2024-01-15T10:00:00Z",
                    "end_time": "2024-01-15T11:00:00Z",
                    "location": "Conference Room A",
                    "event_type": "meeting",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-15T09:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "gmail_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
