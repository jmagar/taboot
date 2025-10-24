"""Services for dispatching document ingestion events."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, Protocol

from packages.core.events import DocumentIngestedEvent
from packages.schemas.models import Document


class SupportsDocumentEventPublish(Protocol):
    async def publish_document_ingested(self, event: DocumentIngestedEvent) -> None: ...


class DocumentEventDispatcher:
    """Dispatches ingestion events through the configured publisher."""

    def __init__(
        self,
        publisher: SupportsDocumentEventPublish | None,
        *,
        enabled: bool,
    ) -> None:
        self._publisher = publisher
        self._enabled = enabled

    def dispatch_document_ingested(self, document: Document, *, chunk_count: int) -> None:
        """Emit a DocumentIngestedEvent if feature flag is enabled."""

        if not self._enabled or self._publisher is None:
            return

        event = DocumentIngestedEvent(
            doc_id=document.doc_id,
            source_url=document.source_url,
            chunk_count=chunk_count,
        )

        self._run_async(self._publisher.publish_document_ingested(event))

    @staticmethod
    def _run_async(coro: Coroutine[Any, Any, None]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(coro)
        else:
            loop.create_task(coro)


__all__ = ["DocumentEventDispatcher"]
