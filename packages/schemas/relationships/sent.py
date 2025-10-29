"""SentRelationship schema (Person → Email)."""

from datetime import datetime

from pydantic import Field

from packages.schemas.relationships.base import BaseRelationship


class SentRelationship(BaseRelationship):
    """SENT relationship from Person to Email.

    Represents email authorship.

    Direction: (:Person)-[:SENT]->(:Email)

    Examples:
        >>> from datetime import datetime, UTC
        >>> rel = SentRelationship(
        ...     sent_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     source="gmail_reader",
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.sent_at.year
        2024
    """

    sent_at: datetime = Field(
        ...,
        description="When the email was sent",
    )
