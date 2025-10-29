"""PortForwardingRule entity schema.

Represents a Unifi port forwarding rule (DNAT).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PortForwardingRule(BaseModel):
    """PortForwardingRule entity representing a port forwarding configuration.

    Extracted from Unifi Controller API: /api/s/{site}/rest/portforward

    Examples:
        >>> from datetime import datetime, UTC
        >>> rule = PortForwardingRule(
        ...     rule_id="5f9c1234abcd5678ef123456",
        ...     name="SSH Forward",
        ...     enabled=True,
        ...     proto="tcp",
        ...     src="any",
        ...     dst_port=22,
        ...     fwd="192.168.1.100",
        ...     fwd_port=22,
        ...     pfwd_interface="wan",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="unifi_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> rule.name
        'SSH Forward'
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
        examples=["SSH Forward", "HTTPS Forward", "Game Server"],
    )
    enabled: bool = Field(
        ...,
        description="Whether the rule is enabled",
    )

    # Port forwarding configuration
    proto: str = Field(
        ...,
        description="Protocol (tcp, udp, tcp_udp)",
        examples=["tcp", "udp", "tcp_udp"],
    )
    src: str = Field(
        ...,
        description="Source IP/network (any for all)",
        examples=["any", "192.168.1.0/24", "10.0.0.5"],
    )
    dst_port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Destination port (external)",
    )
    fwd: str = Field(
        ...,
        description="Forward to IP (internal)",
        examples=["192.168.1.100", "10.0.0.50"],
    )
    fwd_port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Forward to port (internal)",
    )
    pfwd_interface: str | None = Field(
        None,
        description="Port forward interface",
        examples=["wan", "wan2"],
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
                    "name": "SSH Forward",
                    "enabled": True,
                    "proto": "tcp",
                    "src": "any",
                    "dst_port": 22,
                    "fwd": "192.168.1.100",
                    "fwd_port": 22,
                    "pfwd_interface": "wan",
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
