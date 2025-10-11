"""Neo4j graph database client for LlamaCrawl.

This module provides a wrapper around the Neo4j Python driver for managing
knowledge graph storage, including schema initialization, node/relationship
operations, and graph traversal queries.
"""

from typing import Any

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from llamacrawl.config import Config
from llamacrawl.utils.logging import get_logger, log_execution_time

logger = get_logger(__name__)


class Neo4jClient:
    """Neo4j graph database client with connection management and graph operations.

    This class provides:
    1. Connection management with singleton driver pattern
    2. Schema initialization (constraints and indexes)
    3. Node creation and batch operations
    4. Relationship creation and batch operations
    5. Graph traversal and query methods

    All operations use parameterized queries to prevent Cypher injection.
    Batch operations use UNWIND for efficiency.
    """

    def __init__(self, config: Config) -> None:
        """Initialize Neo4j client from configuration.

        Args:
            config: Configuration object with Neo4j connection settings
        """
        self.uri = config.neo4j_uri
        self.username = config.neo4j_user
        self.password = config.neo4j_password
        self._driver: Driver | None = None

        logger.info("Neo4j client initialized", extra={"uri": self.uri, "username": self.username})

    @property
    def driver(self) -> Driver:
        """Get Neo4j driver instance (singleton pattern).

        Returns:
            Neo4j driver instance

        Raises:
            ServiceUnavailable: If connection cannot be established
        """
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    self.uri, auth=(self.username, self.password)
                )
                # Verify connectivity
                self._driver.verify_connectivity()
                logger.info("Neo4j driver created and verified")
            except ServiceUnavailable as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise

        return self._driver

    def close(self) -> None:
        """Close Neo4j driver connection.

        Should be called when shutting down the application.
        """
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed")

    def health_check(self) -> bool:
        """Check Neo4j database connectivity.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as health")
                record = result.single()
                if record and record["health"] == 1:
                    logger.debug("Neo4j health check passed")
                    return True
                return False
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False

    @log_execution_time
    def initialize_schema(self) -> None:
        """Create constraints and indexes for the knowledge graph schema.

        This method is idempotent - constraints and indexes are created
        with IF NOT EXISTS, so it can be run multiple times safely.

        Creates:
        - Unique constraints on primary identifiers
        - Indexes on frequently queried fields
        """
        with self.driver.session() as session:
            # Unique constraints
            constraints = [
                # Document unique constraint
                "CREATE CONSTRAINT document_id_unique IF NOT EXISTS "
                "FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
                # User/Person constraints
                "CREATE CONSTRAINT user_username_unique IF NOT EXISTS "
                "FOR (u:User) REQUIRE u.username IS UNIQUE",
                "CREATE CONSTRAINT person_email_unique IF NOT EXISTS "
                "FOR (p:Person) REQUIRE p.email IS UNIQUE",
                # Email constraint
                "CREATE CONSTRAINT email_message_id_unique IF NOT EXISTS "
                "FOR (e:Email) REQUIRE e.message_id IS UNIQUE",
                # Repository constraint
                "CREATE CONSTRAINT repository_name_unique IF NOT EXISTS "
                "FOR (r:Repository) REQUIRE r.full_name IS UNIQUE",
                # Post constraint
                "CREATE CONSTRAINT post_id_unique IF NOT EXISTS "
                "FOR (p:Post) REQUIRE p.post_id IS UNIQUE",
                # Entity constraint
                "CREATE CONSTRAINT entity_name_type_unique IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE (e.name, e.type) IS UNIQUE",
            ]

            # Indexes for common query patterns
            indexes = [
                # Document indexes
                "CREATE INDEX document_source_type IF NOT EXISTS "
                "FOR (d:Document) ON (d.source_type)",
                "CREATE INDEX document_timestamp IF NOT EXISTS "
                "FOR (d:Document) ON (d.timestamp)",
                "CREATE INDEX document_content_hash IF NOT EXISTS "
                "FOR (d:Document) ON (d.content_hash)",
                # User/Person indexes
                "CREATE INDEX user_platform IF NOT EXISTS FOR (u:User) ON (u.platform)",
                "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",
                # Repository indexes
                "CREATE INDEX repository_owner IF NOT EXISTS FOR (r:Repository) ON (r.owner)",
                # Issue/PR indexes
                "CREATE INDEX issue_state IF NOT EXISTS FOR (i:Issue) ON (i.state)",
                "CREATE INDEX pr_state IF NOT EXISTS FOR (pr:PullRequest) ON (pr.state)",
                # Post indexes
                "CREATE INDEX post_subreddit IF NOT EXISTS FOR (p:Post) ON (p.subreddit)",
                # Entity indexes
                "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            ]

            # Execute constraint creation
            logger.info("Creating Neo4j constraints...")
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.debug(f"Created constraint: {constraint.split()[2]}")
                except Neo4jError as e:
                    # Constraint may already exist, log and continue
                    logger.debug(f"Constraint creation skipped (may exist): {e}")

            # Execute index creation
            logger.info("Creating Neo4j indexes...")
            for index in indexes:
                try:
                    session.run(index)
                    logger.debug(f"Created index: {index.split()[2]}")
                except Neo4jError as e:
                    # Index may already exist, log and continue
                    logger.debug(f"Index creation skipped (may exist): {e}")

            logger.info("Neo4j schema initialization complete")

    def create_document_node(self, doc_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Create or update a Document node in the graph.

        Args:
            doc_id: Unique document identifier
            properties: Document properties (title, source_type, content_hash, etc.)

        Returns:
            Created node properties

        Raises:
            Neo4jError: If node creation fails
        """
        query = """
        MERGE (d:Document {doc_id: $doc_id})
        SET d += $properties
        RETURN d
        """

        with self.driver.session() as session:
            result = session.execute_write(
                self._create_node_tx, query, doc_id=doc_id, properties=properties
            )
            logger.debug(f"Upserted Document node: {doc_id}")
            return result

    def create_entity_node(
        self, name: str, entity_type: str, properties: dict[str, Any]
    ) -> dict[str, Any]:
        """Create an Entity node in the graph.

        Args:
            name: Entity name
            entity_type: Entity type (PERSON, ORGANIZATION, LOCATION, etc.)
            properties: Additional entity properties

        Returns:
            Created node properties

        Raises:
            Neo4jError: If node creation fails
        """
        query = """
        MERGE (e:Entity {name: $name, type: $type})
        ON CREATE SET e += $properties
        RETURN e
        """

        with self.driver.session() as session:
            result = session.execute_write(
                self._create_node_tx,
                query,
                name=name,
                type=entity_type,
                properties=properties,
            )
            logger.debug(f"Created Entity node: {name} ({entity_type})")
            return result

    def create_nodes_batch(self, nodes: list[dict[str, Any]]) -> int:
        """Create multiple nodes in a batch using UNWIND for efficiency.

        Args:
            nodes: List of node dictionaries with keys:
                - label: Node label (e.g., "Document", "Entity")
                - properties: Dict of node properties

        Returns:
            Number of nodes created

        Raises:
            Neo4jError: If batch creation fails

        Example:
            nodes = [
                {"label": "Document", "properties": {"doc_id": "123", "title": "Doc 1"}},
                {"label": "Entity", "properties": {"name": "John", "type": "PERSON"}},
            ]
            count = client.create_nodes_batch(nodes)
        """
        query = """
        UNWIND $nodes as node
        CALL apoc.create.node([node.label], node.properties) YIELD node as n
        RETURN count(n) as created_count
        """

        with self.driver.session() as session:
            result = session.execute_write(self._batch_operation_tx, query, nodes=nodes)
            count: int = result.get("created_count", 0)
            logger.info(f"Created {count} nodes in batch")
            return count

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
        from_label: str = "Document",
        to_label: str = "Document",
    ) -> dict[str, Any]:
        """Create a relationship between two nodes.

        Args:
            from_id: Source node identifier (matches node's primary ID field)
            to_id: Target node identifier
            rel_type: Relationship type (e.g., "AUTHORED", "REFERENCES")
            properties: Optional relationship properties
            from_label: Label of source node (default: Document)
            to_label: Label of target node (default: Document)

        Returns:
            Created relationship properties

        Raises:
            Neo4jError: If relationship creation fails
        """
        # Determine ID field based on label
        from_id_field = self._get_id_field_for_label(from_label)
        to_id_field = self._get_id_field_for_label(to_label)

        query = f"""
        MATCH (from:{from_label} {{{from_id_field}: $from_id}})
        MATCH (to:{to_label} {{{to_id_field}: $to_id}})
        CREATE (from)-[r:{rel_type}]->(to)
        """

        if properties:
            query += " SET r += $properties"

        query += " RETURN r"

        with self.driver.session() as session:
            result = session.execute_write(
                self._create_relationship_tx,
                query,
                from_id=from_id,
                to_id=to_id,
                properties=properties or {},
            )
            logger.debug(f"Created relationship: ({from_label})-[{rel_type}]->({to_label})")
            return result

    def create_relationships_batch(self, relationships: list[dict[str, Any]]) -> int:
        """Create multiple relationships in a batch using UNWIND.

        Args:
            relationships: List of relationship dictionaries with keys:
                - from_id: Source node identifier
                - to_id: Target node identifier
                - type: Relationship type
                - properties: Optional relationship properties
                - from_label: Source node label (optional, default: Document)
                - to_label: Target node label (optional, default: Document)

        Returns:
            Number of relationships created

        Raises:
            Neo4jError: If batch creation fails

        Example:
            rels = [
                {
                    "from_id": "doc1",
                    "to_id": "doc2",
                    "type": "REFERENCES",
                    "properties": {"weight": 0.9}
                }
            ]
            count = client.create_relationships_batch(rels)
        """
        query = """
        UNWIND $relationships as rel
        MATCH (from {doc_id: rel.from_id})
        MATCH (to {doc_id: rel.to_id})
        CALL apoc.create.relationship(from, rel.type, rel.properties, to) YIELD rel as r
        RETURN count(r) as created_count
        """

        with self.driver.session() as session:
            result = session.execute_write(
                self._batch_operation_tx, query, relationships=relationships
            )
            count: int = result.get("created_count", 0)
            logger.info(f"Created {count} relationships in batch")
            return count

    def traverse_relationships(
        self,
        start_node_id: str,
        rel_types: list[str] | None = None,
        depth: int = 1,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        """Traverse relationships from a starting node.

        Args:
            start_node_id: Starting node doc_id
            rel_types: List of relationship types to follow (None = all types)
            depth: Maximum traversal depth (default: 1)
            direction: Traversal direction ("outgoing", "incoming", "both")

        Returns:
            List of connected nodes with their properties

        Raises:
            Neo4jError: If traversal fails
        """
        # Build relationship pattern based on direction
        if direction == "outgoing":
            rel_pattern = "-[r]->"
        elif direction == "incoming":
            rel_pattern = "<-[r]-"
        else:  # both
            rel_pattern = "-[r]-"

        # Add relationship type filter if specified
        if rel_types:
            rel_type_filter = "|".join(rel_types)
            if direction == "both":
                rel_pattern = f"-[r:{rel_type_filter}]-"
            else:
                rel_pattern = rel_pattern.replace("[r]", f"[r:{rel_type_filter}]")

        query = f"""
        MATCH path = (start:Document {{doc_id: $start_node_id}})
        {rel_pattern}(connected)
        WHERE length(path) <= $depth
        RETURN DISTINCT connected, type(r) as relationship_type, length(path) as distance
        ORDER BY distance
        """

        with self.driver.session() as session:
            result = session.execute_read(
                self._traverse_relationships_tx,
                query,
                start_node_id=start_node_id,
                depth=depth,
            )
            logger.debug(
                f"Traversed relationships from {start_node_id}: found {len(result)} connected nodes"
            )
            return result

    def find_related_documents(
        self, doc_id: str, max_depth: int = 2, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Find documents related to a given document through graph traversal.

        This method finds documents connected through various relationship paths:
        - Direct references (REFERENCES, REPLIED_TO)
        - Shared entities (MENTIONS same entities)
        - Shared authors (same AUTHORED relationships)

        Args:
            doc_id: Document identifier to start from
            max_depth: Maximum relationship depth to traverse
            limit: Maximum number of related documents to return

        Returns:
            List of related documents with relevance scores

        Raises:
            Neo4jError: If query fails
        """
        query = """
        MATCH (start:Document {doc_id: $doc_id})

        CALL {
            WITH start
            OPTIONAL MATCH p=(start)-[*1..2]-(related1:Document)
            RETURN [row IN collect({related: related1, path: p})
                    WHERE row.related IS NOT NULL
                      AND row.path IS NOT NULL
                      AND all(rel IN relationships(row.path) WHERE type(rel) IN $reference_types)
                    | row.related] AS related_refs
        }

        CALL {
            WITH start
            OPTIONAL MATCH (start)-[rel1]->(entity:Entity)<-[rel2]-(related2:Document)
            RETURN [row IN collect({related: related2, rel1: rel1, rel2: rel2})
                    WHERE row.related IS NOT NULL
                      AND row.rel1 IS NOT NULL AND row.rel2 IS NOT NULL
                      AND type(row.rel1) IN $mention_types
                      AND type(row.rel2) IN $mention_types
                    | row.related] AS related_mentions
        }

        CALL {
            WITH start
            OPTIONAL MATCH (start)<-[rel1]-(author)-[rel2]->(related3:Document)
            RETURN [row IN collect({related: related3, rel1: rel1, rel2: rel2})
                    WHERE row.related IS NOT NULL
                      AND row.rel1 IS NOT NULL AND row.rel2 IS NOT NULL
                      AND type(row.rel1) IN $author_types
                      AND type(row.rel2) IN $author_types
                    | row.related] AS related_authors
        }

        WITH start, (
            coalesce(related_refs, []) +
            coalesce(related_mentions, []) +
            coalesce(related_authors, [])
        ) AS all_related

        UNWIND all_related AS related
        WITH start, related
        WHERE related IS NOT NULL AND related.doc_id <> start.doc_id

        WITH related,
             count(*) AS connection_count,
             related.source_type AS source_type

        RETURN related.doc_id AS doc_id,
               related.title AS title,
               related.source_type AS source_type,
               related.timestamp AS timestamp,
               connection_count AS relevance_score
        ORDER BY relevance_score DESC, timestamp DESC
        LIMIT $limit
        """

        reference_types = ["REFERENCES", "REPLIED_TO"]
        mention_types = ["MENTIONS"]
        author_types = ["AUTHORED"]

        with self.driver.session() as session:
            result = session.execute_read(
                self._find_related_documents_tx,
                query,
                doc_id=doc_id,
                limit=limit,
                reference_types=reference_types,
                mention_types=mention_types,
                author_types=author_types,
            )
            logger.debug(f"Found {len(result)} related documents for {doc_id}")
            return result

    def get_node_counts(self) -> dict[str, int]:
        """Get counts of nodes by label.

        Returns:
            Dictionary mapping node labels to counts

        Example:
            {"Document": 1000, "User": 50, "Entity": 200}
        """
        query = """
        CALL db.labels() YIELD label
        CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {})
        YIELD value
        RETURN label, value.count as count
        ORDER BY count DESC
        """

        with self.driver.session() as session:
            result = session.execute_read(self._get_counts_tx, query)
            logger.debug(f"Node counts: {result}")
            return result

    # =========================================================================
    # Transaction Functions (executed within managed transactions)
    # =========================================================================

    @staticmethod
    def _create_node_tx(tx: Any, /, query: str, **params: Any) -> dict[str, Any]:
        """Transaction function for creating a node.

        Args:
            tx: Neo4j transaction (positional-only)
            query: Cypher query
            **params: Query parameters

        Returns:
            Node properties
        """
        result = tx.run(query, **params)
        record = result.single()
        if record:
            node = record[0]
            return dict(node)
        return {}

    @staticmethod
    def _create_relationship_tx(tx: Any, /, query: str, **params: Any) -> dict[str, Any]:
        """Transaction function for creating a relationship.

        Args:
            tx: Neo4j transaction (positional-only)
            query: Cypher query
            **params: Query parameters

        Returns:
            Relationship properties
        """
        result = tx.run(query, **params)
        record = result.single()
        if record:
            rel = record[0]
            return dict(rel)
        return {}

    @staticmethod
    def _batch_operation_tx(tx: Any, /, query: str, **params: Any) -> dict[str, Any]:
        """Transaction function for batch operations.

        Args:
            tx: Neo4j transaction (positional-only)
            query: Cypher query
            **params: Query parameters

        Returns:
            Operation result
        """
        result = tx.run(query, **params)
        record = result.single()
        if record:
            return dict(record)
        return {}

    @staticmethod
    def _traverse_relationships_tx(tx: Any, /, query: str, **params: Any) -> list[dict[str, Any]]:
        """Transaction function for relationship traversal.

        Args:
            tx: Neo4j transaction (positional-only)
            query: Cypher query
            **params: Query parameters

        Returns:
            List of connected nodes
        """
        result = tx.run(query, **params)
        nodes = []
        for record in result:
            node = record["connected"]
            node_dict = dict(node)
            node_dict["relationship_type"] = record["relationship_type"]
            node_dict["distance"] = record["distance"]
            nodes.append(node_dict)
        return nodes

    @staticmethod
    def _find_related_documents_tx(tx: Any, /, query: str, **params: Any) -> list[dict[str, Any]]:
        """Transaction function for finding related documents.

        Args:
            tx: Neo4j transaction (positional-only)
            query: Cypher query
            **params: Query parameters

        Returns:
            List of related documents
        """
        result = tx.run(query, **params)
        return [dict(record) for record in result]

    @staticmethod
    def _get_counts_tx(tx: Any, /, query: str) -> dict[str, int]:
        """Transaction function for getting node counts.

        Args:
            tx: Neo4j transaction (positional-only)
            query: Cypher query

        Returns:
            Dictionary mapping labels to counts
        """
        result = tx.run(query)
        counts = {}
        for record in result:
            counts[record["label"]] = record["count"]
        return counts

    # =========================================================================
    # Helper Methods
    # =========================================================================

    @staticmethod
    def _get_id_field_for_label(label: str) -> str:
        """Get the ID field name for a given node label.

        Args:
            label: Node label

        Returns:
            ID field name
        """
        id_field_map = {
            "Document": "doc_id",
            "User": "username",
            "Person": "email",
            "Email": "message_id",
            "Repository": "full_name",
            "Post": "post_id",
            "Comment": "comment_id",
            "Entity": "name",
        }
        return id_field_map.get(label, "id")

    def __enter__(self) -> "Neo4jClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - close connection."""
        self.close()


# Export public API
__all__ = ["Neo4jClient"]
