"""FirewallRule entity schema.

Represents a Unifi firewall rule.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FirewallRule(BaseModel):
    """FirewallRule entity representing a firewall policy.

    Extracted from Unifi Controller API: /v2/api/site/{site}/firewall-policies

    Examples:
        >>> from datetime import datetime, UTC
        >>> rule = FirewallRule(
        ...     rule_id="5f9c1234abcd5678ef123456",
        ...     name="Block External",
        ...     enabled=True,
        ...     action="DROP",
        ...     protocol="tcp",
        ...     ip_version="ipv4",
        ...     index=1,
        ...     source_zone="WAN",
        ...     dest_zone="LAN",
        ...     logging=True,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="unifi_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> rule.name
        'Block External'
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
        examples=["Block External", "Allow Internal", "Drop IoT"],
    )
    enabled: bool = Field(
        ...,
        description="Whether the rule is enabled",
    )

    # Firewall configuration
    action: str = Field(
        ...,
        description="Action to take (ALLOW, DROP, REJECT)",
        examples=["ALLOW", "DROP", "REJECT"],
    )
    protocol: str = Field(
        ...,
        description="Protocol to match (all, tcp, udp, icmp)",
        examples=["all", "tcp", "udp", "icmp"],
    )
    ip_version: str = Field(
        ...,
        description="IP version (ipv4, ipv6)",
        examples=["ipv4", "ipv6"],
    )
    index: int = Field(
        ...,
        ge=0,
        description="Rule priority/index (lower = higher priority)",
    )
    source_zone: str | None = Field(
        None,
        description="Source network zone",
        examples=["WAN", "LAN", "Guest"],
    )
    dest_zone: str | None = Field(
        None,
        description="Destination network zone",
        examples=["LAN", "WAN", "IoT"],
    )
    logging: bool | None = Field(
        None,
        description="Whether to log matches",
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
                    "name": "Block External",
                    "enabled": True,
                    "action": "DROP",
                    "protocol": "tcp",
                    "ip_version": "ipv4",
                    "index": 1,
                    "source_zone": "WAN",
                    "dest_zone": "LAN",
                    "logging": True,
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
