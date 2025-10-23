"""Parameterized Cypher query builders for MERGE operations."""

from typing import Any


def build_merge_node(
    label: str,
    properties: dict[str, Any],
    unique_key: str,
) -> tuple[str, dict[str, Any]]:
    """Build MERGE query for a single node.

    Args:
        label: Node label (e.g., "Service").
        properties: Node properties.
        unique_key: Property name to use for uniqueness constraint.

    Returns:
        tuple[str, dict]: Cypher query and parameters.
    """
    query = f"""
    MERGE (n:{label} {{{unique_key}: ${unique_key}}})
    SET n += $properties
    RETURN n
    """

    params = {
        unique_key: properties[unique_key],
        "properties": properties,
    }

    return query.strip(), params


def build_merge_relationship(
    source_label: str,
    source_key: str,
    source_value: Any,
    target_label: str,
    target_key: str,
    target_value: Any,
    rel_type: str,
    rel_properties: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build MERGE query for a relationship.

    Args:
        source_label: Source node label.
        source_key: Source node unique property name.
        source_value: Source node unique property value.
        target_label: Target node label.
        target_key: Target node unique property name.
        target_value: Target node unique property value.
        rel_type: Relationship type (e.g., "DEPENDS_ON").
        rel_properties: Relationship properties (optional).

    Returns:
        tuple[str, dict]: Cypher query and parameters.
    """
    query = f"""
    MATCH (source:{source_label} {{{source_key}: $source_value}})
    MATCH (target:{target_label} {{{target_key}: $target_value}})
    MERGE (source)-[r:{rel_type}]->(target)
    """

    params: dict[str, Any] = {
        "source_value": source_value,
        "target_value": target_value,
    }

    if rel_properties:
        query += "    SET r += $rel_properties\n"
        params["rel_properties"] = rel_properties

    query += "    RETURN r"

    return query.strip(), params


def build_batch_merge_nodes(
    label: str,
    nodes: list[dict[str, Any]],
    unique_key: str,
) -> tuple[str, dict[str, Any]]:
    """Build batched UNWIND MERGE query for multiple nodes.

    Args:
        label: Node label.
        nodes: List of node property dictionaries.
        unique_key: Property name to use for uniqueness.

    Returns:
        tuple[str, dict]: Cypher query and parameters.
    """
    query = f"""
    UNWIND $nodes AS node
    MERGE (n:{label} {{{unique_key}: node.{unique_key}}})
    SET n += node
    RETURN count(n) AS created_count
    """

    params = {"nodes": nodes}

    return query.strip(), params
