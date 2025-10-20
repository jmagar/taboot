# Quick Start: LlamaCrawl v2

**Feature**: `001-llamacrawl-v2-rag-platform`
**Audience**: Developers setting up LlamaCrawl v2 for the first time
**Time to Complete**: 20-30 minutes

---

## Prerequisites

Before starting, ensure you have:

### Required Software

1. **Python 3.11+** — Install via [python.org](https://www.python.org/) or system package manager
2. **uv** — Python package manager ([Installation](https://github.com/astral-sh/uv))
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. **Docker 24+** with Docker Compose v2 — [Installation Guide](https://docs.docker.com/get-docker/)
4. **NVIDIA GPU with ≥8GB VRAM** (RTX 3060/4060 minimum, RTX 4070 recommended)
5. **nvidia-container-toolkit** — [Installation Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
   ```bash
   # Ubuntu/Debian
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

### Hardware Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 16GB minimum, 32GB recommended
- **GPU**: NVIDIA GPU with ≥8GB VRAM (for TEI embeddings, reranker, Ollama LLM)
- **Disk**: 50GB free space (for Docker images, models, data)

### Verify GPU Access

```bash
# Verify NVIDIA driver
nvidia-smi

# Verify Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

Expected output: GPU info with CUDA version ≥12.0

---

## Setup Steps

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/taboot.git
cd taboot
```

### 2. Install Python Dependencies

```bash
# Sync workspace dependencies (all packages)
uv sync

# Verify installation
uv run python --version
# Expected: Python 3.11.x or 3.12.x or 3.13.x
```

**What this does**: Installs all packages in the monorepo (core, adapters, apps) with pinned versions from `uv.lock`.

### 3. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit config (use your preferred editor)
nano .env
```

**Minimal required config** (defaults work for local development):

```bash
# Neo4j
NEO4J_URI=bolt://taboot-graph:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme

# Qdrant
QDRANT_URL=http://taboot-vectors:6333

# Redis
REDIS_URL=redis://taboot-cache:6379

# Firecrawl
FIRECRAWL_API_URL=http://taboot-crawler:3002

# Ollama
OLLAMA_PORT=11434

# TEI Embeddings
TEI_EMBEDDING_URL=http://taboot-embed:80

# Reranker
RERANKER_URL=http://taboot-rerank:8000
RERANKER_MODEL=Qwen/Qwen3-Reranker-0.6B

# API
LLAMACRAWL_API_URL=http://localhost:8000
```

**Optional source credentials** (add as needed):

```bash
# GitHub (for ingesting repos)
GITHUB_TOKEN=ghp_your_token_here

# Reddit (for ingesting threads)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret

# Gmail (for ingesting emails)
GMAIL_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
```

### 4. Start All Services

```bash
# Pull and start all 11 services
docker compose up -d

# Watch startup logs (optional)
docker compose logs -f
# Press Ctrl+C to exit logs
```

**Services started**:
1. `taboot-graph` — Neo4j 5.23 with APOC
2. `taboot-vectors` — Qdrant with GPU acceleration
3. `taboot-cache` — Redis 7.2
4. `taboot-db` — PostgreSQL 16 (Firecrawl metadata)
5. `taboot-crawler` — Firecrawl v2 API
6. `taboot-playwright` — Playwright browser microservice
7. `taboot-embed` — TEI embeddings (Qwen3-Embedding-0.6B, GPU)
8. `taboot-rerank` — Reranker (Qwen3-Reranker-0.6B, GPU)
9. `taboot-ollama` — Ollama LLM (Qwen3-4B-Instruct, GPU)
10. `taboot-app` — FastAPI + MCP + Web (unified container)
11. `taboot-worker` — Extraction worker (Tier A/B/C)

**Expected wait time**: 60-120 seconds for all services to become healthy.

### 5. Verify Services Health

```bash
# Check service status
docker compose ps

# All services should show "Up" with "(healthy)" status
```

**Troubleshooting**: If any service is unhealthy:

```bash
# View logs for specific service
docker compose logs taboot-graph
docker compose logs taboot-ollama

# Common issues:
# - taboot-ollama: First run downloads Qwen3-4B (may take 5-10 min)
# - taboot-embed: Model download (Qwen3-Embedding-0.6B, ~2GB)
# - taboot-graph: Wait for Neo4j initialization (30-60 sec)
```

### 6. Initialize Schema

```bash
# Initialize Neo4j constraints/indexes and Qdrant collection
uv run taboot init

# Expected output:
# ✓ Neo4j constraints created (11 total)
# ✓ Neo4j indexes created (14 total)
# ✓ Qdrant collection 'taboot.documents' created
# ✓ Qdrant indexes created (8 payload fields)
# ✓ Redis connection verified
# ✓ Initialization complete
```

**What this does**:
- Creates Neo4j constraints (unique on Service.name, Host.hostname, etc.)
- Creates Neo4j indexes (for query performance)
- Creates Qdrant collection with 1024-dim vectors, HNSW config
- Creates Qdrant payload indexes
- Verifies Redis connectivity

### 7. Pull Ollama Model (First-Time Only)

```bash
# Pull Qwen3-4B-Instruct model
docker exec taboot-ollama ollama pull qwen2.5:4b-instruct

# Expected download: ~2.5GB
# Time: 5-10 minutes depending on network speed
```

**Verification**:

```bash
# List models
docker exec taboot-ollama ollama list

# Expected output:
# NAME                     ID              SIZE    MODIFIED
# qwen2.5:4b-instruct      abc123def456    2.5GB   1 minute ago
```

---

## First Workflow: Ingest → Extract → Query

### Step 1: Ingest a Web Page

```bash
# Ingest a single technical documentation page
uv run taboot ingest web https://docs.docker.com/compose/

# Expected output:
# → Starting web ingestion: https://docs.docker.com/compose/
# → Firecrawl job started: fwl_abc123
# → Crawling... (0/1 pages)
# → Crawling... (1/1 pages)
# ✓ Crawl complete
# → Normalizing content (HTML → Markdown, boilerplate removal)
# → Chunking (512 tokens, 128 overlap)
# → Created 45 chunks
# → Embedding chunks (TEI, 1024-dim)
# → Upserting to Qdrant...
# ✓ Qdrant upsert complete (45 vectors)
# → Creating Neo4j Document node...
# ✓ Document created: doc_id=550e8400-e29b-41d4-a716-446655440000
#
# Ingestion complete in 8.2s
```

**What happened**:
1. Firecrawl crawled the URL
2. Content normalized (HTML → Markdown)
3. Text chunked semantically (≤512 tokens per chunk)
4. TEI embedded chunks (1024-dim vectors)
5. Vectors upserted to Qdrant
6. Neo4j Document node created
7. MENTIONS relationships created (Document → chunks)

### Step 2: Run Extraction Pipeline

```bash
# Extract entities and relationships from ingested document
uv run taboot extract pending

# Expected output:
# → Checking pending extractions...
# → Tier A: 1 document (deterministic parsing)
# → Tier B: 45 chunks (spaCy NLP)
# → Tier C: 0 windows (LLM extraction)
#
# Running Tier A extraction...
# ✓ Tier A complete (0 entities, 0 relations) — no structured configs detected
#
# Running Tier B extraction...
# → Processing chunk 1/45...
# → Processing chunk 2/45...
# ...
# ✓ Tier B complete (12 entities, 8 relations, 3 windows selected for Tier C)
#
# Running Tier C extraction on 3 windows...
# → Window 1/3 (245ms, cached=false)
# → Window 2/3 (187ms, cached=false)
# → Window 3/3 (203ms, cached=false)
# ✓ Tier C complete (15 entities, 12 relations)
#
# Writing to Neo4j...
# → Batch 1/1 (27 nodes, 20 edges)
# ✓ Neo4j write complete
#
# Extraction complete in 4.8s
```

**What happened**:
1. **Tier A** (deterministic): No Docker Compose/SWAG configs found, skipped
2. **Tier B** (spaCy): Extracted service names (Docker, Compose, etc.), identified 3 high-relevance windows
3. **Tier C** (LLM): Processed 3 windows with Qwen3-4B, extracted detailed entities and relationships
4. **Neo4j**: Batch-wrote nodes (Service, Host, etc.) and edges (DEPENDS_ON, etc.) with provenance

### Step 3: Query the Knowledge Graph

```bash
# Ask a question about the ingested content
uv run taboot query "What is Docker Compose used for?"

# Expected output:
# → Embedding query (TEI, 1024-dim)...
# → Vector search (Qdrant, top-100)...
# → Reranking (top-5)...
# → Graph traversal (2 hops)...
# → Synthesizing answer (Qwen3-4B)...
#
# Answer:
# Docker Compose [1] is a tool for defining and running multi-container Docker applications [2].
# It uses YAML files to configure application services [3], allowing developers to spin up
# entire application stacks with a single command [1]. Compose simplifies the management of
# containerized applications by handling networking, volumes, and dependencies between services [2].
#
# Sources:
# [1] Docker Compose Overview (doc_id: 550e8400-e29b-41d4-a716-446655440000)
#     https://docs.docker.com/compose/
#     Section: "Overview"
#     Ingested: 2025-10-20 14:30:00 UTC
#
# [2] Docker Compose Features (doc_id: 550e8400-e29b-41d4-a716-446655440000)
#     https://docs.docker.com/compose/
#     Section: "Key features"
#     Ingested: 2025-10-20 14:30:00 UTC
#
# [3] Compose File Reference (doc_id: 550e8400-e29b-41d4-a716-446655440000)
#     https://docs.docker.com/compose/
#     Section: "Compose file"
#     Ingested: 2025-10-20 14:30:00 UTC
#
# Query executed in 1.8s
```

**What happened**:
1. **Embedding**: Query embedded to 1024-dim vector (TEI)
2. **Vector Search**: Top-100 similar chunks retrieved from Qdrant
3. **Reranking**: BAAI reranker re-scored to top-5 most relevant
4. **Graph Traversal**: Neo4j explored ≤2 hops for related entities
5. **Synthesis**: Qwen3-4B generated natural-language answer with inline citations
6. **Bibliography**: Source list with document IDs, URLs, sections, timestamps

---

## Testing a Single Pipeline Tier

### Test Tier A: Deterministic Parsing (Docker Compose)

Create a sample `docker-compose.yaml`:

```bash
cat > /tmp/test-compose.yaml <<EOF
services:
  nginx:
    image: nginx:1.25
    ports:
      - "80:80"
    depends_on:
      - postgres
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: changeme
EOF
```

Ingest and extract:

```bash
# Ingest Docker Compose file
uv run taboot ingest compose /tmp/test-compose.yaml

# Extract (Tier A only)
uv run taboot extract pending

# Expected Tier A output:
# ✓ Tier A complete (4 entities, 3 relations)
#   Entities: Service(nginx), Service(postgres), Host(localhost), Image(nginx:1.25), Image(postgres:15)
#   Relations: nginx DEPENDS_ON postgres, nginx BINDS localhost:80, postgres BINDS localhost:5432
```

Verify in Neo4j:

```bash
# Query Neo4j directly
uv run taboot graph query "MATCH (s:Service)-[:DEPENDS_ON]->(d:Service) RETURN s.name, d.name"

# Expected output:
# s.name    | d.name
# ----------|----------
# nginx     | postgres
```

---

## Debugging Checklist

### Service Health Issues

**Problem**: `docker compose ps` shows services as "unhealthy"

**Solutions**:

1. **Neo4j not starting**:
   ```bash
   # Check logs
   docker compose logs taboot-graph

   # Common issue: Insufficient memory
   # Solution: Increase Docker memory limit to ≥4GB
   # Docker Desktop → Settings → Resources → Memory
   ```

2. **Ollama not healthy**:
   ```bash
   # Check logs
   docker compose logs taboot-ollama

   # Common issue: GPU not detected
   # Verify: nvidia-smi works inside container
   docker exec taboot-ollama nvidia-smi

   # If GPU not found, ensure nvidia-container-toolkit installed
   ```

3. **Qdrant not starting**:
   ```bash
   docker compose logs taboot-vectors

   # Common issue: Port conflict (6333 already in use)
   # Solution: Change QDRANT_PORT in .env
   ```

### Ingestion Failures

**Problem**: `taboot ingest` fails with error

**Common Errors**:

| Error Code | Cause | Solution |
|------------|-------|----------|
| `E_URL_BAD` | Malformed URL | Check URL format (`https://...`) |
| `E_ROBOTS` | Blocked by robots.txt | Respect robots.txt or configure override |
| `E_TIMEOUT` | Firecrawl timeout | Increase timeout or use async ingestion |
| `E_QDRANT` | Qdrant connection failed | Check `docker compose ps taboot-vectors` |
| `E_NEO4J` | Neo4j connection failed | Check `docker compose ps taboot-graph` |

**Debug steps**:

```bash
# 1. Verify services
docker compose ps

# 2. Check API logs
docker compose logs taboot-app

# 3. Check Firecrawl logs
docker compose logs taboot-crawler

# 4. Test Firecrawl directly
curl http://localhost:3002/health
# Expected: {"status":"ok"}
```

### Extraction Failures

**Problem**: Extraction produces no results or fails

**Debug steps**:

```bash
# 1. Check extraction worker logs
docker compose logs taboot-worker

# 2. Check DLQ (dead-letter queue) count
uv run taboot status

# Expected output:
# Extraction Status:
# - Tier A pending: 0
# - Tier B pending: 0
# - Tier C pending: 0
# - DLQ (failed): 0

# 3. If DLQ > 0, inspect failed windows
docker exec taboot-cache redis-cli KEYS "dlq:extraction:*"
```

**Common issues**:

- **Tier C LLM timeout**: Increase `OLLAMA_TIMEOUT` in `.env`
- **Malformed JSON from LLM**: Check Ollama logs, verify model pulled correctly
- **spaCy model missing**: Run `python -m spacy download en_core_web_md` in worker container

### Query Returns No Results

**Problem**: `taboot query` returns no answer or "No relevant documents found"

**Debug steps**:

```bash
# 1. Verify documents ingested
uv run taboot graph query "MATCH (d:Document) RETURN d.docId, d.title LIMIT 5"

# 2. Check Qdrant points count
curl http://localhost:6333/collections/taboot.documents
# Expected: {"result": {"points_count": > 0, ...}}

# 3. Test embedding service
curl -X POST http://localhost:80/embed \
  -H "Content-Type: application/json" \
  -d '{"inputs": ["test query"]}'
# Expected: {"embeddings": [[...]], "model": "..."}

# 4. Query with verbose logging
uv run taboot query "test" --verbose
```

### Performance Issues

**Problem**: Ingestion/extraction/query is slower than targets

**Benchmark targets** (RTX 4070):
- Tier A: ≥50 pages/sec
- Tier B: ≥200 sentences/sec
- Tier C: ≤250ms/window median
- Query: <3s p95 end-to-end

**Debug steps**:

```bash
# 1. Check GPU utilization
nvidia-smi -l 1
# Should show 80-100% GPU utilization during extraction/query

# 2. Check Ollama performance
docker exec taboot-ollama ollama run qwen2.5:4b-instruct "Test prompt"
# Should complete in <1s

# 3. Check Redis cache hit rate
docker exec taboot-cache redis-cli INFO stats | grep keyspace_hits
# Hit rate should be ≥60% after warmup

# 4. Profile extraction pipeline
uv run taboot extract pending --profile
# Outputs timing breakdown by tier
```

---

## Next Steps

### Ingest from Multiple Sources

**GitHub repository**:
```bash
uv run taboot ingest github https://github.com/username/repo --token $GITHUB_TOKEN
```

**Reddit thread**:
```bash
uv run taboot ingest reddit https://reddit.com/r/programming/comments/xyz
```

**Local Docker Compose file**:
```bash
uv run taboot ingest compose /path/to/docker-compose.yaml
```

### Advanced Queries

**Filter by source**:
```bash
uv run taboot query "nginx config" --source compose
```

**Filter by date range**:
```bash
uv run taboot query "recent changes" --since 7d
```

**Graph traversal only (no vector search)**:
```bash
uv run taboot query "dependencies of nginx" --graph-only
```

### Development Workflows

**Run tests**:
```bash
# Unit tests (fast)
uv run pytest -m "not slow"

# Integration tests (requires Docker services healthy)
uv run pytest -m "integration"

# Coverage report
uv run pytest --cov=packages/core packages/core
```

**Lint and format**:
```bash
uv run ruff check .
uv run ruff format .
```

**Type check**:
```bash
uv run mypy .
```

### API Access

Start API server:
```bash
uv run llamacrawl-api
# Listening on http://localhost:8000
```

Access API docs:
```
http://localhost:8000/docs
```

Authenticate:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme"}'

# Response:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer",
#   "expires_in": 3600
# }
```

Query via API:
```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Docker Compose?"}'
```

---

## Configuration Reference

### Environment Variables (Key Settings)

**Neo4j**:
- `NEO4J_URI` — Bolt connection URI (default: `bolt://taboot-graph:7687`)
- `NEO4J_USER` — Username (default: `neo4j`)
- `NEO4J_PASSWORD` — Password (default: `changeme`)

**Qdrant**:
- `QDRANT_URL` — HTTP endpoint (default: `http://taboot-vectors:6333`)
- `QDRANT_COLLECTION` — Collection name (default: `taboot.documents`)

**Ollama**:
- `OLLAMA_HOST` — Ollama server (default: `http://taboot-ollama:11434`)
- `OLLAMA_MODEL` — LLM model (default: `qwen2.5:4b-instruct`)

**TEI Embeddings**:
- `TEI_EMBEDDING_URL` — TEI endpoint (default: `http://taboot-embed:80`)
- `EMBEDDING_MODEL` — Model ID (default: `Qwen/Qwen3-Embedding-0.6B`)

**Reranker**:
- `RERANKER_URL` — Reranker endpoint (default: `http://taboot-rerank:8000`)
- `RERANKER_MODEL` — Model ID (default: `Qwen/Qwen3-Reranker-0.6B`)

**Performance Tuning**:
- `EXTRACTION_BATCH_SIZE` — Tier C batch size (default: `8`)
- `VECTOR_SEARCH_TOP_K` — Initial vector search results (default: `100`)
- `RERANK_TOP_N` — Post-rerank results (default: `5`)
- `GRAPH_TRAVERSAL_MAX_HOPS` — Max graph hops (default: `2`)

See `.env.example` for complete list (112 variables documented).

---

## Common Workflows

### Daily Development

```bash
# Start services
docker compose up -d

# Run tests
uv run pytest -m "not slow"

# Ingest new document
uv run taboot ingest web https://example.com/docs

# Query
uv run taboot query "your question"

# Stop services
docker compose down
```

### Reset All Data

```bash
# WARNING: Deletes all ingested documents, chunks, triples
docker compose down -v  # Delete volumes
docker compose up -d    # Restart
uv run taboot init      # Re-initialize schema
```

### View Service Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f taboot-ollama

# Last 100 lines
docker compose logs --tail=100 taboot-worker
```

### Backup Neo4j Data

```bash
# Create backup
docker exec taboot-graph neo4j-admin dump --to=/backups/backup-$(date +%Y%m%d).dump

# Restore backup
docker compose down
docker exec taboot-graph neo4j-admin load --from=/backups/backup-20251020.dump
docker compose up -d
```

---

## Troubleshooting FAQ

**Q: Models not downloading?**
A: Check disk space (`df -h`). Models total ~20GB. Clear space and retry.

**Q: GPU out of memory?**
A: Reduce batch sizes in `.env`: `EXTRACTION_BATCH_SIZE=4`, `RERANKER_BATCH_SIZE=8`

**Q: Neo4j slow?**
A: Increase heap size in `docker-compose.yaml`: `NEO4J_dbms_memory_heap_max__size=4G`

**Q: Qdrant slow?**
A: Increase page cache: `QDRANT_PAGE_CACHE_SIZE=4g` in `docker-compose.yaml`

**Q: Tests failing?**
A: Ensure all services healthy (`docker compose ps`). Run `uv run taboot init` again.

---

## Getting Help

- **Documentation**: `/home/jmagar/code/taboot/docs/`
- **Issues**: GitHub Issues (https://github.com/yourusername/taboot/issues)
- **Logs**: `docker compose logs -f`
- **Health**: `curl http://localhost:8000/health/services`

**Common log locations**:
- API: `docker compose logs taboot-app`
- Worker: `docker compose logs taboot-worker`
- Neo4j: `docker compose logs taboot-graph`
- Ollama: `docker compose logs taboot-ollama`

---

## Quick Reference Card

```bash
# Setup
uv sync                          # Install dependencies
docker compose up -d             # Start services
uv run taboot init               # Initialize schema

# Ingest
uv run taboot ingest web <URL>   # Web page
uv run taboot ingest compose <FILE>  # Docker Compose

# Extract
uv run taboot extract pending    # Run extraction pipeline

# Query
uv run taboot query "question"   # Hybrid retrieval

# Status
docker compose ps                # Service health
uv run taboot status             # Extraction status
uv run taboot graph query "MATCH (n) RETURN count(n)"  # Node count

# Development
uv run pytest                    # Run tests
uv run ruff check .              # Lint
uv run mypy .                    # Type check

# Cleanup
docker compose down              # Stop services
docker compose down -v           # Stop + delete data
```

---

**Version**: 1.0.0
**Last Updated**: 2025-10-20
**Status**: Complete
