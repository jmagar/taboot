"""WorksAtRelationship schema (Person → Organization)."""

from datetime import datetime

from pydantic import Field

from packages.schemas.relationships.base import BaseRelationship


class WorksAtRelationship(BaseRelationship):
    """WORKS_AT relationship from Person to Organization.

    Represents employment or affiliation.

    Direction: (:Person)-[:WORKS_AT]->(:Organization)

    Examples:
        >>> from datetime import datetime, UTC
        >>> rel = WorksAtRelationship(
        ...     role="Senior Engineer",
        ...     start_date=datetime(2020, 1, 1, tzinfo=UTC),
        ...     created_at=datetime.now(UTC),
        ...     source="github_reader",
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.role
        'Senior Engineer'
    """

    role: str | None = Field(
        None,
        description="Job title or role",
        examples=["Senior Engineer", "Product Manager", "CTO"],
    )
    start_date: datetime | None = Field(
        None,
        description="Employment start date",
    )
    end_date: datetime | None = Field(
        None,
        description="Employment end date (None if current)",
    )
