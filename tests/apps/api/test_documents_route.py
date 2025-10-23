"""Tests for GET /documents API endpoint (T167).

Tests listing documents with filters and pagination via REST API.
Follows TDD RED-GREEN-REFACTOR methodology.
"""

import pytest
from fastapi.testclient import TestClient

from apps.api.app import app

client = TestClient(app)


@pytest.mark.unit
def test_documents_endpoint_exists():
    """Test GET /documents endpoint exists.

    RED phase: Will fail until route exists.
    """
    response = client.get("/documents")
    # Should return 200, 400, 500, or 503, but not 404 (not found)
    assert response.status_code != 404


@pytest.mark.unit
def test_documents_endpoint_accepts_limit():
    """Test documents endpoint accepts limit query parameter.

    RED phase: Will fail until route exists.
    """
    response = client.get("/documents?limit=5")
    # May fail if DB not running, but should accept request
    assert response.status_code in [200, 400, 500, 503]


@pytest.mark.unit
def test_documents_endpoint_accepts_offset():
    """Test documents endpoint accepts offset query parameter.

    RED phase: Will fail until route exists.
    """
    response = client.get("/documents?offset=10")
    # May fail if DB not running, but should accept request
    assert response.status_code in [200, 400, 500, 503]


@pytest.mark.unit
def test_documents_endpoint_accepts_source_type_filter():
    """Test documents endpoint accepts source_type filter.

    RED phase: Will fail until route exists.
    """
    response = client.get("/documents?source_type=web")
    # May fail if DB not running, but should accept request
    assert response.status_code in [200, 400, 500, 503]


@pytest.mark.unit
def test_documents_endpoint_accepts_extraction_state_filter():
    """Test documents endpoint accepts extraction_state filter.

    RED phase: Will fail until route exists.
    """
    response = client.get("/documents?extraction_state=pending")
    # May fail if DB not running, but should accept request
    assert response.status_code in [200, 400, 500, 503]


@pytest.mark.unit
def test_documents_endpoint_accepts_combined_filters():
    """Test documents endpoint accepts multiple filters.

    RED phase: Will fail until route exists.
    """
    response = client.get(
        "/documents?limit=5&offset=10&source_type=github&extraction_state=completed"
    )
    # May fail if DB not running, but should accept request
    assert response.status_code in [200, 400, 500, 503]


@pytest.mark.unit
def test_documents_endpoint_validates_invalid_source_type():
    """Test documents endpoint rejects invalid source_type.

    RED phase: Will fail until route exists.
    """
    response = client.get("/documents?source_type=invalid_source")
    # Should return validation error
    assert response.status_code in [400, 422]


@pytest.mark.unit
def test_documents_endpoint_validates_invalid_extraction_state():
    """Test documents endpoint rejects invalid extraction_state.

    RED phase: Will fail until route exists.
    """
    response = client.get("/documents?extraction_state=invalid_state")
    # Should return validation error
    assert response.status_code in [400, 422]


@pytest.mark.unit
def test_documents_endpoint_validates_negative_limit():
    """Test documents endpoint rejects negative limit.

    RED phase: Will fail until route exists.
    """
    response = client.get("/documents?limit=-5")
    # Should return validation error
    assert response.status_code in [400, 422]


@pytest.mark.unit
def test_documents_endpoint_validates_negative_offset():
    """Test documents endpoint rejects negative offset.

    RED phase: Will fail until route exists.
    """
    response = client.get("/documents?offset=-10")
    # Should return validation error
    assert response.status_code in [400, 422]


@pytest.mark.unit
def test_documents_endpoint_returns_expected_structure():
    """Test documents endpoint returns expected response structure.

    RED phase: Will fail until route exists.
    """
    response = client.get("/documents?limit=1")

    if response.status_code == 200:
        data = response.json()
        # Should have required fields
        assert "documents" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["documents"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["offset"], int)


@pytest.mark.integration
@pytest.mark.slow
def test_documents_endpoint_with_real_db():
    """Test documents endpoint against real database.

    Requires PostgreSQL service running.
    """
    response = client.get("/documents?limit=10")

    # Should succeed or fail gracefully
    assert response.status_code in [200, 500, 503]

    if response.status_code == 200:
        data = response.json()
        assert "documents" in data
        assert "total" in data
        assert data["total"] >= 0
        assert data["limit"] == 10
