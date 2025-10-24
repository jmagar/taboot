"""Tests for Cypher query builders."""

from packages.graph.cypher.builders import (
    build_batch_merge_nodes,
    build_merge_node,
    build_merge_relationship,
)


class TestCypherBuilders:
    """Test parameterized Cypher query builders."""

    def test_build_merge_node(self) -> None:
        """Test building MERGE query for single node."""
        query, params = build_merge_node(
            label="Service",
            properties={"name": "api-service", "version": "v1.0.0"},
            unique_key="name",
        )

        assert "MERGE (n:Service {name: $name})" in query
        assert "SET n += $properties" in query
        assert params["name"] == "api-service"
        assert params["properties"] == {"name": "api-service", "version": "v1.0.0"}

    def test_build_merge_relationship(self) -> None:
        """Test building MERGE query for relationship."""
        query, params = build_merge_relationship(
            source_label="Service",
            source_key="name",
            source_value="api",
            target_label="Service",
            target_key="name",
            target_value="postgres",
            rel_type="DEPENDS_ON",
            rel_properties={"dependency_type": "runtime"},
        )

        assert "MATCH (source:Service {name: $source_value})" in query
        assert "MATCH (target:Service {name: $target_value})" in query
        assert "MERGE (source)-[r:DEPENDS_ON]->(target)" in query
        assert "SET r += $rel_properties" in query
        assert params["source_value"] == "api"
        assert params["target_value"] == "postgres"
        assert params["rel_properties"] == {"dependency_type": "runtime"}

    def test_build_batch_merge_nodes(self) -> None:
        """Test building batched UNWIND MERGE query."""
        nodes = [
            {"name": "api", "version": "v1"},
            {"name": "db", "version": "v2"},
        ]

        query, params = build_batch_merge_nodes(
            label="Service",
            nodes=nodes,
            unique_key="name",
        )

        assert "UNWIND $nodes AS node" in query
        assert "MERGE (n:Service {name: node.name})" in query
        assert "SET n += node" in query
        assert params["nodes"] == nodes
