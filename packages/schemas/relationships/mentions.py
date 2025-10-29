"""MentionsRelationship schema (Document → Entity)."""

from uuid import UUID

from pydantic import Field

from packages.schemas.relationships.base import BaseRelationship


class MentionsRelationship(BaseRelationship):
    """MENTIONS relationship from Document to Entity.

    Represents a mention of an entity within a document chunk.

    Direction: (:Document)-[:MENTIONS]->(:Entity)

    Examples:
        >>> from datetime import datetime, UTC
        >>> from uuid import uuid4
        >>> rel = MentionsRelationship(
        ...     span="John Doe works at Acme Corp",
        ...     section="Introduction",
        ...     chunk_id=uuid4(),
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     source="job_12345",
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.span
        'John Doe works at Acme Corp'
    """

    span: str = Field(
        ...,
        min_length=1,
        description="Text snippet where entity is mentioned",
        examples=["John Doe works at Acme Corp", "deployed to production"],
    )
    section: str = Field(
        ...,
        min_length=1,
        description="Document section containing the mention",
        examples=["Introduction", "Methods", "Conclusion"],
    )
    chunk_id: UUID = Field(
        ...,
        description="ID of the chunk containing this mention",
    )
