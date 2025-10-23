# Quickstart Guide: Taboot Doc-to-Graph RAG Platform

**Last Updated**: 2025-10-21

## Prerequisites

- **Docker** with Compose V2
- **NVIDIA GPU** (RTX 4070 or equivalent) with drivers installed
- **nvidia-container-toolkit** for GPU passthrough
- **Python 3.11+** managed via `uv`
- **Node.js 18+** and **pnpm** (optional, for web dashboard)
- **Minimum 16GB RAM**, **12GB GPU VRAM**, **50GB disk space**

## Initial Setup (5 minutes)

### 1. Clone and Configure

```bash
# Clone repository
git clone https://github.com/yourusername/taboot.git
cd taboot

# Install Python dependencies
uv sync

# Copy environment template and configure
cp .env.example .env
$EDITOR .env  # Set passwords, API keys if needed
```

### 2. Start Services

```bash
# Start all Docker services (Neo4j, Qdrant, Redis, TEI, Ollama, Firecrawl, etc.)
docker compose up -d

# Wait for services to be healthy (check status)
docker compose ps

# Expected output: All services showing "healthy" or "running"
# First run will download models (~20GB total): Qwen3-4B, Qwen3-Embedding-0.6B, spaCy en_core_web_md
```

### 3. Initialize Database Schemas

```bash
# Create Neo4j constraints, Qdrant collections, PostgreSQL tables
uv run apps/cli init

# Expected output:
# ✓ Neo4j constraints created (4)
# ✓ Qdrant collection 'documents' created (1024-dim, HNSW)
# ✓ PostgreSQL tables created (4)
# ✓ All services healthy
```

**Setup complete!** You're ready to ingest documents and start querying.

---

## Basic Workflows

### Ingest Web Documentation

Ingest a documentation site and build knowledge base:

```bash
# Ingest up to 20 pages from a documentation site
uv run apps/cli ingest web https://docs.example.com --limit 20

# Monitor progress (in separate terminal)
uv run apps/cli status --component firecrawl

# Expected output:
# ✓ 18 pages crawled (2 failed: rate limited)
# ✓ 342 chunks created
# ✓ 342 embeddings generated
# ✓ Qdrant upserts complete
# Job ID: 123e4567-e89b-12d3-a456-426614174000
# Duration: 45s
```

### Extract Knowledge Graph

Run extraction pipeline to build Neo4j property graph:

```bash
# Process documents awaiting extraction
uv run apps/cli extract pending

# Monitor extraction metrics
uv run apps/cli extract status

# Expected output:
# Tier A: 62.5 pages/sec (deterministic parsing)
# Tier B: 215.3 sentences/sec (spaCy NLP)
# Tier C: 4.2 windows/sec, median 235ms, p95 680ms (LLM)
# Cache hit rate: 63%
# Neo4j: 22,400 edges/min
# Qdrant: 5,320 vectors/sec
```

### Query the Knowledge Base

Ask natural language questions with hybrid retrieval:

```bash
# Basic query
uv run apps/cli query "Which services expose port 8080?"

# Expected output:
# The following services expose port 8080:
# - api-service [1] uses JWT authentication
# - web-frontend [2] serves static content
#
# Sources:
# [1] API Service Documentation (https://docs.example.com/api-service)
# [2] Frontend Configuration (https://docs.example.com/web-frontend)
#
# Query latency: 1.49s (embed: 45ms, vector: 82ms, rerank: 320ms, graph: 156ms, synthesis: 890ms)
```

### Query with Filters

Filter by source type or date:

```bash
# Filter by source types (web + docker_compose only)
uv run apps/cli query "Show all services" --sources web,docker_compose

# Filter by ingestion date (after Oct 15, 2025)
uv run apps/cli query "Recent infrastructure changes" --after 2025-10-15

# Combine filters and increase result count
uv run apps/cli query "Redis configuration" --sources docker_compose --top-k 10
```

---

## Advanced Workflows

### Ingest Structured Sources

Ingest infrastructure configurations directly into graph:

```bash
# Docker Compose file
uv run apps/cli ingest docker-compose ./docker-compose.yml

# Expected output:
# ✓ 12 services parsed
# ✓ 35 dependencies extracted (DEPENDS_ON relationships)
# ✓ 18 port bindings created (BINDS relationships)
# ✓ Neo4j writes complete

# SWAG reverse proxy config
uv run apps/cli ingest swag /path/to/swag/config

# Tailscale network data (requires API key in .env)
uv run apps/cli ingest tailscale
```

### Ingest from External APIs

Ingest from GitHub, Reddit, YouTube, etc. (requires API credentials):

```bash
# GitHub repository (README, wiki, issues)
uv run apps/cli ingest github owner/repo --limit 50

# Reddit subreddit (posts + top comments)
uv run apps/cli ingest reddit r/kubernetes --limit 100

# YouTube video transcript
uv run apps/cli ingest youtube https://www.youtube.com/watch?v=VIDEO_ID

# Gmail threads (requires OAuth credentials)
uv run apps/cli ingest gmail --label "Infrastructure" --limit 20

# Elasticsearch index
uv run apps/cli ingest elasticsearch logs-* --limit 1000
```

