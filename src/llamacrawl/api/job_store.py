"""Persistence utilities for Firecrawl job metadata."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from llamacrawl.api.models import (
    FirecrawlJobProgress,
    FirecrawlJobRecord,
    FirecrawlJobStatus,
    FirecrawlJobSummary,
)
from llamacrawl.storage.redis import RedisClient


class FirecrawlJobStore:
    """Redis-backed repository for tracking Firecrawl ingestion jobs."""

    _JOB_KEY_PREFIX = "firecrawl:jobs"

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis_client = redis_client

    def _job_key(self, job_id: str) -> str:
        return f"{self._JOB_KEY_PREFIX}:{job_id}"

    def upsert(self, record: FirecrawlJobRecord) -> None:
        """Persist a job record."""
        key = self._job_key(record.job_id)
        self._redis_client.client.set(key, record.model_dump_json())

    def get(self, job_id: str) -> FirecrawlJobRecord | None:
        """Retrieve a job record by identifier."""
        key = self._job_key(job_id)
        payload = self._redis_client.client.get(key)
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        return FirecrawlJobRecord.model_validate_json(payload)

    def update_status(
        self,
        job_id: str,
        status: FirecrawlJobStatus,
        *,
        error: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        summary: FirecrawlJobSummary | None = None,
    ) -> FirecrawlJobRecord | None:
        """Update job status and optional metadata."""
        record = self.get(job_id)
        if record is None:
            return None

        record.status = status
        record.updated_at = datetime.now(UTC)
        if started_at is not None:
            record.started_at = started_at
        if completed_at is not None:
            record.completed_at = completed_at
        if summary is not None:
            record.summary = summary
        if error is not None:
            record.error = error

        self.upsert(record)
        return record

    def update_progress(
        self,
        job_id: str,
        *,
        completed: int,
        total: int | None,
        status: str,
    ) -> FirecrawlJobRecord | None:
        """Store incremental progress metrics for a job."""
        record = self.get(job_id)
        if record is None:
            return None

        record.progress = FirecrawlJobProgress(
            completed=completed,
            total=total,
            status=status,
        )
        record.updated_at = datetime.now(UTC)
        self.upsert(record)
        return record

    def update_request_payload(self, job_id: str, payload: dict[str, Any]) -> None:
        """Persist the original request payload for auditing."""
        record = self.get(job_id)
        if record is None:
            return
        record.request_payload = payload
        record.updated_at = datetime.now(UTC)
        self.upsert(record)
