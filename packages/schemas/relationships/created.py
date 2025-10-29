"""CreatedRelationship schema (Person → File)."""

from packages.schemas.relationships.base import BaseRelationship


class CreatedRelationship(BaseRelationship):
    """CREATED relationship from Person to File.

    Represents file authorship.

    Direction: (:Person)-[:CREATED]->(:File)

    Examples:
        >>> from datetime import datetime, UTC
        >>> rel = CreatedRelationship(
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     source="github_reader",
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.confidence
        1.0
    """

    # No additional fields beyond BaseRelationship
    pass
