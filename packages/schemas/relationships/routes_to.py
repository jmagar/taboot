"""RoutesToRelationship schema (Proxy → Service)."""

from pydantic import Field

from packages.schemas.relationships.base import BaseRelationship


class RoutesToRelationship(BaseRelationship):
    """ROUTES_TO relationship from Proxy to Service.

    Represents proxy routing configuration.

    Direction: (:Proxy)-[:ROUTES_TO]->(:Service)

    Examples:
        >>> from datetime import datetime, UTC
        >>> rel = RoutesToRelationship(
        ...     host="example.com",
        ...     path="/api",
        ...     tls=True,
        ...     auth_enabled=True,
        ...     created_at=datetime.now(UTC),
        ...     source="swag_reader",
        ...     extractor_version="1.0.0",
        ... )
        >>> rel.host
        'example.com'
    """

    host: str = Field(
        ...,
        min_length=1,
        description="Server name (hostname)",
        examples=["example.com", "api.service.local"],
    )
    path: str = Field(
        ...,
        min_length=1,
        description="Location path",
        examples=["/", "/api", "/admin"],
    )
    tls: bool = Field(
        ...,
        description="Whether TLS is enabled",
    )
    auth_enabled: bool = Field(
        ...,
        description="Whether authentication is enabled",
    )
