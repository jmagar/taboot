"""DocumentWriter - Batched Neo4j writer for Document entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Handles both Document nodes and MENTIONS relationships.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging
from typing import Any

from packages.graph.client import Neo4jClient
from packages.schemas.web.document import Document

logger = logging.getLogger(__name__)


class DocumentWriter:
    """Batched Neo4j writer for Document entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Supports:
    - Document node creation
    - MENTIONS relationships (Document -> Any Entity)

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize DocumentWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized DocumentWriter (batch_size={batch_size})")

    def write_documents(self, documents: list[Document]) -> dict[str, int]:
        """Write Document nodes to Neo4j using batched UNWIND.

        Creates or updates Document nodes with all properties.
        Uses MERGE on unique key (doc_id) for idempotency.

        Args:
            documents: List of Document entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total documents written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If documents list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not documents:
            logger.info("No documents to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare document parameters (optimized list comprehension)
        try:
            doc_params = [
                {
                    "doc_id": d.doc_id,
                    "source_url": d.source_url,
                    "source_type": d.source_type,
                    "content_hash": d.content_hash,
                    "ingested_at": d.ingested_at.isoformat(),
                    "extraction_state": d.extraction_state,
                    "created_at": d.created_at.isoformat(),
                    "updated_at": d.updated_at.isoformat(),
                    "source_timestamp": (
                        d.source_timestamp.isoformat() if d.source_timestamp else None
                    ),
                    "extraction_tier": d.extraction_tier,
                    "extraction_method": d.extraction_method,
                    "confidence": d.confidence,
                    "extractor_version": d.extractor_version,
                }
                for d in documents
            ]
        except AttributeError as e:
            logger.error(f"Invalid Document entity in batch: {e}")
            raise ValueError(f"Invalid Document entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(doc_params), self.batch_size):
                    batch = doc_params[i : i + self.batch_size]

                    # Optimized Cypher query with explicit property setting
                    query = """
                    UNWIND $rows AS row
                    MERGE (d:Document {doc_id: row.doc_id})
                    SET d.source_url = row.source_url,
                        d.source_type = row.source_type,
                        d.content_hash = row.content_hash,
                        d.ingested_at = row.ingested_at,
                        d.extraction_state = row.extraction_state,
                        d.created_at = row.created_at,
                        d.updated_at = row.updated_at,
                        d.source_timestamp = row.source_timestamp,
                        d.extraction_tier = row.extraction_tier,
                        d.extraction_method = row.extraction_method,
                        d.confidence = row.confidence,
                        d.extractor_version = row.extractor_version
                    RETURN count(d) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote document batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} Document node(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write documents to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_documents": len(documents)},
            )
            raise

    def write_mentions_relationships(
        self, mentions: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Write MENTIONS relationships from Documents to Entities.

        Creates relationships between Document nodes and any entity type.

        Args:
            mentions: List of mention data with keys:
                - doc_id: Document ID (source node)
                - entity_type: Target entity label (e.g., "Person", "Organization")
                - entity_key: Property key for matching target (e.g., "email", "name")
                - entity_value: Property value for matching target
                - relationship: MentionsRelationship instance with properties

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total relationships written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If mentions list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not mentions:
            logger.info("No mentions relationships to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare relationship parameters
        try:
            rel_params = [
                {
                    "doc_id": m["doc_id"],
                    "entity_type": m["entity_type"],
                    "entity_key": m["entity_key"],
                    "entity_value": m["entity_value"],
                    "span": m["relationship"].span,
                    "section": m["relationship"].section,
                    "chunk_id": str(m["relationship"].chunk_id),
                    "created_at": m["relationship"].created_at.isoformat(),
                    "source_timestamp": (
                        m["relationship"].source_timestamp.isoformat()
                        if m["relationship"].source_timestamp
                        else None
                    ),
                    "source": m["relationship"].source,
                    "confidence": m["relationship"].confidence,
                    "extractor_version": m["relationship"].extractor_version,
                }
                for m in mentions
            ]
        except (KeyError, AttributeError) as e:
            logger.error(f"Invalid mention data in batch: {e}")
            raise ValueError(f"Invalid mention data: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(rel_params), self.batch_size):
                    batch = rel_params[i : i + self.batch_size]

                    # Dynamic Cypher query using CALL to handle variable entity types
                    # We use apoc.cypher.run with proper scoping (Neo4j 5+ syntax)
                    query = """
                    UNWIND $rows AS row
                    MATCH (d:Document {doc_id: row.doc_id})
                    CALL (row, d) {
                        WITH row, d
                        CALL apoc.cypher.run(
                            'MATCH (e:' + row.entity_type + ' {' +
                            row.entity_key + ': $entity_value}) RETURN e',
                            {entity_value: row.entity_value}
                        ) YIELD value
                        WITH value.e AS entity, row, d
                        MERGE (d)-[r:MENTIONS {chunk_id: row.chunk_id}]->(entity)
                        SET r.span = row.span,
                            r.section = row.section,
                            r.created_at = row.created_at,
                            r.source_timestamp = row.source_timestamp,
                            r.source = row.source,
                            r.confidence = row.confidence,
                            r.extractor_version = row.extractor_version
                        RETURN r
                    }
                    RETURN count(*) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote MENTIONS relationship batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} MENTIONS relationship(s) in "
                f"{batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write MENTIONS relationships to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_mentions": len(mentions)},
            )
            raise


# Export public API
__all__ = ["DocumentWriter"]
