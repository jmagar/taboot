"""Email entity schema.

Represents an email message from Gmail.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Email(BaseModel):
    """Email entity representing a Gmail message.

    Extracted from:
    - Gmail API

    Examples:
        >>> from datetime import datetime, UTC
        >>> email = Email(
        ...     message_id="msg_12345",
        ...     thread_id="thread_67890",
        ...     subject="Project Update",
        ...     snippet="Thanks for the update...",
        ...     body="Full email body content",
        ...     sent_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        ...     labels=["INBOX", "IMPORTANT"],
        ...     size_estimate=2048,
        ...     has_attachments=True,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="gmail_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> email.message_id
        'msg_12345'
    """

    # Identity fields
    message_id: str = Field(
        ...,
        min_length=1,
        description="Gmail message ID",
        examples=["msg_12345", "17a4b2c3d4e5f6a7"],
    )
    thread_id: str = Field(
        ...,
        min_length=1,
        description="Gmail thread ID",
        examples=["thread_67890", "17a4b2c3d4e5f6a8"],
    )

    # Content fields
    subject: str = Field(
        ...,
        description="Email subject line",
        examples=["Project Update", "Re: Meeting Notes", "FYI: Deployment Schedule"],
    )
    snippet: str = Field(
        ...,
        description="Short preview snippet of email body (first ~150 chars)",
        examples=["Thanks for the update...", "I'll review the PR today..."],
    )
    body: str | None = Field(
        None,
        description="Full email body content (optional, may be large)",
    )

    # Metadata fields
    sent_at: datetime = Field(
        ...,
        description="When the email was sent",
    )
    labels: list[str] = Field(
        default_factory=list,
        description="Gmail labels applied to this message",
        examples=[
            ["INBOX", "IMPORTANT"],
            ["CATEGORY_PERSONAL", "UNREAD"],
            ["SENT"],
        ],
    )
    size_estimate: int = Field(
        ...,
        ge=0,
        description="Estimated size of the message in bytes",
        examples=[1024, 2048, 10240],
    )
    has_attachments: bool = Field(
        default=False,
        description="Whether this email has attachments",
    )

    # Thread/conversation fields
    in_reply_to: str | None = Field(
        None,
        description="Message ID this email is replying to",
        examples=["msg_11111"],
    )
    references: list[str] = Field(
        default_factory=list,
        description="List of message IDs referenced in email headers",
        examples=[["msg_11111", "msg_11112"]],
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
        description="When the source content was created (usually same as sent_at)",
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
                    "message_id": "msg_12345",
                    "thread_id": "thread_67890",
                    "subject": "Re: Project Update",
                    "snippet": "Thanks for the update...",
                    "body": "Full email body content here",
                    "sent_at": "2024-01-15T10:30:00Z",
                    "labels": ["INBOX", "IMPORTANT", "CATEGORY_WORK"],
                    "size_estimate": 2048,
                    "has_attachments": True,
                    "in_reply_to": "msg_11111",
                    "references": ["msg_11111", "msg_11112"],
                    "created_at": "2024-01-15T10:30:05Z",
                    "updated_at": "2024-01-15T10:30:05Z",
                    "source_timestamp": "2024-01-15T10:30:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "gmail_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
