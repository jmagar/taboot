"""InThreadRelationship schema (Email → Thread)."""

from packages.schemas.relationships.base import BaseRelationship


class InThreadRelationship(BaseRelationship):
    """IN_THREAD relationship from Email to Thread.

    Represents email thread membership.

    Direction: (:Email)-[:IN_THREAD]->(:Thread)

    Examples:
        >>> from datetime import datetime, UTC
        >>> rel = InThreadRelationship(
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     source="gmail_reader",
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.confidence
        1.0
    """

    # No additional fields beyond BaseRelationship
    pass
