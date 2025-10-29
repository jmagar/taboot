"""UnifiSite entity schema.

Represents a Unifi site (location/deployment).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class UnifiSite(BaseModel):
    """UnifiSite entity representing a deployment site.

    Extracted from Unifi Controller API.

    Examples:
        >>> from datetime import datetime, UTC
        >>> site = UnifiSite(
        ...     site_id="default",
        ...     name="Default Site",
        ...     description="Main office location",
        ...     wan_ip="203.0.113.10",
        ...     gateway_ip="192.168.1.1",
        ...     dns_servers=["8.8.8.8", "8.8.4.4"],
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="unifi_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> site.name
        'Default Site'
    """

    # Identity fields
    site_id: str = Field(
        ...,
        min_length=1,
        description="Unifi site ID (unique identifier)",
        examples=["default", "branch-office", "home"],
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Site name",
        examples=["Default Site", "Branch Office", "Home Network"],
    )
    description: str | None = Field(
        None,
        description="Site description",
        examples=["Main office location", "Remote branch"],
    )

    # Network fields (optional)
    wan_ip: str | None = Field(
        None,
        description="WAN IP address",
        examples=["203.0.113.10", "198.51.100.5"],
    )
    gateway_ip: str | None = Field(
        None,
        description="Gateway IP address",
        examples=["192.168.1.1", "10.0.0.1"],
    )
    dns_servers: list[str] | None = Field(
        None,
        description="DNS server IP addresses",
        examples=[["8.8.8.8", "8.8.4.4"], ["1.1.1.1"]],
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
        examples=["unifi_api", "unifi_controller", "regex"],
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
                    "site_id": "default",
                    "name": "Default Site",
                    "description": "Main office location",
                    "wan_ip": "203.0.113.10",
                    "gateway_ip": "192.168.1.1",
                    "dns_servers": ["8.8.8.8", "8.8.4.4"],
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "unifi_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
