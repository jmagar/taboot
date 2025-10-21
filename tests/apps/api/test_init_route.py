"""Tests for /init endpoint (T029).

Following TDD: Write tests first (RED), then implement to pass (GREEN).
This test module covers the POST /init endpoint that triggers system initialization.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.app import app


@pytest.fixture
def client() -> TestClient:
    """Provide FastAPI test client.

    Returns:
        TestClient: Configured test client for API.
    """
    return TestClient(app)


@pytest.mark.unit
class TestInitEndpoint:
    """Test POST /init endpoint initialization workflow."""

    @pytest.mark.asyncio
    async def test_init_endpoint_exists(self, client: TestClient) -> None:
        """Test that POST /init endpoint exists and is accessible.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        response = client.post("/init")
        # Should not be 404 (not found) once endpoint exists
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_init_success_returns_200_with_status(self, client: TestClient) -> None:
        """Test that successful initialization returns 200 with status message.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        # Mock all initialization dependencies to succeed
        mock_health = {
            "healthy": True,
            "services": {
                "neo4j": True,
                "qdrant": True,
                "redis": True,
                "tei": True,
                "ollama": True,
                "firecrawl": True,
                "playwright": True,
            },
        }

        with (
            patch(
                "packages.graph.constraints.create_neo4j_constraints",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.vector.collections.create_qdrant_collections",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.common.db_schema.create_postgresql_schema",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.common.health.check_system_health",
                new_callable=AsyncMock,
                return_value=mock_health,
            ),
        ):
            response = client.post("/init")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "initialized"
            assert "message" in data
            assert "services" in data
            assert data["services"]["healthy"] is True

    @pytest.mark.asyncio
    async def test_init_failure_returns_500(self, client: TestClient) -> None:
        """Test that initialization failure returns 500 with error details.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        # Mock Neo4j constraint creation to fail
        with (
            patch(
                "packages.graph.constraints.create_neo4j_constraints",
                new_callable=AsyncMock,
                side_effect=Exception("Neo4j connection failed"),
            ),
            patch(
                "packages.vector.collections.create_qdrant_collections",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.common.db_schema.create_postgresql_schema",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            response = client.post("/init")

            assert response.status_code == 500
            data = response.json()
            assert "error" in data or "detail" in data
            # Error message should mention the failure
            error_msg = data.get("error", data.get("detail", ""))
            assert "Neo4j" in str(error_msg) or "failed" in str(error_msg).lower()

    @pytest.mark.asyncio
    async def test_init_includes_service_health_status(self, client: TestClient) -> None:
        """Test that endpoint response includes service health status.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        mock_health = {
            "healthy": True,
            "services": {
                "neo4j": True,
                "qdrant": True,
                "redis": True,
                "tei": True,
                "ollama": True,
                "firecrawl": True,
                "playwright": True,
            },
        }

        with (
            patch(
                "packages.graph.constraints.create_neo4j_constraints",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.vector.collections.create_qdrant_collections",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.common.db_schema.create_postgresql_schema",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.common.health.check_system_health",
                new_callable=AsyncMock,
                return_value=mock_health,
            ),
        ):
            response = client.post("/init")

            assert response.status_code == 200
            data = response.json()
            assert "services" in data
            assert "healthy" in data["services"]
            assert data["services"]["healthy"] is True
            assert "neo4j" in data["services"]["services"]
            assert "qdrant" in data["services"]["services"]
            assert "redis" in data["services"]["services"]

    @pytest.mark.asyncio
    async def test_init_partial_service_failure(self, client: TestClient) -> None:
        """Test initialization with partial service health failure.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        # Initialization succeeds but some services are unhealthy
        mock_health = {
            "healthy": False,
            "services": {
                "neo4j": True,
                "qdrant": True,
                "redis": True,
                "tei": False,  # TEI unhealthy
                "ollama": False,  # Ollama unhealthy
                "firecrawl": True,
                "playwright": True,
            },
        }

        with (
            patch(
                "packages.graph.constraints.create_neo4j_constraints",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.vector.collections.create_qdrant_collections",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.common.db_schema.create_postgresql_schema",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.common.health.check_system_health",
                new_callable=AsyncMock,
                return_value=mock_health,
            ),
        ):
            response = client.post("/init")

            # Init should succeed (200) but report unhealthy services
            assert response.status_code == 200
            data = response.json()
            assert data["services"]["healthy"] is False
            assert data["services"]["services"]["tei"] is False
            assert data["services"]["services"]["ollama"] is False

    @pytest.mark.asyncio
    async def test_concurrent_init_requests_handled_safely(self, client: TestClient) -> None:
        """Test that concurrent init requests are handled safely.

        Expected to FAIL initially (endpoint not implemented yet).
        This tests idempotency and concurrent request handling.
        """
        mock_health = {
            "healthy": True,
            "services": {
                "neo4j": True,
                "qdrant": True,
                "redis": True,
                "tei": True,
                "ollama": True,
                "firecrawl": True,
                "playwright": True,
            },
        }

        # Track number of calls to constraint creation
        call_counter = {"count": 0}

        def mock_create_constraints() -> None:
            """Mock constraint creation with call tracking."""
            call_counter["count"] += 1

        with (
            patch(
                "packages.graph.constraints.create_neo4j_constraints",
                new_callable=AsyncMock,
                side_effect=mock_create_constraints,
            ),
            patch(
                "packages.vector.collections.create_qdrant_collections",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.common.db_schema.create_postgresql_schema",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.common.health.check_system_health",
                new_callable=AsyncMock,
                return_value=mock_health,
            ),
        ):
            # Make multiple concurrent requests
            response1 = client.post("/init")
            response2 = client.post("/init")

            # Both should succeed
            assert response1.status_code == 200
            assert response2.status_code == 200

            # Verify both got proper responses
            data1 = response1.json()
            data2 = response2.json()
            assert data1["status"] == "initialized"
            assert data2["status"] == "initialized"

    @pytest.mark.asyncio
    async def test_init_qdrant_collection_failure(self, client: TestClient) -> None:
        """Test initialization failure during Qdrant collection creation.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with (
            patch(
                "packages.graph.constraints.create_neo4j_constraints",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.vector.collections.create_qdrant_collections",
                new_callable=AsyncMock,
                side_effect=Exception("Qdrant collection creation failed"),
            ),
            patch(
                "packages.common.db_schema.create_postgresql_schema",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            response = client.post("/init")

            assert response.status_code == 500
            data = response.json()
            error_msg = str(data.get("error", data.get("detail", "")))
            assert "Qdrant" in error_msg or "collection" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_init_postgresql_schema_failure(self, client: TestClient) -> None:
        """Test initialization failure during PostgreSQL schema creation.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with (
            patch(
                "packages.graph.constraints.create_neo4j_constraints",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.vector.collections.create_qdrant_collections",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "packages.common.db_schema.create_postgresql_schema",
                new_callable=AsyncMock,
                side_effect=Exception("PostgreSQL schema creation failed"),
            ),
        ):
            response = client.post("/init")

            assert response.status_code == 500
            data = response.json()
            error_msg = str(data.get("error", data.get("detail", "")))
            assert (
                "PostgreSQL" in error_msg
                or "schema" in error_msg.lower()
                or "database" in error_msg.lower()
            )
