"""Place entity schema.

Represents physical or virtual locations.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Place(BaseModel):
    """Place entity representing physical or virtual locations.

    Extracted from:
    - Tailscale networks
    - Unifi sites
    - Gmail locations
    - Document mentions

    Examples:
        >>> from datetime import datetime, UTC
        >>> place = Place(
        ...     name="San Francisco Office",
        ...     address="123 Market St, San Francisco, CA 94105",
        ...     coordinates="37.7749,-122.4194",
        ...     place_type="office",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="B",
        ...     extraction_method="spacy_ner",
        ...     confidence=0.85,
        ...     extractor_version="1.0.0",
        ... )
        >>> place.name
        'San Francisco Office'
    """

    # Identity fields
    name: str = Field(
        ...,
        min_length=1,
        description="Place name or identifier",
        examples=["San Francisco Office", "Main Datacenter", "Home Network"],
    )

    # Location fields (optional)
    address: str | None = Field(
        None,
        description="Physical address",
        examples=["123 Market St, San Francisco, CA 94105"],
    )
    coordinates: str | None = Field(
        None,
        description="Geographic coordinates (lat,lon)",
        examples=["37.7749,-122.4194"],
    )
    place_type: str | None = Field(
        None,
        description="Type of place",
        examples=["office", "datacenter", "network", "city", "building"],
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
        examples=["tailscale_api", "spacy_ner", "qwen3_llm", "regex"],
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
                    "name": "San Francisco Office",
                    "address": "123 Market St, San Francisco, CA 94105",
                    "coordinates": "37.7749,-122.4194",
                    "place_type": "office",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2020-05-10T08:00:00Z",
                    "extraction_tier": "B",
                    "extraction_method": "spacy_ner",
                    "confidence": 0.85,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
