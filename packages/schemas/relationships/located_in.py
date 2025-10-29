"""LocatedInRelationship schema (Entity → Place)."""

from packages.schemas.relationships.base import BaseRelationship


class LocatedInRelationship(BaseRelationship):
    """LOCATED_IN relationship from any entity to Place.

    Represents physical or logical location.

    Direction: (:Entity)-[:LOCATED_IN]->(:Place)

    Examples:
        >>> from datetime import datetime, UTC
        >>> rel = LocatedInRelationship(
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     source="tailscale_reader",
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.confidence
        1.0
    """

    # No additional fields beyond BaseRelationship
    pass
