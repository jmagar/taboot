"""NATRule entity schema.

Represents a Unifi NAT rule (DNAT only - limited API support).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class NATRule(BaseModel):
    """NATRule entity representing a NAT rule (DNAT only).

    Note: Unifi API only exposes DNAT via PortForwardingRule.
    SNAT/Masquerade not available via API (Phase 2 implementation).

    Examples:
        >>> from datetime import datetime, UTC
        >>> rule = NATRule(
        ...     rule_id="5f9c1234abcd5678ef123456",
        ...     name="DNAT Rule",
        ...     enabled=True,
        ...     type="dnat",
        ...     source="192.168.0.0/16",
        ...     destination="192.168.1.100",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="unifi_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> rule.name
        'DNAT Rule'
    """

    # Identity fields
    rule_id: str = Field(
        ...,
        min_length=1,
        description="Unifi rule ID (unique identifier)",
        examples=["5f9c1234abcd5678ef123456"],
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Rule name",
        examples=["DNAT Rule", "Port Forward", "Service NAT"],
    )
    enabled: bool = Field(
        ...,
        description="Whether the rule is enabled",
    )

    # NAT configuration
    type: str = Field(
        ...,
        description="NAT type (dnat only - SNAT not available via API)",
        examples=["dnat"],
    )
    source: str = Field(
        ...,
        description="Source IP/network (any for all)",
        examples=["any", "192.168.0.0/16", "10.0.0.0/8"],
    )
    destination: str = Field(
        ...,
        description="Destination IP after NAT",
        examples=["192.168.1.100", "10.0.0.50"],
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
                    "rule_id": "5f9c1234abcd5678ef123456",
                    "name": "DNAT Rule",
                    "enabled": True,
                    "type": "dnat",
                    "source": "192.168.0.0/16",
                    "destination": "192.168.1.100",
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
