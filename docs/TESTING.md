# Testing Guide

Comprehensive guide to testing in Taboot. Single-user system = we can break tests when refactoring (just fix them after).

## Quick Start

```bash
# Run all fast tests (default)
uv run pytest -m "not slow"

# Run everything (including slow integration tests)
uv run pytest

# Run with coverage
uv run pytest --cov=packages packages/core

# Run specific package tests
uv run pytest tests/core/
uv run pytest tests/extraction/

# Run tests matching a pattern
uv run pytest -k "test_ingest"
```

## Test Organization

```
tests/
├── core/              # Core business logic tests (TARGET: ≥85% coverage)
├── extraction/        # Extraction pipeline tests (TARGET: ≥85% coverage)
├── graph/             # Neo4j adapter tests
├── vector/            # Qdrant adapter tests
├── ingest/            # Ingestion tests
├── retrieval/         # Retrieval tests
└── integration/       # Cross-package integration tests
```

**Mirror structure**: Tests mirror `packages/` and `apps/` directory structure.

## Test Markers

Defined in `pyproject.toml` under `[tool.pytest.ini_options]`:

| Marker | Purpose | Requires Docker | Speed |
|--------|---------|-----------------|-------|
| `unit` | Fast tests with mocked dependencies | ❌ | <1s each |
| `integration` | Tests requiring real services | ✅ | 1-10s |
| `slow` | Long-running tests (>5s) | Varies | >5s |
| `gmail` | Gmail-specific tests | ✅ | Varies |
| `github` | GitHub-specific tests | ✅ | Varies |
| `reddit` | Reddit-specific tests | ✅ | Varies |
| `elasticsearch` | Elasticsearch tests | ✅ | Varies |
| `firecrawl` | Firecrawl tests | ✅ | Varies |

### Marker Usage

```python
import pytest

@pytest.mark.unit
def test_parse_document():
    """Unit test - fast, no external dependencies"""
    pass

@pytest.mark.integration
def test_neo4j_write():
    """Integration test - requires Neo4j running"""
    pass

@pytest.mark.slow
@pytest.mark.github
def test_github_full_repo_ingest():
    """Slow integration test for GitHub"""
    pass
```

### Running by Marker

```bash
# Only unit tests
uv run pytest -m unit

# Only integration tests (ensure services are up!)
docker compose ps  # verify all healthy first
uv run pytest -m integration

# Exclude slow tests (default for dev)
uv run pytest -m "not slow"

# GitHub tests only
uv run pytest -m github

# Integration but not slow
uv run pytest -m "integration and not slow"
```

## Writing Unit Tests

### Pattern: Mock External Dependencies

```python
# tests/core/use_cases/test_ingest_document.py
import pytest
from unittest.mock import Mock, MagicMock
from packages.core.use_cases.ingest_document import IngestDocumentUseCase
from packages.schemas.models import Document, Chunk

@pytest.mark.unit
def test_ingest_document_creates_nodes():
    # Arrange: Create mocks
    mock_graph = Mock()
    mock_vector = Mock()
    use_case = IngestDocumentUseCase(graph=mock_graph, vector=mock_vector)

    doc = Document(
        id="test-123",
        url="https://example.com",
        content="Test content"
    )

    # Act
    use_case.execute(doc)

    # Assert: Verify interactions
    mock_graph.create_nodes.assert_called_once()
    mock_vector.upsert_chunks.assert_called_once()

    # Verify data passed to graph
    nodes = mock_graph.create_nodes.call_args[0][0]
    assert len(nodes) > 0
    assert nodes[0].id == "test-123"
```

### Pattern: Test Data Builders

```python
# tests/builders.py
from packages.schemas.models import Document, Chunk

def build_document(
    doc_id: str = "test-doc",
    url: str = "https://example.com",
    content: str = "Test content",
    **kwargs
) -> Document:
    """Builder for test documents"""
    return Document(id=doc_id, url=url, content=content, **kwargs)

def build_chunk(
    chunk_id: str = "chunk-1",
    doc_id: str = "test-doc",
    text: str = "Chunk text",
    **kwargs
) -> Chunk:
    """Builder for test chunks"""
    return Chunk(id=chunk_id, doc_id=doc_id, text=text, **kwargs)

# Usage in tests:
@pytest.mark.unit
def test_chunk_validation():
    chunk = build_chunk(text="")  # Override defaults
    # ... test validation
```

## Writing Integration Tests

### Pattern: Docker Services Required

