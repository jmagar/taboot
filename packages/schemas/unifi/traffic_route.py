"""TrafficRoute entity schema.

Represents a Unifi policy-based routing rule.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TrafficRoute(BaseModel):
    """TrafficRoute entity representing a policy-based routing rule.

    Extracted from Unifi Controller API: /v2/api/site/{site}/trafficroutes

    Examples:
        >>> from datetime import datetime, UTC
        >>> route = TrafficRoute(
        ...     route_id="5f9c1234abcd5678ef123456",
        ...     name="Route to VPN",
        ...     enabled=True,
        ...     next_hop="192.168.1.1",
        ...     matching_target="domain",
        ...     network_id="5f9c1234abcd5678ef111111",
        ...     ip_addresses=["10.0.0.0/24"],
        ...     domains=["internal.company.com"],
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="unifi_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> route.name
        'Route to VPN'
    """

    # Identity fields
    route_id: str = Field(
        ...,
        min_length=1,
        description="Unifi route ID (unique identifier)",
        examples=["5f9c1234abcd5678ef123456"],
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Route name",
        examples=["Route to VPN", "Failover Route", "Internal Route"],
    )
    enabled: bool = Field(
        ...,
        description="Whether the route is enabled",
    )

    # Routing configuration
    next_hop: str = Field(
        ...,
        description="Next hop gateway IP",
        examples=["192.168.1.1", "10.0.0.1"],
    )
    matching_target: str | None = Field(
        None,
        description="What to match against (ip, domain, network)",
        examples=["ip", "domain", "network"],
    )
    network_id: str | None = Field(
        None,
        description="Network ID for route",
        examples=["5f9c1234abcd5678ef111111"],
    )
    ip_addresses: list[str] | None = Field(
        None,
        description="IP addresses or CIDR ranges to match",
        examples=[["10.0.0.0/24", "192.168.1.0/24"]],
    )
    domains: list[str] | None = Field(
        None,
        description="Domain names to match",
        examples=[["internal.company.com", "vpn.company.com"]],
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
                    "route_id": "5f9c1234abcd5678ef123456",
                    "name": "Route to VPN",
                    "enabled": True,
                    "next_hop": "192.168.1.1",
                    "matching_target": "domain",
                    "network_id": "5f9c1234abcd5678ef111111",
                    "ip_addresses": ["10.0.0.0/24"],
                    "domains": ["internal.company.com"],
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
