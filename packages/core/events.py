"""Domain events for cross-service communication.

Defines immutable dataclasses that describe key lifecycle events. These
events are emitted by core use cases and delivered through adapter layers
such as Redis Streams publishers.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class DocumentIngestedEvent:
    """Event emitted when a document completes the ingestion pipeline."""

    doc_id: UUID
    source_url: str
    chunk_count: int


__all__ = ["DocumentIngestedEvent"]
