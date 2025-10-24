"""Tests for Neo4j graph traversal."""

import pytest

from packages.graph.traversal import GraphTraversal


@pytest.mark.unit
def test_graph_traversal_init() -> None:
    """Test GraphTraversal initialization."""
    traversal = GraphTraversal(neo4j_uri="bolt://localhost:7687", username="neo4j", password="test")

    assert traversal.neo4j_uri == "bolt://localhost:7687"
    assert traversal.max_hops == 2


@pytest.mark.unit
def test_graph_traversal_builds_cypher_query() -> None:
    """Test Cypher query construction for multi-hop traversal."""
    traversal = GraphTraversal(neo4j_uri="bolt://localhost:7687", username="neo4j", password="test")

    query = traversal.build_traversal_query(
        start_node_names=["api-service"], relationship_types=["DEPENDS_ON", "ROUTES_TO"], max_hops=2
    )

    assert query is not None
    assert "MATCH" in query
    assert "DEPENDS_ON" in query or "ROUTES_TO" in query


@pytest.mark.integration
@pytest.mark.slow
def test_graph_traversal_with_real_neo4j(neo4j_client) -> None:
    """Test graph traversal against real Neo4j instance."""
    traversal = GraphTraversal(
        neo4j_uri="bolt://localhost:7687", username="neo4j", password="changeme"
    )

    # Test traversal from known service
    results = traversal.traverse_from_entities(entity_names=["api-service"], max_hops=2)

    assert isinstance(results, list)
    # Results may be empty if no data, but should return list


@pytest.mark.unit
def test_graph_traversal_prioritizes_relationships() -> None:
    """Test relationship type prioritization in traversal."""
    traversal = GraphTraversal(neo4j_uri="bolt://localhost:7687", username="neo4j", password="test")

    priority = traversal.get_relationship_priority()
    assert "DEPENDS_ON" in priority
    assert "ROUTES_TO" in priority
    assert priority.index("DEPENDS_ON") < priority.index("ROUTES_TO")
