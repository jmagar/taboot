"""DependsOnRelationship schema (Service → Service)."""

from pydantic import Field

from packages.schemas.relationships.base import BaseRelationship


class DependsOnRelationship(BaseRelationship):
    """DEPENDS_ON relationship from Service to Service.

    Represents service dependency (Docker Compose, etc.).

    Direction: (:ComposeService)-[:DEPENDS_ON]->(:ComposeService)

    Examples:
        >>> from datetime import datetime, UTC
        >>> rel = DependsOnRelationship(
        ...     condition="service_healthy",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     source="docker_compose_reader",
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.condition
        'service_healthy'
    """

    condition: str = Field(
        ...,
        min_length=1,
        description="Dependency condition",
        examples=["service_started", "service_healthy", "service_completed_successfully"],
    )
