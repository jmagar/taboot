"""Pydantic models for documents, metadata, and query results."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class DocumentMetadata(BaseModel):
    """Source-specific metadata for documents.

    Attributes:
        source_type: Type of data source (firecrawl, github, reddit, gmail, elasticsearch)
        source_url: Original URL or reference to the source
        timestamp: Document creation or last update timestamp
        extra: Additional source-specific fields (e.g., GitHub repo info, Reddit scores)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_type": "github",
                "source_url": "https://github.com/owner/repo/issues/123",
                "timestamp": "2024-09-30T14:23:45.123Z",
                "extra": {
                    "repo_owner": "owner",
                    "repo_name": "repo",
                    "issue_number": 123,
                    "author": "username",
                },
            }
        }
    )

    source_type: Literal[
        "firecrawl", "github", "reddit", "gmail",
        "elasticsearch", "claude_code", "codex"
    ]
    source_url: str
    timestamp: datetime
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        """Serialize datetime to ISO 8601 format with timezone."""
        return dt.isoformat()


class Document(BaseModel):
    """Core document model representing ingested content.

    Attributes:
        doc_id: Unique document identifier
        title: Document title
        content: Full text content
        content_hash: SHA-256 hash of normalized content for deduplication
        metadata: Source-specific metadata
        embedding: Optional embedding vector (1024-dim for Qwen3-Embedding-0.6B)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "doc_id": "github_owner_repo_issue_123",
                "title": "Authentication bug in login flow",
                "content": "Full issue body text...",
                "content_hash": "abc123...",
                "metadata": {
                    "source_type": "github",
                    "source_url": "https://github.com/owner/repo/issues/123",
                    "timestamp": "2024-09-30T14:23:45.123Z",
                    "extra": {},
                },
                "embedding": None,
            }
        }
    )

    doc_id: str
    title: str
    content: str
    content_hash: str
    metadata: DocumentMetadata
    embedding: list[float] | None = None

    def __hash__(self) -> int:
        """Hash based on doc_id and content_hash for efficient comparison."""
        return hash((self.doc_id, self.content_hash))

    def __eq__(self, other: object) -> bool:
        """Equality based on doc_id and content_hash.

        Two documents are equal if they have the same doc_id and content_hash.
        This allows efficient deduplication checks.
        """
        if not isinstance(other, Document):
            return NotImplemented
        return self.doc_id == other.doc_id and self.content_hash == other.content_hash


class SourceAttribution(BaseModel):
    """Source reference for query results.

    Attributes:
        doc_id: Unique document identifier
        source_type: Type of data source
        title: Document title
        url: Source URL
        score: Relevance score (0.0 to 1.0)
        snippet: Short excerpt from the document (100-200 chars)
        timestamp: Document timestamp
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "doc_id": "gmail_msg_abc123",
                "source_type": "gmail",
                "title": "Re: Authentication bug",
                "url": "https://mail.google.com/mail/u/0/#inbox/abc123",
                "score": 0.92,
                "snippet": "...relevant excerpt from email...",
                "timestamp": "2024-09-15T10:30:00Z",
            }
        }
    )

    doc_id: str
    source_type: Literal[
        "firecrawl", "github", "reddit", "gmail",
        "elasticsearch", "claude_code", "codex"
    ]
    title: str
    url: str
    score: float = Field(ge=0.0, le=1.0, description="Relevance score between 0.0 and 1.0")
    snippet: str
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        """Serialize datetime to ISO 8601 format with timezone."""
        return dt.isoformat()


class QueryResult(BaseModel):
    """Query response model with answer and sources.

    Attributes:
        answer: Synthesized answer text with inline citations [1][2]
        sources: List of source attributions with metadata
        query_time_ms: Total query time in milliseconds
        retrieved_docs: Number of documents retrieved from vector search
        reranked_docs: Number of documents after reranking
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": (
                    "The authentication bug was fixed in PR #456 [1]. "
                    "The issue was related to session timeout handling [2]."
                ),
                "sources": [
                    {
                        "doc_id": "github_owner_repo_pr_456",
                        "source_type": "github",
                        "title": "Fix: Authentication session timeout",
                        "url": "https://github.com/owner/repo/pull/456",
                        "score": 0.95,
                        "snippet": "This PR fixes the authentication session timeout bug...",
                        "timestamp": "2024-09-20T08:15:00Z",
                    }
                ],
                "query_time_ms": 245,
                "retrieved_docs": 20,
                "reranked_docs": 5,
            }
        }
    )

    answer: str
    sources: list[SourceAttribution]
    query_time_ms: int = Field(ge=0, description="Query time in milliseconds")
    retrieved_docs: int = Field(ge=0, description="Number of documents retrieved")
    reranked_docs: int = Field(ge=0, description="Number of documents after reranking")