### Reprocess with Updated Extractors

Re-extract documents when extraction logic improves:

```bash
# Reprocess documents ingested in last 7 days
uv run apps/cli extract reprocess --since 7d

# Expected output:
# ✓ 123 documents queued for reprocessing
# ✓ Extraction jobs created
# Monitor progress: uv run apps/cli extract status
```

### Monitor System Health

Check service health and configuration:

```bash
# Overall system status
uv run apps/cli status

# Expected output:
# Services:
#   neo4j: healthy
#   qdrant: healthy
#   redis: healthy
#   tei: healthy
#   ollama: healthy
#   firecrawl: healthy
# Queue depth:
#   ingestion: 0
#   extraction: 5
# Config:
#   neo4j_uri: bolt://taboot-graph:7687
#   qdrant_url: http://taboot-vectors:6333
#   embedding_model: Qwen3-Embedding-0.6B

# Check specific component (verbose)
uv run apps/cli status --component neo4j --verbose
```

### List Ingested Documents

Browse ingested documents with filters:

```bash
# List recent documents (default 20)
uv run apps/cli list documents

# Filter by source type
uv run apps/cli list documents --source-type web --limit 50

# Filter by extraction state
uv run apps/cli list documents --extraction-state completed --limit 100

# Paginate results
uv run apps/cli list documents --limit 20 --offset 40
```

---

## Running the API Server

Start FastAPI server for HTTP access:

```bash
# API server already running in Docker
docker compose up -d taboot-app

# Check API health
curl http://localhost:8000/status

# Ingest via API
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "web",
    "source_target": "https://docs.example.com",
    "limit": 20
  }'

# Query via API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Which services expose port 8080?",
    "top_k": 10
  }'

# API documentation: http://localhost:8000/docs (OpenAPI/Swagger UI)
```

---

## Running Tests

Execute test suite with TDD methodology:

```bash
# Run all fast unit tests (no Docker required)
uv run pytest -m "not slow"

# Run integration tests (requires Docker services healthy)
uv run pytest -m integration --tb=short

# Run tests for specific package with coverage
uv run pytest --cov=packages packages/core

# Run slow tests (full end-to-end, requires GPU)
uv run pytest -m slow

# Run all tests with verbose output
uv run pytest -v

# Expected coverage: ≥85% in packages/core and packages/extraction
```

---

## Development Workflow (TDD)

Follow Test-Driven Development (RED-GREEN-REFACTOR):

### RED Phase: Write Failing Test

```bash
# Example: Test for web ingestion
# File: tests/packages/ingest/test_web_reader.py

import pytest
from packages.ingest.readers.web import WebReader

@pytest.mark.unit
def test_web_reader_crawls_page():
    reader = WebReader(firecrawl_url="http://taboot-crawler:3002")
    docs = reader.load_data(url="https://docs.example.com", limit=1)

    assert len(docs) == 1
    assert docs[0].text is not None
    assert len(docs[0].text) > 100  # Non-trivial content
    assert docs[0].metadata["source_url"] == "https://docs.example.com"

# Run test (expect FAIL)
uv run pytest tests/packages/ingest/test_web_reader.py::test_web_reader_crawls_page -v
```

### GREEN Phase: Write Minimum Code to Pass

```python
# File: packages/ingest/readers/web.py

from llama_index.core import Document
from llama_index.readers.web import SimpleWebPageReader

class WebReader:
    def __init__(self, firecrawl_url: str):
        self.firecrawl_url = firecrawl_url
        self.reader = SimpleWebPageReader()

    def load_data(self, url: str, limit: int = None) -> list[Document]:
        docs = self.reader.load_data([url])
        if limit:
            docs = docs[:limit]
        return docs

# Run test (expect PASS)
uv run pytest tests/packages/ingest/test_web_reader.py::test_web_reader_crawls_page -v
```

### REFACTOR Phase: Improve Code Quality

```python
# Add type hints, error handling, logging (keep tests green)
from typing import Optional
import logging
from llama_index.core import Document
from llama_index.readers.web import SimpleWebPageReader

logger = logging.getLogger(__name__)

class WebReader:
    """Web document reader using Firecrawl API."""

    def __init__(self, firecrawl_url: str) -> None:
        self.firecrawl_url = firecrawl_url
        self.reader = SimpleWebPageReader()

    def load_data(self, url: str, limit: Optional[int] = None) -> list[Document]:
        """Load documents from URL with optional limit."""
        logger.info(f"Loading data from {url} (limit: {limit})")

        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {url}")

        docs = self.reader.load_data([url])

        if limit and limit > 0:
            docs = docs[:limit]

        logger.info(f"Loaded {len(docs)} documents from {url}")
        return docs

# Run test (expect PASS, code improved)
uv run pytest tests/packages/ingest/test_web_reader.py::test_web_reader_crawls_page -v
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check service status
docker compose ps

# View logs for specific service
docker compose logs -f taboot-graph  # Neo4j
docker compose logs -f taboot-vectors  # Qdrant
docker compose logs -f taboot-ollama  # Ollama LLM

# Common issues:
# - GPU not detected: Install nvidia-container-toolkit, restart Docker
# - Port conflicts: Stop conflicting services on ports 7687, 6333, 6379, 8000, 3002
# - Out of memory: Increase Docker memory limit to 16GB+
```

