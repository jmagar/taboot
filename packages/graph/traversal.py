"""Neo4j graph traversal for knowledge graph expansion."""

from typing import Any

from neo4j import GraphDatabase


class GraphTraversal:
    """Graph traversal with relationship prioritization."""

    def __init__(
        self,
        neo4j_uri: str,
        username: str,
        password: str,
        max_hops: int = 2,
        relationship_priority: list[str] | None = None
    ):
        """
        Initialize graph traversal client.

        Args:
            neo4j_uri: Neo4j connection URI
            username: Neo4j username
            password: Neo4j password
            max_hops: Maximum traversal depth (default 2)
            relationship_priority: Priority order for relationship types
        """
        self.neo4j_uri = neo4j_uri
        self.max_hops = max_hops
        self.relationship_priority = relationship_priority or [
            "DEPENDS_ON",
            "ROUTES_TO",
            "BINDS",
            "EXPOSES_ENDPOINT",
            "MENTIONS"
        ]

        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(username, password)
        )

    def get_relationship_priority(self) -> list[str]:
        """Get relationship type priority order."""
        return self.relationship_priority

    def build_traversal_query(
        self,
        start_node_names: list[str],
        relationship_types: list[str] | None = None,
        max_hops: int | None = None
    ) -> str:
        """
        Build Cypher query for multi-hop graph traversal.

        Args:
            start_node_names: Starting node names
            relationship_types: Relationship types to traverse
            max_hops: Maximum hops (overrides default)

        Returns:
            Cypher query string
        """
        hops = max_hops or self.max_hops
        rel_types = relationship_types or self.relationship_priority

        # Build relationship type filter
        rel_filter = "|".join(rel_types)

        query = f"""
        MATCH path = (start)-[:{rel_filter}*1..{hops}]-(end)
        WHERE start.name IN $start_names
        RETURN DISTINCT
            start.name AS start_name,
            [r IN relationships(path) | type(r)] AS rel_types,
            end.name AS end_name,
            labels(end) AS end_labels,
            properties(end) AS end_properties,
            length(path) AS hops
        ORDER BY hops ASC
        LIMIT 100
        """

        return query.strip()

    def traverse_from_entities(
        self,
        entity_names: list[str],
        max_hops: int | None = None,
        relationship_types: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Traverse graph from given entity names.

        Args:
            entity_names: Starting entity names
            max_hops: Maximum traversal depth
            relationship_types: Relationship types to follow

        Returns:
            List of traversal results with nodes and paths
        """
        if not entity_names:
            return []

        query = self.build_traversal_query(
            start_node_names=entity_names,
            relationship_types=relationship_types,
            max_hops=max_hops
        )

        results = []
        with self.driver.session() as session:
            records = session.run(query, start_names=entity_names)

            for record in records:
                results.append({
                    "start_name": record["start_name"],
                    "rel_types": record["rel_types"],
                    "end_name": record["end_name"],
                    "end_labels": record["end_labels"],
                    "end_properties": dict(record["end_properties"]),
                    "hops": record["hops"]
                })

        return results

    def close(self) -> None:
        """Close Neo4j driver connection."""
        self.driver.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
