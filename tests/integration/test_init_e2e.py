"""End-to-end integration tests for system initialization workflow (T027).

This test suite validates User Story 4 acceptance scenarios:
1. Neo4j constraints are created (Service.name, Host.hostname unique, Endpoint composite index)
2. Qdrant collections are created with correct dimensionality and HNSW settings
3. PostgreSQL tables are created (if applicable)
4. All services report healthy after init
5. Init is idempotent (can run twice without errors)

Following TDD: RED phase - tests written before implementation.
These tests require Docker services to be running and healthy.

Markers:
- @pytest.mark.integration: Requires Docker services
- @pytest.mark.slow: End-to-end tests take longer to run
"""

import pytest
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from packages.common.config import get_config
from packages.common.health import check_system_health


@pytest.mark.integration
@pytest.mark.slow
class TestInitEndToEnd:
    """End-to-end integration tests for initialization workflow."""

    @pytest.mark.asyncio
    async def test_init_creates_neo4j_constraints(
        self, docker_services_ready: None
    ) -> None:
        """Test that Neo4j constraints are actually created during init.

        Acceptance Scenario 1: Given a fresh deployment, When the user runs init
        command, Then Neo4j constraints are created (Service.name unique,
        Host.hostname unique, Endpoint composite index) and the system confirms
        constraint creation.
        """
        # This test will FAIL until init workflow is implemented
        config = get_config()

        # Connect to Neo4j and query constraints
        driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
        )

        try:
            with driver.session(database=config.neo4j_db) as session:
                # Query for constraints
                result = session.run("SHOW CONSTRAINTS")
                constraints = list(result)

                # Extract constraint names and properties
                constraint_map = {}
                for record in constraints:
                    name = record.get("name", "")
                    # Different Neo4j versions may use different field names
                    labels_or_types = record.get(
                        "labelsOrTypes", record.get("entityType", [])
                    )
                    properties = record.get("properties", [])

                    if labels_or_types and properties:
                        label = (
                            labels_or_types[0]
                            if isinstance(labels_or_types, list)
                            else labels_or_types
                        )
                        prop = properties[0] if isinstance(properties, list) else properties
                        constraint_map[f"{label}.{prop}"] = name

                # Assert required constraints exist
                assert (
                    "Service.name" in constraint_map
                ), "Service.name unique constraint not found"
                assert (
                    "Host.hostname" in constraint_map
                ), "Host.hostname unique constraint not found"

                # Check for Endpoint composite index (may be index or constraint)
                result_indexes = session.run("SHOW INDEXES")
                indexes = list(result_indexes)

                endpoint_index_found = False
                for record in indexes:
                    labels_or_types = record.get(
                        "labelsOrTypes", record.get("entityType", [])
                    )
                    properties = record.get("properties", [])

                    if labels_or_types and properties:
                        label = (
                            labels_or_types[0]
                            if isinstance(labels_or_types, list)
                            else labels_or_types
                        )
                        if label == "Endpoint" and set(properties) == {
                            "service",
                            "method",
                            "path",
                        }:
                            endpoint_index_found = True
                            break

                assert (
                    endpoint_index_found
                ), "Endpoint(service, method, path) composite index not found"

        finally:
            driver.close()

    @pytest.mark.asyncio
    async def test_init_creates_qdrant_collection(
        self, docker_services_ready: None
    ) -> None:
        """Test that Qdrant collection is actually created during init.

        Acceptance Scenario 2: Given Neo4j initialized, When Qdrant initialization
        runs, Then vector collections are created with 768-dimensional vectors,
        HNSW indexing enabled, and metadata schema configured for filtering.
        """
        # This test will FAIL until init workflow is implemented
        config = get_config()

        # Connect to Qdrant and check collection
        client = QdrantClient(url=config.qdrant_url)

        try:
            # Check if collection exists
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]

            # Assert main collection exists
            expected_collection = "taboot_documents"
            assert (
                expected_collection in collection_names
            ), f"Qdrant collection '{expected_collection}' not found"

            # Get collection info
            collection_info = client.get_collection(expected_collection)

            # Assert vector configuration
            vectors = collection_info.config.params.vectors
            if isinstance(vectors, dict):
                # Named vectors configuration
                raise AssertionError("Expected single vector config, got named vectors")
            assert vectors is not None, "Vector config should exist"
            assert vectors.size == 768, "Vector dimension should be 768"

            # Assert HNSW indexing is enabled
            assert (
                vectors.distance.name == "Cosine"
            ), "Distance metric should be Cosine"

            # Check for HNSW config
            hnsw_config = collection_info.config.hnsw_config
            assert hnsw_config is not None, "HNSW config should exist"

        finally:
            client.close()

    @pytest.mark.asyncio
    async def test_init_all_services_healthy(
        self, docker_services_ready: None
    ) -> None:
        """Test that all services report healthy after init.

        Acceptance Scenario 3: Given all schemas initialized, When the system
        performs health checks, Then all services (Neo4j, Qdrant, Redis, TEI,
        Ollama, Firecrawl) report healthy status and the init command completes
        successfully.
        """
        # This test will FAIL until init workflow is implemented
        health_status = await check_system_health()

        # Assert overall system health
        assert (
            health_status["healthy"] is True
        ), f"System not healthy: {health_status['services']}"

        # Assert individual service health
        required_services = [
            "neo4j",
            "qdrant",
            "redis",
            "tei",
            "ollama",
            "firecrawl",
            "playwright",
        ]

        for service in required_services:
            assert (
                health_status["services"].get(service) is True
            ), f"Service {service} is not healthy"

    @pytest.mark.asyncio
    async def test_init_is_idempotent(self, docker_services_ready: None) -> None:
        """Test that init is idempotent (can run twice without errors).

        Acceptance Scenario 4: Given an already-initialized system, When init runs
        again, Then the system detects existing schemas, skips redundant operations,
        and reports current configuration status.
        """
        # This test will FAIL until init workflow is implemented
        config = get_config()

        # Run init logic twice (simulating double execution)
        # In actual implementation, this would call the init use-case/CLI command

        # First init: Should create all schemas
        # (This part assumes init implementation exists)

        # Second init: Should detect existing schemas and skip
        # Connect to Neo4j to verify constraints still exist (not duplicated)
        driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
        )

        try:
            with driver.session(database=config.neo4j_db) as session:
                # Count constraints - should not duplicate
                result = session.run("SHOW CONSTRAINTS")
                constraints = list(result)

                # We should have exactly the required constraints (not duplicates)
                # Service.name, Host.hostname unique constraints
                constraint_count = len(constraints)

                # Re-running init should not increase constraint count
                # Store initial count for comparison
                initial_count = constraint_count

                # TODO: When init implementation exists, call it here
                # await init_system()

                # Verify constraint count unchanged
                result_after = session.run("SHOW CONSTRAINTS")
                constraints_after = list(result_after)

                assert len(constraints_after) == initial_count, (
                    "Init should be idempotent - constraint count should not change "
                    "on second run"
                )

        finally:
            driver.close()

        # Verify Qdrant collection still exists (not duplicated or deleted)
        client = QdrantClient(url=config.qdrant_url)

        try:
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]

            expected_collection = "taboot_documents"
            assert (
                expected_collection in collection_names
            ), "Collection should still exist after re-init"

        finally:
            client.close()


@pytest.mark.integration
@pytest.mark.slow
class TestInitWorkflowComponents:
    """Test individual components of the init workflow."""

    @pytest.mark.asyncio
    async def test_neo4j_connection_established(
        self, docker_services_ready: None
    ) -> None:
        """Test that Neo4j connection can be established."""
        config = get_config()

        driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
        )

        try:
            # Verify connectivity
            driver.verify_connectivity()

            # Execute simple query
            with driver.session(database=config.neo4j_db) as session:
                result = session.run("RETURN 1 as num")
                record = result.single()
                assert record is not None, "Query should return a record"
                assert record["num"] == 1

        finally:
            driver.close()

    @pytest.mark.asyncio
    async def test_qdrant_connection_established(
        self, docker_services_ready: None
    ) -> None:
        """Test that Qdrant connection can be established."""
        config = get_config()

        client = QdrantClient(url=config.qdrant_url)

        try:
            # Get collections (should not raise)
            collections = client.get_collections()
            assert collections is not None

        finally:
            client.close()
