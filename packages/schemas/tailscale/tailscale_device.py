"""TailscaleDevice entity schema.

Represents Tailscale devices/nodes in a tailnet mesh network.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TailscaleDevice(BaseModel):
    """TailscaleDevice entity representing a node in a Tailscale tailnet.

    Extracted from Tailscale API showing device configuration, IP addresses,
    routing settings, and security configuration.

    Examples:
        >>> from datetime import datetime, UTC
        >>> device = TailscaleDevice(
        ...     device_id="ts-device-123",
        ...     hostname="gateway.example.com",
        ...     long_domain="gateway.example.com",
        ...     os="linux",
        ...     ipv4_address="100.64.1.5",
        ...     ipv6_address="fd7a:115c:a1e0::1",
        ...     is_exit_node=True,
        ...     ssh_enabled=True,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="tailscale_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> device.hostname
        'gateway.example.com'
    """

    # Identity fields
    device_id: str = Field(
        ...,
        min_length=1,
        description="Unique Tailscale device ID",
        examples=["ts-device-123", "kVxxxxxxxxxxxxxxxx"],
    )
    hostname: str = Field(
        ...,
        min_length=1,
        description="Device hostname",
        examples=["gateway.example.com", "server.tailnet.ts.net"],
    )
    long_domain: str | None = Field(
        None,
        description="Fully qualified domain name reported by Tailscale (outside MagicDNS)",
        examples=["gateway.example.com", "workstation.corp.example.com"],
    )
    os: str = Field(
        ...,
        min_length=1,
        description="Operating system of the device",
        examples=["linux", "darwin", "windows", "ios", "android"],
    )

    # Network configuration (optional)
    ipv4_address: str | None = Field(
        None,
        description="Tailscale IPv4 address (100.x range)",
        examples=["100.64.1.5", "100.100.100.1"],
    )
    ipv6_address: str | None = Field(
        None,
        description="Tailscale IPv6 address",
        examples=["fd7a:115c:a1e0::1", "fd7a:115c:a1e0:ab12:4843:cd96:6258:1234"],
    )
    endpoints: list[str] | None = Field(
        None,
        description="List of public endpoint addresses (IP:port)",
        examples=[["192.168.1.100:41641", "203.0.113.50:41641"]],
    )

    # Security and routing configuration (optional)
    key_expiry: datetime | None = Field(
        None,
        description="When the device's authentication key expires",
    )
    is_exit_node: bool | None = Field(
        None,
        description="Whether this device acts as an exit node",
    )
    subnet_routes: list[str] | None = Field(
        None,
        description="Subnet routes advertised by this device",
        examples=[["10.0.0.0/24", "10.1.0.0/24"]],
    )
    ssh_enabled: bool | None = Field(
        None,
        description="Whether Tailscale SSH is enabled on this device",
    )
    tailnet_dns_name: str | None = Field(
        None,
        description="MagicDNS hostname within the tailnet (e.g., device.tailnet.ts.net)",
        examples=["gateway.tailnet-abc.ts.net"],
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
        description="When the device was last seen/updated in Tailscale",
    )

    # Extraction metadata (required on ALL entities)
    extraction_tier: Literal["A", "B", "C"] = Field(
        ...,
        description="Extraction tier: A (deterministic), B (spaCy), C (LLM)",
    )
    extraction_method: str = Field(
        ...,
        description="Method used for extraction",
        examples=["tailscale_api", "regex", "spacy_ner"],
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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "device_id": "ts-device-456",
                    "hostname": "gateway.example.com",
                    "long_domain": "gateway.example.com",
                    "os": "linux",
                    "ipv4_address": "100.64.1.5",
                    "ipv6_address": "fd7a:115c:a1e0::1",
                    "endpoints": ["192.168.1.100:41641", "203.0.113.50:41641"],
                    "key_expiry": "2024-12-31T23:59:59Z",
                    "is_exit_node": True,
                    "subnet_routes": ["10.0.0.0/24", "10.1.0.0/24"],
                    "ssh_enabled": True,
                    "tailnet_dns_name": "gateway.tailnet-abc.ts.net",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-15T09:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "tailscale_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
