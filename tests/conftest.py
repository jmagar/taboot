"""Shared pytest fixtures for LlamaCrawl tests."""

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, Mock

import pytest
from faker import Faker

from llamacrawl.config import Config, SourceConfig
from llamacrawl.models.document import Document, DocumentMetadata

fake = Faker()


# =============================================================================
# Mock Configuration Fixtures
# =============================================================================


@pytest.fixture
def mock_config() -> Config:
    """Provide test configuration with all settings."""
    return Config(
        redis_url="redis://localhost:6379",
        qdrant_url="http://localhost:7000",
        neo4j_uri="bolt://localhost:7687",
        neo4j_password="changeme",
        tei_embedding_url="http://localhost:8080",
        tei_reranker_url="http://localhost:8081",
        ollama_url="http://localhost:11434",
        firecrawl_api_url="http://localhost:3002",
        firecrawl_api_key="test-key",
        sources={
            "gmail": SourceConfig(
                type="gmail",
                enabled=True,
                config={
                    "labels": ["INBOX", "SENT"],
                    "max_results": 500,
                    "include_attachments_metadata": True,
                },
            ),
            "github": SourceConfig(
                type="github",
                enabled=True,
                config={
                    "owner": "test-owner",
                    "repo": "test-repo",
                    "include_issues": True,
                    "include_prs": True,
                },
            ),
        },
        ingestion={"chunk_size": 8192, "chunk_overlap": 512, "batch_size": 100},
        query={"top_k": 20, "top_n": 5, "max_graph_depth": 2},
    )


# =============================================================================
# Mock Storage Fixtures
# =============================================================================


@pytest.fixture
def mock_redis_client() -> Mock:
    """Provide mocked Redis client."""
    client = MagicMock()
    # Cursor operations
    client.get.return_value = None
    client.set.return_value = True
    client.delete.return_value = 1
    client.exists.return_value = 0
    # Lock operations
    client.setnx.return_value = True
    # Hash operations (for deduplication)
    client.hget.return_value = None
    client.hset.return_value = 1
    return client


@pytest.fixture
def mock_qdrant_client() -> Mock:
    """Provide mocked Qdrant client."""
    client = MagicMock()
    # Collection operations
    client.collection_exists.return_value = True
    client.create_collection.return_value = True
    client.get_collection.return_value = {"vectors_count": 0}
    # Vector operations
    client.upsert.return_value = {"status": "completed"}
    client.search.return_value = []
    return client


@pytest.fixture
def mock_neo4j_client() -> Mock:
    """Provide mocked Neo4j client."""
    client = MagicMock()
    # Session/transaction mocks
    session = MagicMock()
    client.session.return_value.__enter__.return_value = session
    session.run.return_value = []
    return client


@pytest.fixture
def mock_tei_client() -> Mock:
    """Provide mocked TEI embedding client."""
    client = MagicMock()
    # Return fake embeddings (1024-dim vector)
    client.embed.return_value = [[0.1] * 1024]
    client.embed_batch.return_value = [[0.1] * 1024] * 10
    return client


@pytest.fixture
def mock_ollama_client() -> Mock:
    """Provide mocked Ollama LLM client."""
    client = MagicMock()
    client.generate.return_value = {"response": "Test answer"}
    return client


# =============================================================================
# Integration Test Fixtures (Real Services)
# =============================================================================


