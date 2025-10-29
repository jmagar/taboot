"""UnifiClient entity schema.

Represents a client device connected to a Unifi network.
"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class UnifiClient(BaseModel):
    """UnifiClient entity representing a client device on the network.

    Extracted from Unifi Controller API.

    Examples:
        >>> from datetime import datetime, UTC
        >>> client = UnifiClient(
        ...     mac="aa:bb:cc:dd:ee:ff",
        ...     hostname="laptop-01",
        ...     ip="192.168.1.50",
        ...     network="LAN",
        ...     is_wired=False,
        ...     link_speed=866,
        ...     connection_type="wifi6",
        ...     uptime=7200,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="unifi_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> client.mac
        'aa:bb:cc:dd:ee:ff'
    """

    # Identity fields
    mac: str = Field(
        ...,
        min_length=1,
        description="MAC address of the client (unique identifier)",
        examples=["aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66"],
    )
    hostname: str = Field(
        ...,
        min_length=1,
        description="Hostname of the client",
        examples=["laptop-01", "phone-jane", "server-02"],
    )
    ip: str = Field(
        ...,
        description="IP address of the client",
        examples=["192.168.1.50", "10.0.0.100"],
    )
    network: str = Field(
        ...,
        description="Network name the client is connected to",
        examples=["LAN", "Guest", "IoT"],
    )

    # Connection fields
    is_wired: bool = Field(
        ...,
        description="Whether the client is wired or wireless",
    )
    link_speed: int | None = Field(
        None,
        description="Link speed in Mbps",
        examples=[866, 1000, 100],
    )
    connection_type: str | None = Field(
        None,
        description="Connection type details",
        examples=["wifi6", "wifi5", "ethernet", "wifi4"],
    )
    uptime: int | None = Field(
        None,
        ge=0,
        description="Client connection uptime in seconds",
        examples=[7200, 3600, 0],
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

    @field_validator("mac")
    @classmethod
    def validate_mac(cls, v: str) -> str:
        """Validate MAC address format."""
        # MAC address pattern: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX
        pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
        if not re.match(pattern, v):
            raise ValueError("Invalid MAC address format")
        return v.lower()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "hostname": "laptop-01",
                    "ip": "192.168.1.50",
                    "network": "LAN",
                    "is_wired": False,
                    "link_speed": 866,
                    "connection_type": "wifi6",
                    "uptime": 7200,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-15T10:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "unifi_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
