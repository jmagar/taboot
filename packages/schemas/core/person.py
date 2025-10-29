"""Person entity schema.

Represents individual people across all data sources (GitHub, Gmail, Reddit, YouTube).
"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Person(BaseModel):
    """Person entity representing an individual across multiple sources.

    Extracted from:
    - GitHub users
    - Gmail contacts
    - Reddit users
    - YouTube creators

    Examples:
        >>> from datetime import datetime, UTC
        >>> person = Person(
        ...     name="John Doe",
        ...     email="john.doe@example.com",
        ...     role="Senior Engineer",
        ...     github_username="johndoe",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> person.name
        'John Doe'
    """

    # Identity fields
    name: str = Field(
        ...,
        min_length=1,
        description="Full name of the person",
        examples=["John Doe", "Jane Smith"],
    )
    email: str = Field(
        ...,
        description="Email address (validated format)",
        examples=["john.doe@example.com"],
    )

    # Profile fields (optional)
    role: str | None = Field(
        None,
        description="Professional role or title",
        examples=["Senior Engineer", "Product Manager", "CTO"],
    )
    bio: str | None = Field(
        None,
        description="Short biography or description",
        examples=["Passionate about open source and Python"],
    )

    # Source-specific usernames (optional)
    github_username: str | None = Field(
        None,
        description="GitHub username",
        examples=["johndoe"],
    )
    reddit_username: str | None = Field(
        None,
        description="Reddit username",
        examples=["john_dev"],
    )
    youtube_channel: str | None = Field(
        None,
        description="YouTube channel handle or ID",
        examples=["@johndoedev", "UCxxxxxxxxxxxxx"],
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
        examples=["github_api", "spacy_ner", "qwen3_llm", "gmail_api", "regex"],
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

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format using simple regex."""
        # Simple email validation pattern
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "role": "Senior Engineer",
                    "bio": "Passionate about open source and Python",
                    "github_username": "johndoe",
                    "reddit_username": "john_dev",
                    "youtube_channel": "@johndoedev",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2020-05-10T08:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
