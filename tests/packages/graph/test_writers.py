"""Tests for batched Neo4j writers."""

from unittest.mock import AsyncMock, Mock

import pytest

from packages.graph.writers import BatchedGraphWriter


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    client = Mock()
    client.execute_query = AsyncMock(return_value=[{"created_count": 100}])
    return client


class TestBatchedGraphWriter:
    """Test batched UNWIND operations."""

    @pytest.mark.asyncio
    async def test_batch_write_nodes(self, mock_neo4j_client):
        """Test batched node writing."""
        writer = BatchedGraphWriter(mock_neo4j_client, batch_size=2000)

        nodes = [{"name": f"service-{i}", "version": "v1"} for i in range(5000)]

        result = await writer.batch_write_nodes(
            label="Service",
            nodes=nodes,
            unique_key="name",
        )

        assert result["total_written"] == 5000
        # Should have made 3 batches (2000 + 2000 + 1000)
        assert mock_neo4j_client.execute_query.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_write_relationships(self, mock_neo4j_client):
        """Test batched relationship writing."""
        writer = BatchedGraphWriter(mock_neo4j_client, batch_size=2000)

        relationships = [
            {
                "source_value": f"api-{i}",
                "target_value": f"db-{i}",
                "rel_properties": {"type": "runtime"},
            }
            for i in range(3000)
        ]

        result = await writer.batch_write_relationships(
            source_label="Service",
            source_key="name",
            target_label="Service",
            target_key="name",
            rel_type="DEPENDS_ON",
            relationships=relationships,
        )

        assert result["total_written"] == 3000
        # Should have made 2 batches (2000 + 1000)
        assert mock_neo4j_client.execute_query.call_count == 2
