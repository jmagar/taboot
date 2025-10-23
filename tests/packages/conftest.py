"""Shared fixtures for package-level tests."""

from pathlib import Path

import pytest
from neo4j import GraphDatabase
from qdrant_client import QdrantClient


@pytest.fixture(scope="session")
def contracts_root() -> Path:
    """Root directory for contract files used across package tests."""

    return (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "001-taboot-rag-platform"
        / "contracts"
    )


@pytest.fixture(scope="session")
def neo4j_constraints_path(contracts_root: Path) -> Path:
    """Path to the Neo4j constraints contract."""

    return contracts_root / "neo4j-constraints.cypher"


@pytest.fixture(scope="session")
def collection_config_path(contracts_root: Path) -> Path:
    """Path to the Qdrant collection configuration contract."""

    return contracts_root / "qdrant-collection.json"


@pytest.fixture(scope="session")
def postgres_schema_path(contracts_root: Path) -> Path:
    """Path to the PostgreSQL schema contract."""

    return contracts_root / "postgresql-schema.sql"


@pytest.fixture(scope="session")
def qdrant_client():
    """Real Qdrant client for integration tests."""
    from qdrant_client.models import Distance, VectorParams

    client = QdrantClient(url="http://localhost:7000")

    # Create test collection if it doesn't exist
    collections = client.get_collections().collections
    if not any(c.name == "test_documents" for c in collections):
        client.create_collection(
            collection_name="test_documents",
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )

    yield client
    client.close()


@pytest.fixture(scope="session")
def neo4j_client():
    """Real Neo4j driver for integration tests."""
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "changeme")
    )
    yield driver
    driver.close()
