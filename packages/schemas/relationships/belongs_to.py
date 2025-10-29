"""BelongsToRelationship schema (File → Space/Repository)."""

from packages.schemas.relationships.base import BaseRelationship


class BelongsToRelationship(BaseRelationship):
    """BELONGS_TO relationship from File to parent container.

    Represents file membership in a repository or space.

    Direction: (:File)-[:BELONGS_TO]->(:Repository|:Space)

    Examples:
        >>> from datetime import datetime, UTC
        >>> rel = BelongsToRelationship(
        ...     created_at=datetime.now(UTC),
        ...     source="github_reader",
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.confidence
        1.0
    """

    # No additional fields beyond BaseRelationship
    pass
