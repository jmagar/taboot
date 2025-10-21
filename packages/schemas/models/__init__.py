"""Pydantic data models for Taboot platform.

Defines all entity models with validation rules per data-model.md.
Includes relational entities (Document, Chunk, IngestionJob, ExtractionJob, ExtractionWindow)
and graph node models (Service, Host, IP, Proxy, Endpoint).
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ========== Enums ==========


class SourceType(str, Enum):
    """Source types for document ingestion."""

    WEB = "web"
    GITHUB = "github"
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    GMAIL = "gmail"
    ELASTICSEARCH = "elasticsearch"
    DOCKER_COMPOSE = "docker_compose"
    SWAG = "swag"
    TAILSCALE = "tailscale"
    UNIFI = "unifi"
    AI_SESSION = "ai_session"


class ExtractionState(str, Enum):
    """Extraction states for documents and jobs."""

    PENDING = "pending"
    TIER_A_DONE = "tier_a_done"
    TIER_B_DONE = "tier_b_done"
    TIER_C_DONE = "tier_c_done"
    COMPLETED = "completed"
    FAILED = "failed"


class JobState(str, Enum):
    """Job states for ingestion and extraction jobs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class HttpMethod(str, Enum):
    """HTTP methods for endpoints."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    ALL = "*"


class IPType(str, Enum):
    """IP address types."""

    V4 = "v4"
    V6 = "v6"


class IPAllocation(str, Enum):
    """IP allocation methods."""

    STATIC = "static"
    DHCP = "dhcp"
    UNKNOWN = "unknown"


class ProxyType(str, Enum):
    """Reverse proxy types."""

    NGINX = "nginx"
    TRAEFIK = "traefik"
    HAPROXY = "haproxy"
    SWAG = "swag"
    OTHER = "other"


class Protocol(str, Enum):
    """Network protocols."""

    TCP = "tcp"
    UDP = "udp"


class ExtractionTier(str, Enum):
    """Extraction tier identifiers."""

    A = "A"
    B = "B"
    C = "C"


# ========== Document Models ==========


class Document(BaseModel):
    """Document entity representing an ingested document.

    Per data-model.md: Represents an ingested document from any source.
    Stored in PostgreSQL with extraction state tracking.
    """

    doc_id: UUID = Field(..., description="Document UUID (primary key)")
    source_url: str = Field(
        ..., min_length=1, max_length=2048, description="Original source URL or identifier"
    )
    source_type: SourceType = Field(..., description="Source type enum")
    content_hash: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 hex digest of content"
    )
    ingested_at: datetime = Field(..., description="UTC timestamp of ingestion")
    extraction_state: ExtractionState = Field(..., description="Current extraction state")
    extraction_version: str | None = Field(
        default=None, max_length=64, description="Extractor version tag (semver)"
    )
    updated_at: datetime = Field(..., description="UTC timestamp of last update")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Arbitrary key-value pairs"
    )

    @field_validator("content_hash")
    @classmethod
    def validate_content_hash_hex(cls, v: str) -> str:
        """Validate that content_hash is a valid hex string.

        Args:
            v: The content hash value.

        Returns:
            str: The validated content hash.

        Raises:
            ValueError: If content_hash is not a valid hex string.
        """
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("content_hash must be a valid hexadecimal string")
        return v.lower()


class Chunk(BaseModel):
    """Chunk entity representing a semantic chunk with embeddings.

    Per data-model.md: Represents a semantic chunk of a document.
    Stored in Qdrant vector database with metadata for filtering.
    """

    chunk_id: UUID = Field(..., description="Chunk UUID (Qdrant point ID)")
    doc_id: UUID = Field(..., description="Foreign key to Document")
    content: str = Field(
        ..., min_length=1, max_length=4096, description="Chunk text content"
    )
    section: str | None = Field(
        default=None, max_length=512, description="Heading/path context"
    )
    position: int = Field(..., ge=0, description="Offset in document (0-indexed)")
    token_count: int = Field(..., ge=1, le=512, description="Token count in chunk")

    # Qdrant metadata (for filtering)
    source_url: str = Field(..., description="Copied from Document")
    source_type: SourceType = Field(..., description="Copied from Document")
    ingested_at: int = Field(..., description="Unix timestamp from Document")
    tags: list[str] | None = Field(
        default=None, description="Optional tags for filtering"
    )


class IngestionJob(BaseModel):
    """Ingestion job entity tracking ingestion tasks.

    Per data-model.md: Represents an ingestion task with state transitions.
    """

    job_id: UUID = Field(..., description="Job UUID (primary key)")
    source_type: SourceType = Field(..., description="Source type enum")
    source_target: str = Field(
        ..., min_length=1, max_length=2048, description="URL, repo name, file path"
    )
    state: JobState = Field(..., description="Job state enum")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: datetime | None = Field(default=None, description="Job start timestamp")
    completed_at: datetime | None = Field(
        default=None, description="Job completion timestamp"
    )
    pages_processed: int = Field(..., ge=0, description="Count of pages/documents ingested")
    chunks_created: int = Field(..., ge=0, description="Count of chunks created")
    errors: list[dict[str, Any]] | None = Field(
        default=None, description="Array of error objects"
    )


class ExtractionWindow(BaseModel):
    """Extraction window entity for Tier C LLM processing.

    Per data-model.md: Represents a micro-window processed by Tier C.
    """

    window_id: UUID = Field(..., description="Window UUID (primary key)")
    doc_id: UUID = Field(..., description="Foreign key to Document")
    content: str = Field(
        ..., min_length=1, max_length=2048, description="Text content (≤512 tokens)"
    )
    tier: ExtractionTier = Field(..., description="Extraction tier (A, B, C)")
    triples_generated: int = Field(..., ge=0, description="Count of extracted triples")
    llm_latency_ms: int | None = Field(
        default=None, ge=0, description="LLM inference time (tier C only)"
    )
    cache_hit: bool | None = Field(
        default=None, description="LLM response cached (tier C only)"
    )
    processed_at: datetime = Field(..., description="Processing timestamp")
    extraction_version: str | None = Field(
        default=None, max_length=64, description="Extractor version tag"
    )


class ExtractionJob(BaseModel):
    """Extraction job entity tracking extraction tasks.

    Per data-model.md: Represents an extraction task for a document with tier progression.
    """

    job_id: UUID = Field(..., description="Job UUID (primary key)")
    doc_id: UUID = Field(..., description="Foreign key to Document")
    state: ExtractionState = Field(..., description="Extraction state enum")
    tier_a_triples: int = Field(..., ge=0, description="Triples from Tier A")
    tier_b_windows: int = Field(..., ge=0, description="Windows selected by Tier B")
    tier_c_triples: int = Field(..., ge=0, description="Triples from Tier C")
    started_at: datetime | None = Field(default=None, description="Job start timestamp")
    completed_at: datetime | None = Field(
        default=None, description="Job completion timestamp"
    )
    retry_count: int = Field(..., ge=0, le=3, description="Retry attempts (max 3)")
    errors: dict[str, Any] | None = Field(default=None, description="Error log")


# ========== Graph Node Models ==========


class Service(BaseModel):
    """Service node entity (Neo4j).

    Per data-model.md: Represents a software service/application.
    """

    name: str = Field(..., min_length=1, max_length=256, description="Service name (unique)")
    description: str | None = Field(default=None, max_length=2048, description="Description")
    image: str | None = Field(
        default=None, max_length=512, description="Docker image or binary path"
    )
    version: str | None = Field(default=None, max_length=64, description="Version or tag")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Arbitrary metadata"
    )
    created_at: datetime = Field(..., description="Node creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    extraction_version: str | None = Field(
        default=None, max_length=64, description="Extractor version"
    )


class Host(BaseModel):
    """Host node entity (Neo4j).

    Per data-model.md: Represents a physical or virtual machine.
    """

    hostname: str = Field(..., min_length=1, max_length=256, description="Hostname (unique)")
    ip_addresses: list[str] | None = Field(
        default=None, description="Array of IP addresses"
    )
    os: str | None = Field(default=None, max_length=128, description="Operating system")
    location: str | None = Field(default=None, max_length=256, description="Location")
    metadata: dict[str, Any] | None = Field(default=None, description="Arbitrary metadata")
    created_at: datetime = Field(..., description="Node creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    extraction_version: str | None = Field(
        default=None, max_length=64, description="Extractor version"
    )


class IP(BaseModel):
    """IP address node entity (Neo4j).

    Per data-model.md: Represents an IP address.
    """

    addr: str = Field(
        ..., min_length=1, max_length=64, description="IP address (dotted notation or CIDR)"
    )
    ip_type: IPType = Field(..., description="IPv4 or IPv6")
    allocation: IPAllocation = Field(..., description="Allocation method")
    metadata: dict[str, Any] | None = Field(default=None, description="Arbitrary metadata")
    created_at: datetime = Field(..., description="Node creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    extraction_version: str | None = Field(
        default=None, max_length=64, description="Extractor version"
    )


class Proxy(BaseModel):
    """Proxy node entity (Neo4j).

    Per data-model.md: Represents a reverse proxy or gateway.
    """

    name: str = Field(..., min_length=1, max_length=256, description="Proxy name (unique)")
    proxy_type: ProxyType = Field(..., description="Proxy type enum")
    config_path: str | None = Field(
        default=None, max_length=512, description="Config file path"
    )
    metadata: dict[str, Any] | None = Field(default=None, description="Arbitrary metadata")
    created_at: datetime = Field(..., description="Node creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    extraction_version: str | None = Field(
        default=None, max_length=64, description="Extractor version"
    )


class Endpoint(BaseModel):
    """Endpoint node entity (Neo4j).

    Per data-model.md: Represents an HTTP/API endpoint.
    Composite unique index on (service, method, path).
    """

    service: str = Field(..., max_length=256, description="Foreign key to Service.name")
    method: HttpMethod = Field(..., description="HTTP method enum")
    path: str = Field(..., min_length=1, max_length=512, description="URL path pattern")
    auth: str | None = Field(
        default=None, max_length=128, description="Authentication method"
    )
    rate_limit: int | None = Field(
        default=None, ge=0, description="Requests per minute"
    )
    metadata: dict[str, Any] | None = Field(default=None, description="Arbitrary metadata")
    created_at: datetime = Field(..., description="Node creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    extraction_version: str | None = Field(
        default=None, max_length=64, description="Extractor version"
    )


# ========== Export all models ==========

__all__ = [
    # Enums
    "SourceType",
    "ExtractionState",
    "JobState",
    "HttpMethod",
    "IPType",
    "IPAllocation",
    "ProxyType",
    "Protocol",
    "ExtractionTier",
    # Document models
    "Document",
    "Chunk",
    "IngestionJob",
    "ExtractionWindow",
    "ExtractionJob",
    # Graph node models
    "Service",
    "Host",
    "IP",
    "Proxy",
    "Endpoint",
]