```python
# tests/integration/test_neo4j_integration.py
import pytest
from packages.graph.client import Neo4jClient
from packages.schemas.models import Node

@pytest.mark.integration
def test_neo4j_write_and_read():
    """Integration test - requires taboot-graph running"""
    # Arrange
    client = Neo4jClient()  # Uses env vars from .env

    test_node = Node(
        label="TestService",
        properties={"name": "test-service-123", "type": "api"}
    )

    try:
        # Act
        client.create_node(test_node)
        result = client.get_node_by_name("test-service-123")

        # Assert
        assert result is not None
        assert result.properties["type"] == "api"
    finally:
        # Cleanup
        client.delete_node("test-service-123")
```

### Pattern: Fixtures for Shared Setup

```python
# tests/conftest.py (pytest discovers automatically)
import pytest
from packages.graph.client import Neo4jClient
from packages.vector.client import QdrantClient

@pytest.fixture(scope="session")
def neo4j_client():
    """Shared Neo4j client for integration tests"""
    client = Neo4jClient()
    yield client
    # Cleanup happens after all tests

@pytest.fixture(scope="function")
def clean_neo4j(neo4j_client):
    """Clean Neo4j before each test"""
    neo4j_client.delete_all()  # CAREFUL: Only in test env!
    yield neo4j_client

@pytest.fixture
def qdrant_client():
    """Qdrant client with test collection"""
    client = QdrantClient(collection_name="test_collection")
    yield client
    client.delete_collection()  # Cleanup

# Usage:
@pytest.mark.integration
def test_graph_operations(clean_neo4j):
    clean_neo4j.create_node(...)
    # Test runs with clean database
```

### Pre-Test Checklist for Integration Tests

Before running integration tests:

```bash
# 1. Start all services
docker compose up -d

# 2. Verify all healthy
docker compose ps

# Expected output: All services show "healthy" status
# taboot-graph    healthy
# taboot-vectors  healthy
# taboot-cache    healthy
# ...

# 3. Run integration tests
uv run pytest -m integration
```

## Extraction Pipeline Testing

### Tier A (Deterministic) Tests

```python
# tests/extraction/tier_a/test_docker_compose_parser.py
import pytest
from packages.extraction.tier_a.docker_compose import DockerComposeParser

@pytest.mark.unit
def test_parse_docker_compose():
    yaml_content = """
    version: '3.8'
    services:
      api:
        image: python:3.11
        ports:
          - "8000:8000"
    """

    parser = DockerComposeParser()
    result = parser.parse(yaml_content)

    assert result.entities[0].type == "Service"
    assert result.entities[0].name == "api"
    assert result.relations[0].type == "EXPOSES"
    assert result.relations[0].properties["port"] == "8000"
```

### Tier B (spaCy) Tests

```python
# tests/extraction/tier_b/test_spacy_extractor.py
import pytest
from packages.extraction.tier_b.spacy_extractor import SpacyExtractor

@pytest.mark.unit
def test_spacy_entity_extraction():
    extractor = SpacyExtractor(model="en_core_web_md")

    text = "The Auth0 service connects to PostgreSQL database on port 5432"

    result = extractor.extract(text)

    # Should identify "Auth0" as service, "PostgreSQL" as database
    entities = result.entities
    assert any(e.type == "Service" and e.name == "Auth0" for e in entities)
    assert any(e.type == "Database" and "PostgreSQL" in e.name for e in entities)
```

### Tier C (LLM) Tests

```python
# tests/extraction/tier_c/test_llm_extractor.py
import pytest
from packages.extraction.tier_c.llm_extractor import LLMExtractor

@pytest.mark.integration
@pytest.mark.slow
def test_llm_extraction():
    """Requires Ollama service running"""
    extractor = LLMExtractor(
        model="qwen2.5:4b-instruct-q4_0",
        temperature=0.0
    )

    text = """
    The payment service depends on the user authentication API.
    It communicates via REST over HTTPS on port 8443.
    """

    result = extractor.extract(text)

    # LLM should identify service dependency relationship
    assert len(result.relations) >= 1
    rel = result.relations[0]
    assert rel.type == "DEPENDS_ON"
    assert "payment" in rel.source.lower()
    assert "authentication" in rel.target.lower()
```

## Coverage Requirements

From [constitution.md](.specify/memory/constitution.md):

- **Core packages**: ≥85% coverage (strictly enforced)
- **Extraction logic**: ≥85% coverage
- **Adapter packages**: Best effort (mocking external services is hard)

