"""GmailWriter - Batched Neo4j writer for Gmail entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/person_writer.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging
from typing import Any

from packages.graph.client import Neo4jClient
from packages.schemas.gmail import Attachment, Email, GmailLabel, Thread

logger = logging.getLogger(__name__)


class GmailWriter:
    """Batched Neo4j writer for Gmail entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize GmailWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized GmailWriter (batch_size={batch_size})")

    def write_emails(self, emails: list[Email]) -> dict[str, int]:
        """Write Email nodes to Neo4j using batched UNWIND.

        Creates or updates Email nodes with all properties.
        Uses MERGE on unique key (message_id) for idempotency.

        Args:
            emails: List of Email entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total emails written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If emails list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not emails:
            logger.info("No emails to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare email parameters
        try:
            email_params = [
                {
                    "message_id": e.message_id,
                    "thread_id": e.thread_id,
                    "subject": e.subject,
                    "snippet": e.snippet,
                    "body": e.body,
                    "sent_at": e.sent_at.isoformat(),
                    "labels": e.labels,
                    "size_estimate": e.size_estimate,
                    "has_attachments": e.has_attachments,
                    "in_reply_to": e.in_reply_to,
                    "references": e.references,
                    "created_at": e.created_at.isoformat(),
                    "updated_at": e.updated_at.isoformat(),
                    "source_timestamp": e.source_timestamp.isoformat()
                    if e.source_timestamp
                    else None,
                    "extraction_tier": e.extraction_tier,
                    "extraction_method": e.extraction_method,
                    "confidence": e.confidence,
                    "extractor_version": e.extractor_version,
                }
                for e in emails
            ]
        except AttributeError as err:
            logger.error(f"Invalid Email entity in batch: {err}")
            raise ValueError(f"Invalid Email entity: {err}") from err

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(email_params), self.batch_size):
                    batch = email_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (e:Email {message_id: row.message_id})
                    SET e.thread_id = row.thread_id,
                        e.subject = row.subject,
                        e.snippet = row.snippet,
                        e.body = row.body,
                        e.sent_at = row.sent_at,
                        e.labels = row.labels,
                        e.size_estimate = row.size_estimate,
                        e.has_attachments = row.has_attachments,
                        e.in_reply_to = row.in_reply_to,
                        e.references = row.references,
                        e.created_at = row.created_at,
                        e.updated_at = row.updated_at,
                        e.source_timestamp = row.source_timestamp,
                        e.extraction_tier = row.extraction_tier,
                        e.extraction_method = row.extraction_method,
                        e.confidence = row.confidence,
                        e.extractor_version = row.extractor_version
                    RETURN count(e) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote email batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(f"Wrote {total_written} Email node(s) in {batches_executed} batch(es)")

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write emails to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_emails": len(emails)},
            )
            raise

    def write_threads(self, threads: list[Thread]) -> dict[str, int]:
        """Write Thread nodes to Neo4j using batched UNWIND.

        Creates or updates Thread nodes with all properties.
        Uses MERGE on unique key (thread_id) for idempotency.

        Args:
            threads: List of Thread entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total threads written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If threads list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not threads:
            logger.info("No threads to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare thread parameters
        try:
            thread_params = [
                {
                    "thread_id": t.thread_id,
                    "subject": t.subject,
                    "message_count": t.message_count,
                    "participant_count": t.participant_count,
                    "first_message_at": t.first_message_at.isoformat(),
                    "last_message_at": t.last_message_at.isoformat(),
                    "labels": t.labels,
                    "created_at": t.created_at.isoformat(),
                    "updated_at": t.updated_at.isoformat(),
                    "source_timestamp": t.source_timestamp.isoformat()
                    if t.source_timestamp
                    else None,
                    "extraction_tier": t.extraction_tier,
                    "extraction_method": t.extraction_method,
                    "confidence": t.confidence,
                    "extractor_version": t.extractor_version,
                }
                for t in threads
            ]
        except AttributeError as err:
            logger.error(f"Invalid Thread entity in batch: {err}")
            raise ValueError(f"Invalid Thread entity: {err}") from err

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(thread_params), self.batch_size):
                    batch = thread_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (t:Thread {thread_id: row.thread_id})
                    SET t.subject = row.subject,
                        t.message_count = row.message_count,
                        t.participant_count = row.participant_count,
                        t.first_message_at = row.first_message_at,
                        t.last_message_at = row.last_message_at,
                        t.labels = row.labels,
                        t.created_at = row.created_at,
                        t.updated_at = row.updated_at,
                        t.source_timestamp = row.source_timestamp,
                        t.extraction_tier = row.extraction_tier,
                        t.extraction_method = row.extraction_method,
                        t.confidence = row.confidence,
                        t.extractor_version = row.extractor_version
                    RETURN count(t) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote thread batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(f"Wrote {total_written} Thread node(s) in {batches_executed} batch(es)")

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write threads to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_threads": len(threads)},
            )
            raise

    def write_labels(self, labels: list[GmailLabel]) -> dict[str, int]:
        """Write GmailLabel nodes to Neo4j using batched UNWIND.

        Creates or updates GmailLabel nodes with all properties.
        Uses MERGE on unique key (label_id) for idempotency.

        Args:
            labels: List of GmailLabel entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total labels written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If labels list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not labels:
            logger.info("No labels to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare label parameters
        try:
            label_params = [
                {
                    "label_id": label.label_id,
                    "name": label.name,
                    "type": label.type,
                    "color": label.color,
                    "message_count": label.message_count,
                    "created_at": label.created_at.isoformat(),
                    "updated_at": label.updated_at.isoformat(),
                    "source_timestamp": label.source_timestamp.isoformat()
                    if label.source_timestamp
                    else None,
                    "extraction_tier": label.extraction_tier,
                    "extraction_method": label.extraction_method,
                    "confidence": label.confidence,
                    "extractor_version": label.extractor_version,
                }
                for label in labels
            ]
        except AttributeError as err:
            logger.error(f"Invalid GmailLabel entity in batch: {err}")
            raise ValueError(f"Invalid GmailLabel entity: {err}") from err

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(label_params), self.batch_size):
                    batch = label_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (l:GmailLabel {label_id: row.label_id})
                    SET l.name = row.name,
                        l.type = row.type,
                        l.color = row.color,
                        l.message_count = row.message_count,
                        l.created_at = row.created_at,
                        l.updated_at = row.updated_at,
                        l.source_timestamp = row.source_timestamp,
                        l.extraction_tier = row.extraction_tier,
                        l.extraction_method = row.extraction_method,
                        l.confidence = row.confidence,
                        l.extractor_version = row.extractor_version
                    RETURN count(l) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote label batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(f"Wrote {total_written} GmailLabel node(s) in {batches_executed} batch(es)")

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write labels to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_labels": len(labels)},
            )
            raise

    def write_attachments(self, attachments: list[Attachment]) -> dict[str, int]:
        """Write Attachment nodes to Neo4j using batched UNWIND.

        Creates or updates Attachment nodes with all properties.
        Uses MERGE on unique key (attachment_id) for idempotency.

        Args:
            attachments: List of Attachment entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total attachments written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If attachments list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not attachments:
            logger.info("No attachments to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare attachment parameters
        try:
            attachment_params = [
                {
                    "attachment_id": a.attachment_id,
                    "filename": a.filename,
                    "mime_type": a.mime_type,
                    "size": a.size,
                    "content_hash": a.content_hash,
                    "is_inline": a.is_inline,
                    "created_at": a.created_at.isoformat(),
                    "updated_at": a.updated_at.isoformat(),
                    "source_timestamp": a.source_timestamp.isoformat()
                    if a.source_timestamp
                    else None,
                    "extraction_tier": a.extraction_tier,
                    "extraction_method": a.extraction_method,
                    "confidence": a.confidence,
                    "extractor_version": a.extractor_version,
                }
                for a in attachments
            ]
        except AttributeError as err:
            logger.error(f"Invalid Attachment entity in batch: {err}")
            raise ValueError(f"Invalid Attachment entity: {err}") from err

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(attachment_params), self.batch_size):
                    batch = attachment_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (a:Attachment {attachment_id: row.attachment_id})
                    SET a.filename = row.filename,
                        a.mime_type = row.mime_type,
                        a.size = row.size,
                        a.content_hash = row.content_hash,
                        a.is_inline = row.is_inline,
                        a.created_at = row.created_at,
                        a.updated_at = row.updated_at,
                        a.source_timestamp = row.source_timestamp,
                        a.extraction_tier = row.extraction_tier,
                        a.extraction_method = row.extraction_method,
                        a.confidence = row.confidence,
                        a.extractor_version = row.extractor_version
                    RETURN count(a) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote attachment batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} Attachment node(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write attachments to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_attachments": len(attachments)},
            )
            raise

    def write_email_in_thread_relationships(
        self, relationships: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Write IN_THREAD relationships from Email to Thread.

        Creates Email-[IN_THREAD]->Thread relationships using batched UNWIND.

        Args:
            relationships: List of dicts with keys:
                - email_message_id: str (Email message_id)
                - thread_id: str (Thread thread_id)

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total relationships written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If relationships list is invalid.
            Exception: If Neo4j write operation fails.
        """
        if not relationships:
            logger.info("No email->thread relationships to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(relationships), self.batch_size):
                    batch = relationships[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MATCH (e:Email {message_id: row.email_message_id})
                    MATCH (t:Thread {thread_id: row.thread_id})
                    MERGE (e)-[r:IN_THREAD]->(t)
                    RETURN count(r) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote IN_THREAD relationship batch {batches_executed}: "
                        f"{len(batch)} relationships, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} IN_THREAD relationship(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write email->thread relationships to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_relationships": len(relationships)},
            )
            raise

    def write_email_has_attachment_relationships(
        self, relationships: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Write HAS_ATTACHMENT relationships from Email to Attachment.

        Creates Email-[HAS_ATTACHMENT]->Attachment relationships using batched UNWIND.

        Args:
            relationships: List of dicts with keys:
                - email_message_id: str (Email message_id)
                - attachment_id: str (Attachment attachment_id)

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total relationships written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If relationships list is invalid.
            Exception: If Neo4j write operation fails.
        """
        if not relationships:
            logger.info("No email->attachment relationships to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(relationships), self.batch_size):
                    batch = relationships[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MATCH (e:Email {message_id: row.email_message_id})
                    MATCH (a:Attachment {attachment_id: row.attachment_id})
                    MERGE (e)-[r:HAS_ATTACHMENT]->(a)
                    RETURN count(r) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote HAS_ATTACHMENT relationship batch {batches_executed}: "
                        f"{len(batch)} relationships, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} HAS_ATTACHMENT relationship(s) in "
                f"{batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write email->attachment relationships to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_relationships": len(relationships)},
            )
            raise

    def write_email_has_label_relationships(
        self, relationships: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Write HAS_LABEL relationships from Email to GmailLabel.

        Creates Email-[HAS_LABEL]->GmailLabel relationships using batched UNWIND.

        Args:
            relationships: List of dicts with keys:
                - email_message_id: str (Email message_id)
                - label_id: str (GmailLabel label_id)

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total relationships written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If relationships list is invalid.
            Exception: If Neo4j write operation fails.
        """
        if not relationships:
            logger.info("No email->label relationships to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(relationships), self.batch_size):
                    batch = relationships[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MATCH (e:Email {message_id: row.email_message_id})
                    MATCH (l:GmailLabel {label_id: row.label_id})
                    MERGE (e)-[r:HAS_LABEL]->(l)
                    RETURN count(r) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote HAS_LABEL relationship batch {batches_executed}: "
                        f"{len(batch)} relationships, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} HAS_LABEL relationship(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write email->label relationships to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_relationships": len(relationships)},
            )
            raise


# Export public API
__all__ = ["GmailWriter"]
