"""TrafficRule entity schema.

Represents a Unifi traffic shaping/QoS rule.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TrafficRule(BaseModel):
    """TrafficRule entity representing a traffic shaping/QoS policy.

    Extracted from Unifi Controller API: /v2/api/site/{site}/trafficrules

    Examples:
        >>> from datetime import datetime, UTC
        >>> rule = TrafficRule(
        ...     rule_id="5f9c1234abcd5678ef123456",
        ...     name="Limit Gaming",
        ...     enabled=True,
        ...     action="limit",
        ...     bandwidth_limit={"download_kbps": 10000, "upload_kbps": 5000},
        ...     matching_target="ip",
        ...     ip_addresses=["192.168.1.100"],
        ...     domains=["game-server.com"],
        ...     schedule="weekdays",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="unifi_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> rule.name
        'Limit Gaming'
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
        examples=["Limit Gaming", "Prioritize Video", "Throttle Downloads"],
    )
    enabled: bool = Field(
        ...,
        description="Whether the rule is enabled",
    )

    # Traffic shaping configuration
    action: str = Field(
        ...,
        description="Action to take (limit, prioritize, block)",
        examples=["limit", "prioritize", "block"],
    )
    bandwidth_limit: dict[str, Any] | None = Field(
        None,
        description="Bandwidth limits (download_kbps, upload_kbps)",
        examples=[{"download_kbps": 10000, "upload_kbps": 5000}],
    )
    matching_target: str | None = Field(
        None,
        description="What to match against (ip, domain, application)",
        examples=["ip", "domain", "application"],
    )
    ip_addresses: list[str] | None = Field(
        None,
        description="IP addresses to match",
        examples=[["192.168.1.100", "10.0.0.50"]],
    )
    domains: list[str] | None = Field(
        None,
        description="Domain names to match",
        examples=[["game-server.com", "video-stream.net"]],
    )
    schedule: str | None = Field(
        None,
        description="Time schedule for rule",
        examples=["weekdays", "weekends", "always"],
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
                    "name": "Limit Gaming",
                    "enabled": True,
                    "action": "limit",
                    "bandwidth_limit": {"download_kbps": 10000, "upload_kbps": 5000},
                    "matching_target": "ip",
                    "ip_addresses": ["192.168.1.100"],
                    "domains": ["game-server.com"],
                    "schedule": "weekdays",
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
