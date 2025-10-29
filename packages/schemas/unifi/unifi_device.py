"""UnifiDevice entity schema.

Represents a Unifi network device (switch, AP, gateway, etc.).
"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class UnifiDevice(BaseModel):
    """UnifiDevice entity representing a Unifi network device.

    Extracted from Unifi Controller API.

    Examples:
        >>> from datetime import datetime, UTC
        >>> device = UnifiDevice(
        ...     mac="00:11:22:33:44:55",
        ...     hostname="unifi-switch-01",
        ...     type="usw",
        ...     model="US-24-250W",
        ...     adopted=True,
        ...     state="connected",
        ...     ip="192.168.1.100",
        ...     firmware_version="6.5.55",
        ...     link_speed=1000,
        ...     connection_type="wired",
        ...     uptime=86400,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="unifi_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> device.mac
        '00:11:22:33:44:55'
    """

    # Identity fields
    mac: str = Field(
        ...,
        min_length=1,
        description="MAC address of the device (unique identifier)",
        examples=["00:11:22:33:44:55", "aa:bb:cc:dd:ee:ff"],
    )
    hostname: str = Field(
        ...,
        min_length=1,
        description="Hostname of the device",
        examples=["unifi-switch-01", "unifi-ap-lobby"],
    )
    type: str = Field(
        ...,
        description="Device type (usw=switch, uap=AP, ugw=gateway, etc.)",
        examples=["usw", "uap", "ugw", "udm"],
    )
    model: str = Field(
        ...,
        description="Device model number",
        examples=["US-24-250W", "UAP-AC-PRO", "UDM-Pro"],
    )

    # Status fields
    adopted: bool = Field(
        ...,
        description="Whether the device is adopted by the controller",
    )
    state: str = Field(
        ...,
        description="Current device state",
        examples=["connected", "disconnected", "upgrading", "provisioning"],
    )

    # Network fields (optional)
    ip: str | None = Field(
        None,
        description="IP address of the device",
        examples=["192.168.1.100", "10.0.0.50"],
    )
    firmware_version: str | None = Field(
        None,
        description="Current firmware version",
        examples=["6.5.55", "7.0.23"],
    )
    link_speed: int | None = Field(
        None,
        description="Link speed in Mbps",
        examples=[1000, 10000, 100],
    )
    connection_type: str | None = Field(
        None,
        description="Connection type",
        examples=["wired", "wireless"],
    )
    uptime: int | None = Field(
        None,
        ge=0,
        description="Device uptime in seconds",
        examples=[86400, 3600, 0],
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
                    "mac": "00:11:22:33:44:55",
                    "hostname": "unifi-switch-01",
                    "type": "usw",
                    "model": "US-24-250W",
                    "adopted": True,
                    "state": "connected",
                    "ip": "192.168.1.100",
                    "firmware_version": "6.5.55",
                    "link_speed": 1000,
                    "connection_type": "wired",
                    "uptime": 86400,
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
