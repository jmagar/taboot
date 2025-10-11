"""Pydantic models for the LlamaCrawl FastAPI service."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_serializer


class FirecrawlMode(str, Enum):
    """Supported Firecrawl ingestion modes."""

    SCRAPE = "scrape"
    CRAWL = "crawl"
    MAP = "map"
    EXTRACT = "extract"


class FirecrawlJobStatus(str, Enum):
    """High-level lifecycle states for Firecrawl ingestion jobs."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FirecrawlJobProgress(BaseModel):
    """Incremental progress information for long-running Firecrawl crawls."""

    completed: int = Field(default=0, ge=0)
    total: int | None = Field(default=None, ge=0)
    status: str = Field(default="queued")


class FirecrawlJobSummary(BaseModel):
    """Ingestion pipeline summary results."""

    total: int = 0
    processed: int = 0
    deduplicated: int = 0
    failed: int = 0
    duration_seconds: float = 0.0
    success_rate: float | None = None


class FirecrawlJobRecord(BaseModel):
    """Canonical representation of a tracked Firecrawl job."""

    job_id: str
    url: HttpUrl
    mode: FirecrawlMode = FirecrawlMode.CRAWL
    status: FirecrawlJobStatus = FirecrawlJobStatus.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: FirecrawlJobProgress | None = None
    summary: FirecrawlJobSummary | None = None
    error: str | None = None
    request_payload: dict[str, Any] = Field(default_factory=dict)

    @field_serializer("created_at", "updated_at", "started_at", "completed_at")
    def _serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetimes to ISO format with timezone awareness."""
        if value is None:
            return None
        return value.astimezone(UTC).isoformat()


class FirecrawlJobCreateRequest(BaseModel):
    """Payload for requesting a new Firecrawl ingestion job."""

    url: HttpUrl
    mode: FirecrawlMode = FirecrawlMode.CRAWL
    limit: int | None = Field(default=None, ge=1, le=10_000)
    max_depth: int | None = Field(default=None, ge=1, le=10)
    formats: list[str] | None = None
    prompt: str | None = None
    schema: dict[str, Any] | None = None
    include_paths: list[str] | None = None
    exclude_paths: list[str] | None = None
    location_country: str | None = Field(default=None, max_length=2)
    location_languages: list[str] | None = None
    filter_non_english_metadata: bool | None = None


class FirecrawlJobCreateResponse(BaseModel):
    """Response returned when a crawl job is enqueued."""

    job_id: str
    status: FirecrawlJobStatus


class FirecrawlJobDetailResponse(BaseModel):
    """Detailed representation of a Firecrawl job."""

    job_id: str
    url: HttpUrl
    mode: FirecrawlMode
    status: FirecrawlJobStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: FirecrawlJobProgress | None = None
    summary: FirecrawlJobSummary | None = None
    error: str | None = None
    request_payload: dict[str, Any]

    @classmethod
    def from_record(cls, record: FirecrawlJobRecord) -> FirecrawlJobDetailResponse:
        """Build a detail response from a stored record."""
        return cls.model_validate(record.model_dump())
