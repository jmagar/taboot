"""Ports for publishing domain events to external transports."""

from __future__ import annotations

from abc import ABC, abstractmethod

from packages.core.events import DocumentIngestedEvent


class DocumentEventPublisher(ABC):
    """Publisher interface for document lifecycle events."""

    @abstractmethod
    async def publish_document_ingested(self, event: DocumentIngestedEvent) -> None:
        """Emit a document ingested event to downstream subscribers."""


__all__ = ["DocumentEventPublisher"]
