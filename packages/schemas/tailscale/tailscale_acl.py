"""TailscaleACL entity schema.

Represents Tailscale Access Control List rules.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TailscaleACL(BaseModel):
    """TailscaleACL entity representing an access control rule in Tailscale.

    Extracted from Tailscale ACL configuration showing firewall rules,
    source/destination tags, and port restrictions.

    Examples:
        >>> from datetime import datetime, UTC
        >>> acl = TailscaleACL(
        ...     rule_id="acl-rule-123",
        ...     action="accept",
        ...     source_tags=["tag:production"],
        ...     destination_tags=["tag:database"],
        ...     ports=["3306", "5432"],
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="tailscale_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> acl.action
        'accept'
    """

    # Identity fields
    rule_id: str = Field(
        ...,
        min_length=1,
        description="Unique ACL rule identifier",
        examples=["acl-rule-123", "rule-abc"],
    )
    action: str = Field(
        ...,
        min_length=1,
        description="ACL action (accept, deny)",
        examples=["accept", "deny"],
    )

    # ACL configuration
    source_tags: list[str] = Field(
        ...,
        description="List of source tags for this rule",
        examples=[["tag:production", "tag:staging"], ["tag:admin"]],
    )
    destination_tags: list[str] = Field(
        ...,
        description="List of destination tags for this rule",
        examples=[["tag:database", "tag:api"], ["tag:web"]],
    )
    ports: list[str] | None = Field(
        None,
        description="List of allowed ports (optional, empty means all ports)",
        examples=[["3306", "5432"], ["80", "443"], ["22"]],
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
        description="When the ACL rule was last updated in Tailscale",
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
                    "rule_id": "acl-rule-123",
                    "action": "accept",
                    "source_tags": ["tag:production"],
                    "destination_tags": ["tag:database"],
                    "ports": ["3306", "5432"],
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
