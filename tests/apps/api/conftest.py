"""Fixtures for API tests."""

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set environment variables before TestClient is created."""
    # Ensure config can load without validation errors
    os.environ["RERANKER_BATCH_SIZE"] = "16"
    os.environ["OLLAMA_PORT"] = "11434"
    os.environ["FIRECRAWL_API_URL"] = "http://localhost:3002"
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["QDRANT_URL"] = "http://localhost:6333"
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["TEI_EMBEDDING_URL"] = "http://localhost:80"
    yield


@pytest.fixture(scope="module")
def client():
    """Create FastAPI TestClient for API tests.

    Creates a test client after environment variables are set.
    This ensures get_config() can load successfully during app startup.
    """
    from apps.api.app import app

    with TestClient(app) as test_client:
        yield test_client