### Check Coverage

```bash
# Core package coverage (must be ≥85%)
uv run pytest --cov=packages/core --cov-report=term-missing tests/core/

# Extraction coverage (must be ≥85%)
uv run pytest --cov=packages/extraction --cov-report=term-missing tests/extraction/

# HTML report for detailed view
uv run pytest --cov=packages --cov-report=html
# Open htmlcov/index.html in browser
```

### Coverage Configuration

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "-v --tb=short --strict-markers"
testpaths = ["tests"]
```

## Common Testing Patterns

### Pattern: Parametrized Tests

```python
@pytest.mark.unit
@pytest.mark.parametrize("input_text,expected_count", [
    ("One service", 1),
    ("Service A and Service B", 2),
    ("", 0),
])
def test_service_extraction(input_text, expected_count):
    extractor = ServiceExtractor()
    result = extractor.extract(input_text)
    assert len(result.entities) == expected_count
```

### Pattern: Async Tests

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_async_ingest():
    from packages.ingest.async_reader import AsyncReader

    reader = AsyncReader()
    docs = await reader.read_batch(["url1", "url2"])

    assert len(docs) == 2
```

### Pattern: Temporary Files

```python
import tempfile
import pytest

@pytest.mark.unit
def test_file_parser(tmp_path):
    # tmp_path is a pytest fixture providing temp directory
    test_file = tmp_path / "test.yaml"
    test_file.write_text("key: value")

    parser = YAMLParser()
    result = parser.parse(str(test_file))

    assert result["key"] == "value"
```

## Troubleshooting

### "Services not healthy" Errors

```bash
# Check service status
docker compose ps

# View logs for failing service
docker compose logs taboot-graph

# Restart services
docker compose down
docker compose up -d

# Wait for health checks
sleep 30
docker compose ps
```

### "Collection not found" (Qdrant)

```bash
# Initialize collections before tests
uv run python -m packages.vector.migrations.create_collections

# Or in test setup
@pytest.fixture(scope="session", autouse=True)
def init_qdrant():
    from packages.vector.migrations import create_collections
    create_collections()
```

### "Connection refused" (Neo4j)

```bash
# Verify Neo4j is accessible
curl -f http://localhost:7474/ || echo "Neo4j not responding"

# Check if bolt port is open
nc -zv localhost 7687

# Verify credentials
docker compose logs taboot-graph | grep -i password
```

### Import Errors

```python
# ❌ Wrong - relative imports
from ..core.models import Document

# ✅ Correct - absolute imports from packages
from packages.core.models import Document
from packages.schemas.models import Chunk
```

### Slow Tests

```python
# Mark slow tests explicitly
@pytest.mark.slow
def test_full_repo_ingest():
    # This takes >5 seconds
    pass

# Run without slow tests during development
# uv run pytest -m "not slow"
```

## CI/CD Considerations

When setting up CI (future):

```yaml
# .github/workflows/test.yml example
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start services
        run: docker compose up -d

      - name: Wait for services
        run: |
          sleep 30
          docker compose ps

      - name: Run tests
        run: |
          uv sync
          uv run pytest -m "not slow"

      - name: Check coverage
        run: |
          uv run pytest --cov=packages/core --cov-fail-under=85
```

## Test Development Workflow

1. **Write test first** (TDD when possible)
   ```python
   def test_new_feature():
       # Arrange
       # Act
       # Assert
       assert False  # Fails initially
   ```

2. **Run test, watch it fail**
   ```bash
   uv run pytest tests/test_new_feature.py -v
   ```

3. **Implement feature**
   ```python
   def new_feature():
       # Implementation
       pass
   ```

4. **Run test, watch it pass**
   ```bash
   uv run pytest tests/test_new_feature.py -v
   ```

5. **Refactor if needed** (tests still pass)

## Quick Reference

| Task | Command |
|------|---------|
| Run fast tests | `uv run pytest -m "not slow"` |
| Run all tests | `uv run pytest` |
| Run with coverage | `uv run pytest --cov=packages` |
| Run specific file | `uv run pytest tests/core/test_models.py` |
| Run by pattern | `uv run pytest -k "ingest"` |
| Run verbose | `uv run pytest -v` |
| Stop on first failure | `uv run pytest -x` |
| Show print statements | `uv run pytest -s` |
| Rerun last failures | `uv run pytest --lf` |

---

**Remember**: Single-user system = breaking tests during refactoring is OK. Just fix them after. The goal is confidence in core logic, not test purity.
