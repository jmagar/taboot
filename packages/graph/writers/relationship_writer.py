"""RelationshipWriter - Generic batched Neo4j writer for all relationship types.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Handles all 10 core Pydantic relationship schemas dynamically.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging
from typing import Any

from packages.graph.client import Neo4jClient
from packages.schemas.relationships.base import BaseRelationship

logger = logging.getLogger(__name__)


class RelationshipWriter:
    """Generic batched Neo4j writer for all relationship types.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Supports all 10 core relationship types:
    - WORKS_AT (Person -> Organization)
    - MENTIONS (Document -> Any Entity)
    - ROUTES_TO (Proxy -> Service)
    - DEPENDS_ON (Service -> Service)
    - SENT (Person -> Email)
    - CONTRIBUTES_TO (Person -> Repository)
    - CREATED (Person -> Repository/Issue/etc.)
    - BELONGS_TO (Repository -> Organization)
    - IN_THREAD (Email -> Thread)
    - LOCATED_IN (Organization -> Place)

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize RelationshipWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized RelationshipWriter (batch_size={batch_size})")

    def write_relationships(self, relationships: list[dict[str, Any]]) -> dict[str, int]:
        """Write relationships to Neo4j using batched UNWIND.

        Creates or updates relationships between any entity types.
        Uses MERGE for idempotency.

        Args:
            relationships: List of relationship data with keys:
                - rel_type: Relationship type (e.g., "WORKS_AT", "MENTIONS")
                - source_label: Source node label (e.g., "Person")
                - source_key: Property key for matching source (e.g., "email")
                - source_value: Property value for matching source
                - target_label: Target node label (e.g., "Organization")
                - target_key: Property key for matching target (e.g., "name")
                - target_value: Property value for matching target
                - relationship: BaseRelationship subclass instance with properties

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total relationships written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If relationships list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not relationships:
            logger.info("No relationships to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare relationship parameters
        try:
            rel_params = []
            for r in relationships:
                # Extract relationship instance
                rel_instance: BaseRelationship = r["relationship"]

                # Build base properties (common to all relationships)
                props = {
                    "created_at": rel_instance.created_at.isoformat(),
                    "source_timestamp": (
                        rel_instance.source_timestamp.isoformat()
                        if rel_instance.source_timestamp
                        else None
                    ),
                    "source": rel_instance.source,
                    "confidence": rel_instance.confidence,
                    "extractor_version": rel_instance.extractor_version,
                }

                # Add relationship-specific properties dynamically
                for field_name, field_value in rel_instance.model_dump().items():
                    if field_name not in (
                        "created_at",
                        "source_timestamp",
                        "source",
                        "confidence",
                        "extractor_version",
                    ):
                        # Handle datetime fields
                        if hasattr(field_value, "isoformat"):
                            props[field_name] = field_value.isoformat()
                        # Handle UUID fields
                        elif hasattr(field_value, "__str__") and field_name.endswith("_id"):
                            props[field_name] = str(field_value)
                        else:
                            props[field_name] = field_value

                rel_params.append(
                    {
                        "rel_type": r["rel_type"],
                        "source_label": r["source_label"],
                        "source_key": r["source_key"],
                        "source_value": r["source_value"],
                        "target_label": r["target_label"],
                        "target_key": r["target_key"],
                        "target_value": r["target_value"],
                        "properties": props,
                    }
                )

        except (KeyError, AttributeError) as e:
            logger.error(f"Invalid relationship data in batch: {e}")
            raise ValueError(f"Invalid relationship data: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(rel_params), self.batch_size):
                    batch = rel_params[i : i + self.batch_size]

                    # Dynamic Cypher query using CALL and apoc.create.relationship
                    # This allows us to handle any relationship type dynamically
                    query = """
                    UNWIND $rows AS row
                    CALL {
                        WITH row
                        MATCH (source) WHERE row.source_label IN labels(source)
                            AND source[row.source_key] = row.source_value
                        MATCH (target) WHERE row.target_label IN labels(target)
                            AND target[row.target_key] = row.target_value
                        CALL apoc.merge.relationship(
                            source,
                            row.rel_type,
                            {},
                            row.properties,
                            target,
                            {}
                        ) YIELD rel
                        RETURN rel
                    }
                    RETURN count(rel) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote relationship batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} relationship(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write relationships to Neo4j: {e}",
                extra={
                    "batch_size": self.batch_size,
                    "total_relationships": len(relationships),
                },
            )
            raise


# Export public API
__all__ = ["RelationshipWriter"]
