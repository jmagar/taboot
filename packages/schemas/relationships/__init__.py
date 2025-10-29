"""Relationship schemas for Neo4j graph.

All relationships in the graph must inherit from BaseRelationship
and include temporal tracking fields.
"""

from packages.schemas.relationships.base import BaseRelationship
from packages.schemas.relationships.belongs_to import BelongsToRelationship
from packages.schemas.relationships.contributes_to import ContributesToRelationship
from packages.schemas.relationships.created import CreatedRelationship
from packages.schemas.relationships.depends_on import DependsOnRelationship
from packages.schemas.relationships.in_thread import InThreadRelationship
from packages.schemas.relationships.located_in import LocatedInRelationship
from packages.schemas.relationships.mentions import MentionsRelationship
from packages.schemas.relationships.routes_to import RoutesToRelationship
from packages.schemas.relationships.sent import SentRelationship
from packages.schemas.relationships.works_at import WorksAtRelationship

__all__ = [
    "BaseRelationship",
    "BelongsToRelationship",
    "ContributesToRelationship",
    "CreatedRelationship",
    "DependsOnRelationship",
    "InThreadRelationship",
    "LocatedInRelationship",
    "MentionsRelationship",
    "RoutesToRelationship",
    "SentRelationship",
    "WorksAtRelationship",
]
