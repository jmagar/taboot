# Taboot API Quick Reference

## Application Structure

```text
apps/api/
├── app.py                    # Main FastAPI app + lifespan + middleware
├── middleware/
│   ├── __init__.py
│   └── logging.py            # UUID correlation logging
├── routes/
│   ├── __init__.py
│   ├── init.py              # POST /init (system initialization)
│   ├── ingest.py            # POST/GET /ingest (web crawling)
│   ├── extract.py           # POST/GET /extract (document extraction)
│   ├── query.py             # POST /query (RAG queries)
│   ├── status.py            # GET /status (system health + metrics)
│   └── documents.py         # GET /documents (list with filters)
├── deps/                     # Dependency modules (empty, placeholder)
├── services/                 # Service modules (empty, placeholder)
├── schemas/                  # Response models (empty, moved to packages/schemas)
├── CLAUDE.md                # Route-specific guidance
├── README.md                # Development guide
└── pyproject.toml           # Package metadata
```

## Configuration Flow

```text
.env (from .env.example)
    ↓
packages/common/config/__init__.py (TabootConfig)
    ↓
get_config() [singleton]
    ↓
Used in routes and lifespan
```

## Startup Sequence

```text
1. uvicorn apps.api.app:app
2. lifespan.__enter__()
   - Get config
   - Connect to Redis (fail fast on error)
   - Store redis_client in app.state
3. Router registration
4. App ready for requests
```

## Request Flow

```text
HTTP Request
    ↓
RequestLoggingMiddleware
    - Generate UUID request_id
    - Log request start
    - Add X-Request-ID to response
    ↓
Route Handler
    - Validate input
    - Call use-case (from packages/core)
    - Transform response
    ↓
Response
    - Status code
    - Headers (includes X-Request-ID)
    - Body (JSON)
```

## Endpoints Summary

| Method | Path | Handler | Status |
|--------|------|---------|--------|
| GET | / | root() | 200 |
| GET | /health | health() | 200/503 |
| POST | /init | initialize_system() | 200 |
| POST | /ingest | start_ingestion() | 202 |
| GET | /ingest/{job_id} | get_ingestion_status() | 200/404 |
| POST | /extract/pending | extract_pending() | 202 |
| GET | /extract/status | get_extract_status() | 200 |
| POST | /query | query_knowledge_base() | 200 |
| GET | /status | get_system_status() | 200 |
| GET | /documents | list_documents() | 200 |

## Key Dependencies

**Framework Layer:**
- FastAPI 0.119.0+ (HTTP)
- uvicorn 0.37.0+ (ASGI server)
- Pydantic 2.12.0+ (validation)

**Data Access:**
- redis 4.x (caching, queues)
- neo4j 5.x (graph database)
- qdrant-client (vector search)
- httpx (async HTTP)

**LlamaIndex Stack:**
- llama-index-core
- llama-index-vector-stores-qdrant
- llama-index-graph-stores-neo4j
- llama-index-llms-ollama

**Ingestion & Extraction:**
- firecrawl-py (web crawling)
- spacy (NLP)

## Configuration Categories

### Service URLs (default: container names)
- `firecrawl_api_url` = "http://taboot-crawler:3002"
- `redis_url` = "redis://taboot-cache:6379"
- `qdrant_url` = "http://taboot-vectors:6333"
- `neo4j_uri` = "bolt://taboot-graph:7687"
- `tei_embedding_url` = "http://taboot-embed:80"
- `reranker_url` = "http://taboot-rerank:8000"
- `playwright_microservice_url` = "http://taboot-playwright:3000/scrape"

### Database Credentials
- `neo4j_user` = "neo4j"
- `neo4j_password` = "changeme"
- `postgres_user` = "taboot"
- `postgres_password` = "changeme"

### Models & Tuning
- `tei_embedding_model` = "Qwen/Qwen3-Embedding-0.6B"
- `reranker_model` = "Qwen/Qwen3-Reranker-0.6B"
- `tier_c_batch_size` = 16 (LLM batch)
- `embedding_batch_size` = 32 (TEI batch)

### Smart Container Detection
- Detects if running in Docker
- Rewrites URLs to localhost:mapped_ports if on host

## Health Check Logic

```text
GET /health
    ↓
check_system_health() (concurrent)
    - check_neo4j_health()
    - check_qdrant_health()
    - check_redis_health()
    - check_tei_health()
    - check_ollama_health()
    - check_firecrawl_health()
    - check_playwright_health()
    ↓
overall_healthy = all(services.values())
    ↓
Response:
  - 200 OK if all healthy
  - 503 SERVICE_UNAVAILABLE if any failed
```

