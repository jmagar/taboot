"""Knowledge graph entity and relation schemas.

Defines entity types, relation types, and their properties for structured
knowledge graph extraction using LlamaIndex SchemaLLMPathExtractor.
"""

from enum import Enum


class EntityType(str, Enum):
    """Supported entity types for knowledge graph extraction."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECHNOLOGY"
    EVENT = "EVENT"
    FILE = "FILE"
    CONCEPT = "CONCEPT"


class RelationType(str, Enum):
    """Supported relation types for knowledge graph extraction."""

    WORKS_FOR = "WORKS_FOR"
    CREATED_BY = "CREATED_BY"
    LOCATED_IN = "LOCATED_IN"
    USES = "USES"
    PART_OF = "PART_OF"
    RELATED_TO = "RELATED_TO"
    IMPLEMENTS = "IMPLEMENTS"
    DEPENDS_ON = "DEPENDS_ON"
    MENTIONS = "MENTIONS"
    REFERENCES = "REFERENCES"


# Entity property schemas - maps entity types to their allowed properties
ENTITY_PROPERTY_SCHEMAS: dict[str, list[tuple[str, str]]] = {
    "PERSON": [
        ("email", "Email address"),
        ("role", "Job role or position"),
        ("title", "Professional title"),
        ("company", "Company or organization"),
    ],
    "ORGANIZATION": [
        ("industry", "Industry or sector"),
        ("size", "Company size (employees or revenue)"),
        ("website", "Website URL"),
        ("location", "Headquarters location"),
    ],
    "LOCATION": [
        ("address", "Physical address"),
        ("coordinates", "GPS coordinates"),
        ("type", "Location type (city, country, building, etc.)"),
    ],
    "PRODUCT": [
        ("version", "Product version"),
        ("vendor", "Product vendor or manufacturer"),
        ("category", "Product category"),
    ],
    "TECHNOLOGY": [
        ("language", "Programming language"),
        ("framework", "Framework or library name"),
        ("version", "Version number"),
    ],
    "EVENT": [
        ("startTime", "Start date/time"),
        ("endTime", "End date/time"),
        ("location", "Event location"),
        ("type", "Event type"),
    ],
    "FILE": [
        ("fileId", "File identifier"),
        ("source", "File source or repository"),
        ("format", "File format or extension"),
        ("lastModified", "Last modification date"),
    ],
    "CONCEPT": [
        ("category", "Conceptual category"),
        ("domain", "Knowledge domain"),
        ("relatedTo", "Related concepts"),
    ],
}

# Relation property schemas - maps relation types to their allowed properties
RELATION_PROPERTY_SCHEMAS: dict[str, list[tuple[str, str]]] = {
    "WORKS_FOR": [
        ("role", "Role in organization"),
        ("startDate", "Employment start date"),
        ("endDate", "Employment end date"),
    ],
    "CREATED_BY": [
        ("date", "Creation date"),
        ("version", "Version at creation"),
    ],
    "LOCATED_IN": [
        ("since", "Located since date"),
        ("type", "Location relationship type"),
    ],
    "USES": [
        ("purpose", "Purpose of use"),
        ("frequency", "Usage frequency"),
    ],
    "PART_OF": [
        ("role", "Role within parent"),
        ("percentage", "Percentage or proportion"),
    ],
    "RELATED_TO": [
        ("strength", "Relationship strength"),
        ("type", "Relationship type"),
    ],
    "IMPLEMENTS": [
        ("version", "Implementation version"),
        ("standard", "Standard or specification"),
    ],
    "DEPENDS_ON": [
        ("version", "Dependency version"),
        ("type", "Dependency type"),
    ],
    "MENTIONS": [
        ("context", "Mention context"),
        ("sentiment", "Sentiment of mention"),
    ],
    "REFERENCES": [
        ("page", "Page number"),
        ("section", "Section reference"),
    ],
}


def get_entity_properties_for_type(entity_type: str) -> list[tuple[str, str]]:
    """Get property schema for entity type.

    Args:
        entity_type: Entity type name (e.g., "PERSON")

    Returns:
        List of (property_name, description) tuples
    """
    return ENTITY_PROPERTY_SCHEMAS.get(entity_type, [])


def get_relation_properties_for_type(relation_type: str) -> list[tuple[str, str]]:
    """Get property schema for relation type.

    Args:
        relation_type: Relation type name (e.g., "WORKS_FOR")

    Returns:
        List of (property_name, description) tuples
    """
    return RELATION_PROPERTY_SCHEMAS.get(relation_type, [])


def get_all_entity_properties() -> list[tuple[str, str]]:
    """Get all entity properties across all types.

    Returns:
        Deduplicated list of (property_name, description) tuples
    """
    all_props = {}
    for props in ENTITY_PROPERTY_SCHEMAS.values():
        for name, desc in props:
            if name not in all_props:
                all_props[name] = desc
    return list(all_props.items())


def get_all_relation_properties() -> list[tuple[str, str]]:
    """Get all relation properties across all types.

    Returns:
        Deduplicated list of (property_name, description) tuples
    """
    all_props = {}
    for props in RELATION_PROPERTY_SCHEMAS.values():
        for name, desc in props:
            if name not in all_props:
                all_props[name] = desc
    return list(all_props.items())