### Model Downloads Failing

```bash
# Ollama model download (Qwen3-4B-Instruct)
docker exec taboot-ollama ollama pull qwen3:4b

# spaCy model download
uv run python -m spacy download en_core_web_md

# TEI and reranker models download automatically on first run
# Check logs: docker compose logs -f taboot-embed
```

### Tests Failing

```bash
# Ensure Docker services are healthy before integration tests
docker compose ps

# Run tests with verbose output to see failures
uv run pytest -v --tb=short

# Run only unit tests (no Docker required)
uv run pytest -m unit

# Common issues:
# - Integration tests fail if services not healthy: wait for healthchecks
# - GPU tests fail if CUDA unavailable: check nvidia-smi
```

### Extraction Pipeline Slow

```bash
# Check extraction metrics
uv run apps/cli extract status

# If Tier C latency high (>750ms p95):
# - Check GPU memory: nvidia-smi
# - Increase LLM batch size in .env: TIER_C_BATCH_SIZE=16
# - Reduce concurrency if OOM: TIER_C_WORKERS=2

# If cache hit rate low (<50%):
# - Increase Redis memory: redis.conf maxmemory 4gb
# - Check cache TTL in .env: REDIS_CACHE_TTL=604800 (7 days)
```

### Graph Queries Slow

```bash
# Check Neo4j indexes
docker exec taboot-graph cypher-shell -u neo4j -p changeme "SHOW INDEXES;"

# If missing indexes, re-run init
uv run apps/cli init

# Enable query logging to debug slow Cypher
# In docker-compose.yaml, add to taboot-graph environment:
# NEO4J_dbms_logs_query_enabled=INFO
# NEO4J_dbms_logs_query_threshold=1s
```

---

## Next Steps

1. **Ingest your documentation**: Start with web docs, then add structured sources (Docker Compose, etc.)
2. **Test extraction quality**: Review Neo4j graph, validate entity/relationship accuracy
3. **Tune retrieval**: Adjust top-k, reranking, graph traversal depth for your use case
4. **Customize prompts**: Edit `packages/retrieval/context/prompts.py` for domain-specific synthesis
5. **Add validation data**: Create ~300 labeled windows for F1 score tracking (target ≥0.85)
6. **Set up monitoring**: Track extraction metrics, query latency, cache hit rates over time
7. **Scale ingestion**: Add more sources (GitHub, Reddit, YouTube) with API credentials
8. **Deploy API**: Expose FastAPI service for web dashboard or external integrations

---

## Configuration Reference

Key environment variables in `.env`:

```bash
# Service URLs (Docker internal)
FIRECRAWL_API_URL=http://taboot-crawler:3002
REDIS_URL=redis://taboot-cache:6379
QDRANT_URL=http://taboot-vectors:6333
NEO4J_URI=bolt://taboot-graph:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
TEI_EMBEDDING_URL=http://taboot-embed:80
OLLAMA_PORT=11434

# Extraction tuning
TIER_C_BATCH_SIZE=16  # LLM batch size (8-16 optimal)
TIER_C_WORKERS=4  # Concurrent LLM workers
REDIS_CACHE_TTL=604800  # 7 days

# Reranker tuning
RERANKER_BATCH_SIZE=16  # Reranker batch size
RERANKER_DEVICE=auto  # GPU if available

# API credentials (optional, for external sources)
GITHUB_TOKEN=ghp_...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
YOUTUBE_API_KEY=...
GMAIL_CREDENTIALS_PATH=/path/to/credentials.json
```

---

## Performance Targets (RTX 4070)

Expected performance with default config:

| Metric | Target | Typical |
|--------|--------|---------|
| Tier A throughput | ≥50 pages/sec | 60-70 pages/sec |
| Tier B throughput | ≥200 sent/sec | 210-230 sent/sec |
| Tier C median latency | ≤250ms | 220-240ms |
| Tier C p95 latency | ≤750ms | 650-700ms |
| Neo4j writes | ≥20k edges/min | 22-25k edges/min |
| Qdrant upserts | ≥5k vectors/sec | 5.2-5.5k vectors/sec |
| Query latency (median) | <5s | 1.5-3s |
| Cache hit rate | ≥60% | 60-70% |

If performance degrades, check GPU memory (nvidia-smi), service logs, and tune batch sizes.

---

## Additional Resources

- **CLAUDE.md**: Development guidance for AI assistants
- **README.md**: Project overview and deployment
- **docs/ARCHITECTURE.md**: System architecture deep dive
- **apps/api/docs/API.md**: API endpoint reference
- **packages/*/README.md**: Package-specific documentation
- **docker-compose.yaml**: Service configuration
- **.specify/memory/constitution.md**: Project constitution (principles, standards)
