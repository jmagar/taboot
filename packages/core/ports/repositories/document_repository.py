"""Document repository port definition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from packages.schemas.models import Document, ExtractionState, SourceType


class DocumentRepository(ABC):
    """Repository abstraction for document persistence operations."""

    @abstractmethod
    async def find_by_id(self, doc_id: UUID) -> Document | None:
        """Retrieve a single document by identifier."""

    @abstractmethod
    async def find_pending_extraction(self, limit: int | None = None) -> list[Document]:
        """Return documents pending extraction processing."""

    @abstractmethod
    async def list_documents(
        self,
        *,
        limit: int,
        offset: int,
        source_type: SourceType | None = None,
        extraction_state: ExtractionState | None = None,
    ) -> list[Document]:
        """List documents with optional filters."""

    @abstractmethod
    async def count_documents(
        self,
        *,
        source_type: SourceType | None = None,
        extraction_state: ExtractionState | None = None,
    ) -> int:
        """Count documents with optional filters."""

    @abstractmethod
    async def get_document_content(self, doc_id: UUID) -> str:
        """Fetch raw document content."""

    @abstractmethod
    async def save(self, document: Document) -> None:
        """Persist updates to a document record."""


__all__ = ["DocumentRepository"]
