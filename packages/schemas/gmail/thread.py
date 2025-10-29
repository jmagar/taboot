"""Thread entity schema.

Represents an email conversation thread from Gmail.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Thread(BaseModel):
    """Thread entity representing a Gmail conversation thread.

    Extracted from:
    - Gmail API

    Examples:
        >>> from datetime import datetime, UTC
        >>> thread = Thread(
        ...     thread_id="thread_67890",
        ...     subject="Re: Project Discussion",
        ...     message_count=5,
        ...     participant_count=3,
        ...     first_message_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        ...     last_message_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        ...     labels=["INBOX", "IMPORTANT"],
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="gmail_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> thread.thread_id
        'thread_67890'
    """

    # Identity field
    thread_id: str = Field(
        ...,
        min_length=1,
        description="Gmail thread ID",
        examples=["thread_67890", "17a4b2c3d4e5f6a8"],
    )

    # Content fields
    subject: str = Field(
        ...,
        description="Thread subject (from first message)",
        examples=["Project Discussion", "Re: Meeting Notes", "FYI: Deployment"],
    )

    # Statistics fields
    message_count: int = Field(
        ...,
        ge=1,
        description="Number of messages in this thread",
        examples=[1, 3, 10],
    )
    participant_count: int = Field(
        ...,
        ge=1,
        description="Number of unique participants in this thread",
        examples=[1, 2, 5],
    )

    # Timeline fields
    first_message_at: datetime = Field(
        ...,
        description="Timestamp of the first message in the thread",
    )
    last_message_at: datetime = Field(
        ...,
        description="Timestamp of the most recent message in the thread",
    )

    # Metadata fields
    labels: list[str] = Field(
        default_factory=list,
        description="Gmail labels applied to this thread",
        examples=[
            ["INBOX", "IMPORTANT"],
            ["CATEGORY_PERSONAL", "UNREAD"],
            ["SENT"],
        ],
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
        description="When the source content was created (usually first_message_at)",
    )

    # Extraction metadata (required on ALL entities)
    extraction_tier: Literal["A", "B", "C"] = Field(
        ...,
        description="Extraction tier: A (deterministic), B (spaCy), C (LLM)",
    )
    extraction_method: str = Field(
        ...,
        description="Method used for extraction",
        examples=["gmail_api", "mbox_parser", "regex"],
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
                    "thread_id": "thread_67890",
                    "subject": "Re: Project Discussion",
                    "message_count": 5,
                    "participant_count": 3,
                    "first_message_at": "2024-01-15T10:00:00Z",
                    "last_message_at": "2024-01-15T12:00:00Z",
                    "labels": ["INBOX", "IMPORTANT", "CATEGORY_WORK"],
                    "created_at": "2024-01-15T12:00:05Z",
                    "updated_at": "2024-01-15T12:00:05Z",
                    "source_timestamp": "2024-01-15T10:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "gmail_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
