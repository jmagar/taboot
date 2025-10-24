"""Integration tests for API authentication."""

import pytest


def test_ingest_requires_auth(client) -> None:
    """Test POST /ingest requires API key."""
    response = client.post(
        "/ingest/",
        json={
            "source_type": "web",
            "source_target": "https://example.com",
            "limit": 5,
        },
    )
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ingest_with_valid_key(client, valid_api_key) -> None:
    """Test POST /ingest succeeds with valid API key."""
    response = client.post(
        "/ingest/",
        json={
            "source_type": "web",
            "source_target": "https://example.com",
            "limit": 5,
        },
        headers={"X-API-Key": valid_api_key},
    )
    assert response.status_code == 202
    assert "job_id" in response.json()


def test_query_requires_auth(client) -> None:
    """Test POST /query requires API key."""
    response = client.post(
        "/query",
        json={"question": "test question"},
    )
    assert response.status_code == 401
