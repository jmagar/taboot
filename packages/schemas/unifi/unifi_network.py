"""UnifiNetwork entity schema.

Represents a Unifi network (VLAN/subnet configuration).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class UnifiNetwork(BaseModel):
    """UnifiNetwork entity representing a network configuration.

    Extracted from Unifi Controller API.

    Examples:
        >>> from datetime import datetime, UTC
        >>> network = UnifiNetwork(
        ...     network_id="5f9c1234abcd5678ef123456",
        ...     name="LAN",
        ...     vlan_id=1,
        ...     subnet="192.168.1.0/24",
        ...     gateway_ip="192.168.1.1",
        ...     dns_servers=["8.8.8.8", "8.8.4.4"],
        ...     wifi_name="MyWiFi",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="unifi_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> network.name
        'LAN'
    """

    # Identity fields
    network_id: str = Field(
        ...,
        min_length=1,
        description="Unifi network ID (unique identifier)",
        examples=["5f9c1234abcd5678ef123456"],
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Network name",
        examples=["LAN", "Guest", "IoT", "Management"],
    )

    # Network configuration
    vlan_id: int = Field(
        ...,
        ge=1,
        le=4094,
        description="VLAN ID (1-4094)",
    )
    subnet: str = Field(
        ...,
        description="Network subnet in CIDR notation",
        examples=["192.168.1.0/24", "10.0.0.0/16"],
    )
    gateway_ip: str = Field(
        ...,
        description="Gateway IP address",
        examples=["192.168.1.1", "10.0.0.1"],
    )
    dns_servers: list[str] | None = Field(
        None,
        description="DNS server IP addresses",
        examples=[["8.8.8.8", "8.8.4.4"], ["1.1.1.1"]],
    )
    wifi_name: str | None = Field(
        None,
        description="WiFi SSID name (if wireless)",
        examples=["MyWiFi", "GuestNetwork"],
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
                    "network_id": "5f9c1234abcd5678ef123456",
                    "name": "LAN",
                    "vlan_id": 1,
                    "subnet": "192.168.1.0/24",
                    "gateway_ip": "192.168.1.1",
                    "dns_servers": ["8.8.8.8", "8.8.4.4"],
                    "wifi_name": "MyWiFi",
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
