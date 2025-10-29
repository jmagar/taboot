"""ContributesToRelationship schema (Person → Repository)."""

from datetime import datetime

from pydantic import Field

from packages.schemas.relationships.base import BaseRelationship


class ContributesToRelationship(BaseRelationship):
    """CONTRIBUTES_TO relationship from Person to Repository.

    Represents code contributions.

    Direction: (:Person)-[:CONTRIBUTES_TO]->(:Repository)

    Examples:
        >>> from datetime import datetime, UTC
        >>> rel = ContributesToRelationship(
        ...     commit_count=150,
        ...     first_commit_at=datetime(2020, 1, 1, tzinfo=UTC),
        ...     last_commit_at=datetime(2024, 1, 15, tzinfo=UTC),
        ...     created_at=datetime.now(UTC),
        ...     source="github_reader",
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.commit_count
        150
    """

    commit_count: int = Field(
        ...,
        ge=1,
        description="Number of commits",
    )
    first_commit_at: datetime = Field(
        ...,
        description="Timestamp of first commit",
    )
    last_commit_at: datetime = Field(
        ...,
        description="Timestamp of last commit",
    )
