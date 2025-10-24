"""Batched Neo4j writers using UNWIND operations for high throughput."""

from typing import Any


class BatchedGraphWriter:
    """Batched writer for Neo4j graph operations (target ≥20k edges/min)."""

    def __init__(self, client: Any, batch_size: int = 2000):
        """Initialize batched writer.

        Args:
            client: Neo4j client instance.
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.client = client
        self.batch_size = batch_size

    async def batch_write_nodes(
        self,
        label: str,
        nodes: list[dict[str, Any]],
        unique_key: str,
    ) -> dict[str, int]:
        """Write nodes in batches using UNWIND.

        Args:
            label: Node label.
            nodes: List of node property dictionaries.
            unique_key: Property name for uniqueness constraint.

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        total_written = 0
        batches_executed = 0

        for i in range(0, len(nodes), self.batch_size):
            batch = nodes[i : i + self.batch_size]

            query = f"""
            UNWIND $nodes AS node
            MERGE (n:{label} {{{unique_key}: node.{unique_key}}})
            SET n += node
            RETURN count(n) AS created_count
            """

            _ = await self.client.execute_query(query, {"nodes": batch})
            total_written += len(batch)
            batches_executed += 1

        return {"total_written": total_written, "batches_executed": batches_executed}

    async def batch_write_relationships(
        self,
        source_label: str,
        source_key: str,
        target_label: str,
        target_key: str,
        rel_type: str,
        relationships: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Write relationships in batches using UNWIND.

        Args:
            source_label: Source node label.
            source_key: Source node unique property name.
            target_label: Target node label.
            target_key: Target node unique property name.
            rel_type: Relationship type.
            relationships: List of relationship dictionaries with:
                - source_value: Source node unique value
                - target_value: Target node unique value
                - rel_properties: Relationship properties (optional)

        Returns:
            dict[str, int]: Statistics (total_written, batches_executed).
        """
        total_written = 0
        batches_executed = 0

        for i in range(0, len(relationships), self.batch_size):
            batch = relationships[i : i + self.batch_size]

            query = f"""
            UNWIND $rels AS rel
            MATCH (source:{source_label} {{{source_key}: rel.source_value}})
            MATCH (target:{target_label} {{{target_key}: rel.target_value}})
            MERGE (source)-[r:{rel_type}]->(target)
            SET r += rel.rel_properties
            RETURN count(r) AS created_count
            """

            _ = await self.client.execute_query(query, {"rels": batch})
            total_written += len(batch)
            batches_executed += 1

        return {"total_written": total_written, "batches_executed": batches_executed}
