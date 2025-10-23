"""PostgreSQL implementation of ingestion job store.

Implements persistent job storage and querying for ingestion pipeline.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from packages.schemas.models import IngestionJob, JobState, SourceType

logger = logging.getLogger(__name__)


class PostgresJobStore:
    """PostgreSQL implementation of job store protocol.

    Handles IngestionJob CRUD operations with atomic state transitions.
    """

    def __init__(self, connection: Any) -> None:
        """Initialize with PostgreSQL connection.

        Args:
            connection: psycopg2 connection object.
        """
        self.conn = connection
        logger.info("Initialized PostgresJobStore")

    def create(self, job: IngestionJob) -> None:
        """Create ingestion job record.

        Args:
            job: IngestionJob model to persist.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingestion_jobs (
                    job_id, source_type, source_target, state,
                    created_at, started_at, completed_at,
                    pages_processed, chunks_created, errors
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(job.job_id),
                    job.source_type.value,
                    job.source_target,
                    job.state.value,
                    job.created_at,
                    job.started_at,
                    job.completed_at,
                    job.pages_processed,
                    job.chunks_created,
                    Json(job.errors) if job.errors else None,
                ),
            )
        self.conn.commit()
        logger.debug(f"Created ingestion job {job.job_id}")

    def get_by_id(self, job_id: UUID) -> IngestionJob | None:
        """Get job by ID.

        Args:
            job_id: Job UUID.

        Returns:
            IngestionJob if found, None otherwise.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM ingestion_jobs WHERE job_id = %s",
                (str(job_id),),
            )
            row = cur.fetchone()

        if not row:
            return None

        return IngestionJob(
            job_id=UUID(row["job_id"]),
            source_type=SourceType(row["source_type"]),
            source_target=row["source_target"],
            state=JobState(row["state"]),
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            pages_processed=row["pages_processed"],
            chunks_created=row["chunks_created"],
            errors=row["errors"],
        )

    def update(self, job: IngestionJob) -> None:
        """Update job state and metrics.

        Args:
            job: Job with updated fields.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ingestion_jobs SET
                    state = %s,
                    started_at = %s,
                    completed_at = %s,
                    pages_processed = %s,
                    chunks_created = %s,
                    errors = %s
                WHERE job_id = %s
                """,
                (
                    job.state.value,
                    job.started_at,
                    job.completed_at,
                    job.pages_processed,
                    job.chunks_created,
                    Json(job.errors) if job.errors else None,
                    str(job.job_id),
                ),
            )
        self.conn.commit()
        logger.debug(f"Updated ingestion job {job.job_id}")


__all__ = ["PostgresJobStore"]
