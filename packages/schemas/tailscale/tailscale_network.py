"""TailscaleNetwork entity schema.

Represents Tailscale network configuration and subnets.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TailscaleNetwork(BaseModel):
    """TailscaleNetwork entity representing a network segment in Tailscale.

    Extracted from Tailscale API showing network configuration, CIDR ranges,
    and DNS settings.

    Examples:
        >>> from datetime import datetime, UTC
        >>> network = TailscaleNetwork(
        ...     network_id="net-123",
        ...     name="main-network",
        ...     cidr="100.64.0.0/10",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="tailscale_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> network.cidr
        '100.64.0.0/10'
    """

    # Identity fields
    network_id: str = Field(
        ...,
        min_length=1,
        description="Unique network identifier",
        examples=["net-123", "network-abc"],
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Network name",
        examples=["main-network", "production", "staging"],
    )
    cidr: str = Field(
        ...,
        min_length=1,
        description="Network CIDR range",
        examples=["100.64.0.0/10", "10.0.0.0/8"],
    )

    # DNS configuration (optional)
    global_nameservers: list[str] | None = Field(
        None,
        description="List of global DNS nameservers",
        examples=[["8.8.8.8", "1.1.1.1"]],
    )
    search_domains: list[str] | None = Field(
        None,
        description="DNS search domains",
        examples=[["example.com", "internal.local"]],
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
        description="When the network was last updated in Tailscale",
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
                    "network_id": "net-123",
                    "name": "main-network",
                    "cidr": "100.64.0.0/10",
                    "global_nameservers": ["8.8.8.8", "1.1.1.1"],
                    "search_domains": ["example.com", "internal.local"],
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
