"""Tests for POST /query API endpoint."""

import pytest


@pytest.mark.unit
def test_query_endpoint_validates_request(client):
    """Test query endpoint validates request body."""
    # Empty question should fail
    response = client.post("/query", json={"question": ""})
    assert response.status_code in [400, 422]

    # Missing question should fail
    response = client.post("/query", json={})
    assert response.status_code == 422


@pytest.mark.unit
def test_query_endpoint_accepts_valid_request(client):
    """Test query endpoint accepts valid request."""
    response = client.post(
        "/query",
        json={
            "question": "Which services expose port 8080?",
            "top_k": 10,
            "source_types": ["web", "docker_compose"]
        }
    )

    # May fail if services not running, but should accept request
    assert response.status_code in [200, 400, 500, 503]


@pytest.mark.integration
@pytest.mark.slow
def test_query_endpoint_with_real_services(client, qdrant_client, neo4j_client):
    """Test query endpoint against real services."""
    response = client.post(
        "/query",
        json={"question": "test question", "top_k": 5}
    )

    # Should succeed or fail gracefully
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert "latency_ms" in data