@pytest.fixture(scope="session")
def docker_services() -> Generator[None, None, None]:
    """Ensure Docker Compose services are running."""
    # Check if docker-compose is available
    try:
        subprocess.run(["docker", "compose", "version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("Docker Compose not available")

    # Start services
    subprocess.run(["docker", "compose", "up", "-d"], check=True)

    # Wait for healthchecks
    max_wait = 60  # seconds
    import time

    start = time.time()
    while time.time() - start < max_wait:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
        )
        # Simple check - if no errors and services are up, continue
        if result.returncode == 0:
            time.sleep(5)  # Give services time to stabilize
            break
        time.sleep(2)

    yield

    # Cleanup handled by Docker Compose down (manual)


@pytest.fixture
def redis_client(docker_services: None) -> Generator[Any, None, None]:
    """Provide real Redis client for integration tests."""
    import redis

    client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    yield client
    # Cleanup test data
    for key in client.scan_iter("test:*"):
        client.delete(key)


@pytest.fixture
def qdrant_client(docker_services: None) -> Generator[Any, None, None]:
    """Provide real Qdrant client for integration tests."""
    from qdrant_client import QdrantClient

    client = QdrantClient(url="http://localhost:7000")
    yield client
    # Cleanup test collections
    collections = client.get_collections().collections
    for collection in collections:
        if collection.name.startswith("test_"):
            client.delete_collection(collection.name)


@pytest.fixture
def neo4j_client(docker_services: None) -> Generator[Any, None, None]:
    """Provide real Neo4j client for integration tests."""
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "changeme"))
    yield driver
    # Cleanup test data
    with driver.session() as session:
        session.run("MATCH (n:TestNode) DETACH DELETE n")
    driver.close()


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_document() -> Document:
    """Provide a sample document for testing."""
    content = fake.text(max_nb_chars=500)
    return Document(
        doc_id=f"test_{fake.uuid4()}",
        title=fake.sentence(),
        content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        metadata=DocumentMetadata(
            source_type="gmail",
            source_url=fake.url(),
            timestamp=datetime.now(),
            extra={"test": True},
        ),
    )


@pytest.fixture
def sample_documents() -> list[Document]:
    """Provide multiple sample documents."""
    documents = []
    for i in range(10):
        content = fake.text(max_nb_chars=500)
        documents.append(
            Document(
                doc_id=f"test_{i}",
                title=fake.sentence(),
                content=content,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
                metadata=DocumentMetadata(
                    source_type="gmail",
                    source_url=fake.url(),
                    timestamp=datetime.now(),
                    extra={"test": True},
                ),
            )
        )
    return documents


@pytest.fixture
def sample_gmail_message() -> dict[str, Any]:
    """Provide a sample Gmail API message response."""
    message_id = fake.uuid4()
    return {
        "id": message_id,
        "threadId": fake.uuid4(),
        "labelIds": ["INBOX"],
        "snippet": fake.text(max_nb_chars=100),
        "payload": {
            "headers": [
                {"name": "Subject", "value": fake.sentence()},
                {"name": "From", "value": fake.email()},
                {"name": "To", "value": fake.email()},
                {"name": "Date", "value": "Wed, 02 Oct 2025 12:00:00 -0700"},
            ],
            "body": {"data": fake.text(max_nb_chars=200).encode().hex()},
        },
        "internalDate": str(int(datetime.now().timestamp() * 1000)),
    }


@pytest.fixture
def sample_github_issue() -> dict[str, Any]:
    """Provide a sample GitHub issue response."""
    return {
        "id": fake.random_int(),
        "number": fake.random_int(min=1, max=1000),
        "title": fake.sentence(),
        "body": fake.text(),
        "state": "open",
        "created_at": fake.iso8601(),
        "updated_at": fake.iso8601(),
        "user": {"login": fake.user_name()},
        "html_url": fake.url(),
    }


# =============================================================================
# Helper Fixtures
# =============================================================================


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    """Create a temporary config file."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
sources:
  gmail:
    type: gmail
    enabled: true
    config:
      labels: ["INBOX"]
      max_results: 100

ingestion:
  chunk_size: 4096
  chunk_overlap: 256
  batch_size: 50
"""
    )
    return config_path


@pytest.fixture(autouse=True)
def reset_config_singleton() -> Generator[None, None, None]:
    """Reset config singleton between tests."""
    from llamacrawl import config

    # Store original
    original = getattr(config, "_config", None)
    # Reset
    if hasattr(config, "_config"):
        delattr(config, "_config")
    yield
    # Restore or clear
    if original:
        config._config = original
    elif hasattr(config, "_config"):
        delattr(config, "_config")