## Docker Integration

**Service:** `taboot-app` in docker-compose.yaml

**Build:**
- Multi-stage: builder (compile wheels) → runtime (minimal)
- Base: python:3.13-slim
- User: llamacrawl (UID 10001, non-root)

**Dependencies (wait for healthy):**
- taboot-cache (Redis)
- taboot-vectors (Qdrant)
- taboot-graph (Neo4j)
- taboot-embed (TEI)
- taboot-db (PostgreSQL)

**Ports:**
- 8000 (configurable via TABOOT_HTTP_PORT)

**Health Check:**
- curl -f http://localhost:8000/health
- interval: 30s, timeout: 10s, retries: 3, start_period: 20s

## Logging Pattern

```python
# Standard structured logging
logger.info(
    "Message",
    extra={
        "request_id": "uuid-1234",
        "method": "POST",
        "path": "/ingest",
        "duration_ms": 125,
        "status": 202
    }
)

# Produces JSON:
# {
#   "timestamp": "2024-10-23T...",
#   "level": "INFO",
#   "message": "Message",
#   "request_id": "uuid-1234",
#   ...
# }
```

## Testing Pattern

```python
# tests/apps/api/conftest.py

@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set env vars before app creation."""
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["QDRANT_URL"] = "http://localhost:6333"
    # ... etc
    yield

@pytest.fixture(scope="module")
def client():
    """Create TestClient after env setup."""
    from apps.api.app import app
    with TestClient(app) as test_client:
        yield test_client

# Usage:
def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
```

## Key Design Principles

1. **Thin Routing:** Business logic lives in packages/core
2. **Fail Fast:** Redis connection failure kills app (no fallbacks)
3. **Async-First:** All I/O is async (redis, httpx, db)
4. **Structured Logging:** JSON with correlation IDs
5. **Configuration Centralized:** Single get_config() singleton
6. **Health Comprehensive:** Every service is checked

## Security Status

**Currently:** No authentication/authorization

**Planned (from CLAUDE.md):**
- X-API-Key header validation
- OAuth 2.0 for data sources
- CORS restricted to specific origins
- Secrets manager integration
- Audit trail logging

## Common Issues & Solutions

### Redis Connection Fails
- App exits immediately (designed behavior)
- Check REDIS_URL env var
- Verify docker-compose postgres is healthy

### Health Check Fails
- Run: `curl http://localhost:8000/health`
- Check docker-compose ps (verify all services healthy)
- Check logs: `docker compose logs taboot-app`

### Config Not Loading
- Verify .env file exists and has required vars
- Check case sensitivity (config uses case_sensitive=False)
- Test with: `python -c "from packages.common.config import get_config; print(get_config().redis_url)"`

### Request Hangs
- Check for blocking I/O (should all be async)
- Verify service timeouts (default 5s for health checks)
- Review middleware order (CORS → RequestLogging)

## Performance Notes

### Concurrency
- Single uvicorn worker (async)
- asyncio event loop (no threading)
- Neo4j operations run in executor (doesn't block event loop)

### Timeouts
- Health checks: 5 seconds (configurable)
- Redis PING: uses redis-py defaults
- HTTP requests: use httpx defaults (no timeout set in health checks)

### Resource Usage
- Memory: Python process + Redis client pool
- Connections: 1 Redis pool + Neo4j driver + Qdrant client + Ollama HTTP
- Threads: Small executor pool for Neo4j sync operations

## Development Commands

```bash
# Run locally (requires .env and services)
uv run uvicorn apps.api.app:app --reload --port 8000

# Run via Docker
docker compose up taboot-app

# Test
uv run pytest tests/apps/api -m "not slow"

# Lint
uv run ruff check apps/api && uv run mypy apps/api

# OpenAPI docs
curl http://localhost:8000/openapi.json

# Health check
curl http://localhost:8000/health

# Swagger UI
open http://localhost:8000/docs
```

## File Locations Reference

| What | Where |
|------|-------|
| Main app | `apps/api/app.py` |
| Middleware | `apps/api/middleware/logging.py` |
| Routes | `apps/api/routes/*.py` |
| Config | `packages/common/config/__init__.py` |
| Health checks | `packages/common/health.py` |
| Docker build | `docker/api/Dockerfile` |
| Compose service | `docker-compose.yaml` (line 247) |
| Test config | `tests/apps/api/conftest.py` |
| Environment | `.env.example` |
